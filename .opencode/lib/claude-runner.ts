import { createHash, randomUUID } from "node:crypto";
import { execFileSync, spawn } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  renameSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { basename, dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

export type ClaudeRole =
  | "explore"
  | "counter-plan"
  | "investigate"
  | "design-review"
  | "debate"
  | "diff"
  | "pr"
  | "refute"
  | "implement";

type ClaudeProfile = {
  model: "claude-sonnet-5" | "claude-opus-5";
  effort: "medium" | "high" | "xhigh";
};

type RunnerContext = {
  agent: string;
  directory: string;
  worktree: string;
  abort: AbortSignal;
  ask(input: {
    permission: string;
    patterns: string[];
    always: string[];
    metadata: Record<string, unknown>;
  }): Promise<void>;
  metadata(input: {
    title?: string;
    metadata?: Record<string, unknown>;
  }): void;
};

type SpawnBase = {
  role: Exclude<ClaudeRole, "implement">;
  promptPath: string;
  contextPaths?: string[];
  workingDir: string;
  runId: string;
  complexity?: "normal" | "complex";
  highRisk?: boolean;
  deadlineSeconds?: number;
};

type SpawnImplement = {
  workOrderPath: string;
  contextPaths?: string[];
  workingDir: string;
  runId: string;
  proofCommand?: string;
  complexity?: "normal" | "complex";
  highRisk?: boolean;
  deadlineSeconds?: number;
};

type Manifest = {
  version: 1;
  handle: string;
  runId: string;
  attemptId: string;
  parentHandle?: string;
  transport: "cli-exec" | "cli-resume";
  role: ClaudeRole;
  readOnly: boolean;
  workingDirectory: string;
  promptPath: string;
  sourcePath: string;
  contextPaths: string[];
  workOrderPath?: string;
  proofCommand?: string;
  sessionId: string;
  profile: ClaudeProfile;
  availableTools: string[];
  allowedTools: string[];
  cliArguments: string[];
  stdoutPath: string;
  stderrPath: string;
  statusPath: string;
  processPath: string;
  deadlineSeconds: number;
  promptSha256: string;
  startedAt: string;
};

type Status = {
  state: "queued" | "running" | "completed" | "failed" | "timed_out" | "terminated";
  workerPid?: number;
  claudePid?: number;
  exitCode?: number | null;
  signal?: string | null;
  startedAt?: string;
  endedAt?: string;
  error?: string;
};

const OPENCODE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const WORKER_PATH = resolve(dirname(fileURLToPath(import.meta.url)), "claude-worker.mjs");
const RUN_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;
const ATTEMPT_ID_PATTERN = /^[0-9a-f-]{36}$/;
const READONLY_ROLES = new Set<ClaudeRole>([
  "explore",
  "counter-plan",
  "investigate",
  "design-review",
  "debate",
  "diff",
  "pr",
  "refute",
]);
const OPUS_ROLES = new Set<ClaudeRole>([
  "investigate",
  "design-review",
  "debate",
  "diff",
  "pr",
  "refute",
]);
const PROOF_BINARIES = new Set([
  "npm",
  "npx",
  "pnpm",
  "yarn",
  "node",
  "python",
  "python3",
  "pytest",
  "cargo",
  "go",
  "mvn",
  "gradle",
  "gradlew",
  "dotnet",
  "swift",
  "xcodebuild",
  "bundle",
  "rspec",
  "php",
  "composer",
]);

function sha256(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}

function writeJson(path: string, value: unknown): void {
  const temporary = `${path}.tmp-${process.pid}-${randomUUID()}`;
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  renameSync(temporary, path);
}

function realDirectory(path: string): string {
  const canonical = realpathSync(path);
  if (!statSync(canonical).isDirectory()) {
    throw new Error(`Not a directory: ${path}`);
  }
  return canonical;
}

function isWithin(base: string, target: string): boolean {
  const distance = relative(base, target);
  return distance === "" || (!distance.startsWith(`..${sep}`) && distance !== "..");
}

function contextRoots(context: RunnerContext): string[] {
  return [...new Set([context.directory, context.worktree])]
    .filter((path) => existsSync(path))
    .map(realDirectory);
}

function resolveWorkingDirectory(raw: string, context: RunnerContext): string {
  const candidate = realDirectory(isAbsolute(raw) ? raw : resolve(context.directory, raw));
  if (!contextRoots(context).some((root) => isWithin(root, candidate))) {
    throw new Error(`working_dir is outside the OpenCode session roots: ${raw}`);
  }
  return candidate;
}

function resolveInputFile(raw: string, workingDirectory: string, roots: string[]): string {
  if (!raw || raw.includes("\0")) {
    throw new Error("Input path is empty or invalid");
  }
  const candidate = realpathSync(isAbsolute(raw) ? raw : resolve(workingDirectory, raw));
  if (!statSync(candidate).isFile()) {
    throw new Error(`Not a file: ${raw}`);
  }
  if (!roots.some((root) => isWithin(root, candidate))) {
    throw new Error(`Input path is outside the OpenCode session roots: ${raw}`);
  }
  return candidate;
}

function assertRunId(runId: string): void {
  if (!RUN_ID_PATTERN.test(runId)) {
    throw new Error("run_id must contain only letters, numbers, dot, underscore or hyphen");
  }
}

function handleParts(handle: string): { runId: string; attemptId: string } {
  const [runId, attemptId, extra] = handle.split(":");
  if (extra || !runId || !attemptId || !RUN_ID_PATTERN.test(runId) || !ATTEMPT_ID_PATTERN.test(attemptId)) {
    throw new Error("Invalid Claude handle");
  }
  return { runId, attemptId };
}

function storageRoot(context: RunnerContext): string {
  return resolve(realDirectory(context.directory), ".cross-model", "opencode-cli");
}

function attemptDirectory(context: RunnerContext, runId: string, attemptId: string): string {
  return resolve(storageRoot(context), runId, attemptId);
}

function loadManifest(context: RunnerContext, handle: string): Manifest {
  const { runId, attemptId } = handleParts(handle);
  const directory = attemptDirectory(context, runId, attemptId);
  const path = resolve(directory, "manifest.json");
  if (!isWithin(storageRoot(context), path) || !existsSync(path)) {
    throw new Error(`Unknown Claude handle: ${handle}`);
  }
  const manifest = JSON.parse(readFileSync(path, "utf8")) as Manifest;
  if (manifest.handle !== handle || manifest.runId !== runId || manifest.attemptId !== attemptId) {
    throw new Error("Claude manifest identity mismatch");
  }
  const expectedPaths: Partial<Record<keyof Manifest, string>> = {
    promptPath: resolve(directory, "prompt.md"),
    stdoutPath: resolve(directory, "stdout.json"),
    stderrPath: resolve(directory, "stderr.log"),
    statusPath: resolve(directory, "status.json"),
    processPath: resolve(directory, "process.json"),
  };
  for (const [field, expected] of Object.entries(expectedPaths)) {
    if (manifest[field as keyof Manifest] !== expected) {
      throw new Error(`Claude manifest path mismatch: ${field}`);
    }
  }
  const workingDirectory = realDirectory(manifest.workingDirectory);
  if (!contextRoots(context).some((root) => isWithin(root, workingDirectory))) {
    throw new Error("Claude manifest working directory is outside the OpenCode session roots");
  }
  if (READONLY_ROLES.has(manifest.role) !== manifest.readOnly) {
    throw new Error("Claude manifest role/permission mismatch");
  }
  if (manifest.transport !== (manifest.parentHandle ? "cli-resume" : "cli-exec")) {
    throw new Error("Claude manifest transport mismatch");
  }
  return manifest;
}

function roleContractPath(role: ClaudeRole): string {
  const relativePath: Record<ClaudeRole, string> = {
    explore: "agents/explorer.md",
    "counter-plan": "agents/explorer.md",
    investigate: "agents/investigator.md",
    "design-review": "roles/design-reviewer.md",
    debate: "roles/debate.md",
    diff: "agents/code-reviewer.md",
    pr: "agents/code-reviewer.md",
    refute: "agents/code-reviewer.md",
    implement: "agents/builder.md",
  };
  return resolve(OPENCODE_ROOT, relativePath[role]);
}

export function stripFrontmatter(markdown: string): string {
  return markdown.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "").trim();
}

export function resolveClaudeProfile(
  role: ClaudeRole,
  complexity: "normal" | "complex" = "normal",
  highRisk = false,
): ClaudeProfile {
  if (OPUS_ROLES.has(role) || complexity === "complex" || highRisk) {
    return { model: "claude-opus-5", effort: "xhigh" };
  }
  if (role === "implement") {
    return { model: "claude-sonnet-5", effort: "high" };
  }
  return { model: "claude-sonnet-5", effort: "medium" };
}

export function sanitizeClaudeEnvironment(environment: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
  const clean = { ...environment };
  const exact = new Set([
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
  ]);
  for (const key of Object.keys(clean)) {
    if (key.startsWith("ANTHROPIC_") || key.startsWith("MERIDIAN_") || exact.has(key)) {
      delete clean[key];
    }
  }
  return clean;
}

export function proofBinaries(command?: string): string[] {
  if (!command) return [];
  if (/[`\n\r]|\$\(/.test(command)) {
    throw new Error("proof_cmd may not contain command substitution, backticks or newlines");
  }
  const binaries = new Set<string>();
  for (const section of command.split(/&&|\|\||[;|]/)) {
    const tokens = section.trim().split(/\s+/).filter(Boolean);
    while (tokens[0]?.includes("=") && /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[0])) tokens.shift();
    if (tokens[0] === "cd") continue;
    const token = tokens[0];
    if (!token) continue;
    const binary = token.replace(/^.*\//, "");
    if (!PROOF_BINARIES.has(binary)) {
      throw new Error(`Unsupported proof binary: ${token}`);
    }
    binaries.add(binary);
  }
  return [...binaries];
}

function buildPrompt(input: {
  role: ClaudeRole;
  sourcePath: string;
  sourceText: string;
  contextPaths: string[];
  workingDirectory: string;
  proofCommand?: string;
}): string {
  const contract = stripFrontmatter(readFileSync(roleContractPath(input.role), "utf8"));
  const contexts = input.contextPaths.length
    ? input.contextPaths.map((path) => `- ${path}`).join("\n")
    : "- Ninguno";
  const writerRules = input.role === "implement"
    ? `- Puedes editar solo dentro de ${input.workingDirectory}.\n- No hagas commit, push, merge, rebase ni stash.\n- El único Bash preautorizado es el proof_cmd exacto; no ejecutes comandos adicionales.\n- proof_cmd: ${input.proofCommand || "no definido; no uses Bash"}`
    : "- Esta ejecución es estrictamente read-only. No edites ni generes archivos.";

  return `<role_contract>\n${contract}\n</role_contract>\n\n<execution_contract>\n- MODE: ${input.role}\n- Working directory: ${input.workingDirectory}\n${writerRules}\n- No cargues CLAUDE.md, skills, plugins, hooks, MCPs ni agentes externos.\n- No intentes cambiar proveedor, autenticación, headers ni fingerprints.\n- Devuelve el resultado solicitado en español neutro.\n</execution_contract>\n\n<context_paths>\n${contexts}\n</context_paths>\n\n<assignment source="${input.sourcePath}">\n${input.sourceText}\n</assignment>\n`;
}

function cliArguments(manifest: Pick<Manifest, "profile" | "availableTools" | "allowedTools" | "sessionId">, resume = false): string[] {
  return [
    "-p",
    "--safe-mode",
    "--permission-mode",
    "default",
    "--output-format",
    "json",
    "--model",
    manifest.profile.model,
    "--effort",
    manifest.profile.effort,
    `--tools=${manifest.availableTools.join(",")}`,
    `--allowedTools=${manifest.allowedTools.join(",")}`,
    resume ? "--resume" : "--session-id",
    manifest.sessionId,
  ];
}

function clampDeadline(value: number | undefined, fallback: number): number {
  const resolved = value ?? fallback;
  if (!Number.isInteger(resolved) || resolved < 30 || resolved > 3600) {
    throw new Error("deadline_seconds must be an integer between 30 and 3600");
  }
  return resolved;
}

export function workerRuntime(executable = process.execPath): string {
  const name = basename(executable).toLowerCase();
  return name === "node" || name.startsWith("node-") || name === "bun" ? executable : "node";
}

function launch(
  context: RunnerContext,
  input: {
    role: ClaudeRole;
    runId: string;
    workingDirectory: string;
    sourcePath: string;
    sourceText: string;
    contextPaths: string[];
    workOrderPath?: string;
    proofCommand?: string;
    profile: ClaudeProfile;
    deadlineSeconds: number;
    sessionId?: string;
    parentHandle?: string;
  },
): Record<string, unknown> {
  assertRunId(input.runId);
  const attemptId = randomUUID();
  const handle = `${input.runId}:${attemptId}`;
  const directory = attemptDirectory(context, input.runId, attemptId);
  mkdirSync(directory, { recursive: true, mode: 0o700 });

  const readOnly = READONLY_ROLES.has(input.role);
  const binaries = readOnly ? [] : proofBinaries(input.proofCommand);
  const availableTools = readOnly
    ? ["Read", "Grep", "Glob"]
    : ["Read", "Grep", "Glob", "Edit", "Write", ...(binaries.length ? ["Bash"] : [])];
  const allowedTools = readOnly
    ? ["Read", "Grep", "Glob"]
    : [
        "Read",
        "Grep",
        "Glob",
        "Edit(./**)",
        "Write(./**)",
        ...binaries.map((binary) => `Bash(${binary}:*)`),
      ];
  const prompt = buildPrompt(input);
  const promptPath = resolve(directory, "prompt.md");
  const stdoutPath = resolve(directory, "stdout.json");
  const stderrPath = resolve(directory, "stderr.log");
  const statusPath = resolve(directory, "status.json");
  const processPath = resolve(directory, "process.json");
  writeFileSync(promptPath, prompt, { mode: 0o600 });

  const manifestBase = {
    profile: input.profile,
    availableTools,
    allowedTools,
    sessionId: input.sessionId ?? randomUUID(),
  };
  const manifest: Manifest = {
    version: 1,
    handle,
    runId: input.runId,
    attemptId,
    parentHandle: input.parentHandle,
    transport: input.parentHandle ? "cli-resume" : "cli-exec",
    role: input.role,
    readOnly,
    workingDirectory: input.workingDirectory,
    promptPath,
    sourcePath: input.sourcePath,
    contextPaths: input.contextPaths,
    workOrderPath: input.workOrderPath,
    proofCommand: input.proofCommand,
    ...manifestBase,
    cliArguments: cliArguments(manifestBase, Boolean(input.parentHandle)),
    stdoutPath,
    stderrPath,
    statusPath,
    processPath,
    deadlineSeconds: input.deadlineSeconds,
    promptSha256: sha256(prompt),
    startedAt: new Date().toISOString(),
  };
  const manifestPath = resolve(directory, "manifest.json");
  writeJson(manifestPath, manifest);
  writeJson(statusPath, { state: "queued", startedAt: manifest.startedAt } satisfies Status);

  const child = spawn(workerRuntime(), [WORKER_PATH, manifestPath], {
    cwd: input.workingDirectory,
    detached: true,
    stdio: "ignore",
    env: sanitizeClaudeEnvironment(process.env),
  });
  if (!child.pid) throw new Error("Could not start the Claude worker process");
  writeJson(processPath, { workerPid: child.pid, startedAt: manifest.startedAt });
  child.unref();

  return {
    status: "SPAWNED",
    handle,
    transport: manifest.transport,
    session_id: manifest.sessionId,
    role: input.role,
    model: input.profile.model,
    effort: input.profile.effort,
    read_only: readOnly,
    deadline_seconds: input.deadlineSeconds,
    receipt_dir: directory,
  };
}

export async function spawnReadonly(context: RunnerContext, input: SpawnBase): Promise<Record<string, unknown>> {
  if (!READONLY_ROLES.has(input.role)) throw new Error(`Role is not read-only: ${input.role}`);
  const workingDirectory = resolveWorkingDirectory(input.workingDir, context);
  const roots = contextRoots(context);
  const sourcePath = resolveInputFile(input.promptPath, workingDirectory, roots);
  const contextPaths = (input.contextPaths ?? []).map((path) => resolveInputFile(path, workingDirectory, roots));
  return launch(context, {
    role: input.role,
    runId: input.runId,
    workingDirectory,
    sourcePath,
    sourceText: readFileSync(sourcePath, "utf8"),
    contextPaths,
    profile: resolveClaudeProfile(input.role, input.complexity, input.highRisk),
    deadlineSeconds: clampDeadline(input.deadlineSeconds, input.role === "counter-plan" ? 300 : 600),
  });
}

export async function spawnImplementation(context: RunnerContext, input: SpawnImplement): Promise<Record<string, unknown>> {
  if (!new Set(["conductor", "repo-worker"]).has(context.agent)) {
    throw new Error(`claude_implement_spawn is not available to agent ${context.agent}`);
  }
  const workingDirectory = resolveWorkingDirectory(input.workingDir, context);
  const roots = contextRoots(context);
  const workOrderPath = resolveInputFile(input.workOrderPath, workingDirectory, roots);
  const contextPaths = (input.contextPaths ?? []).map((path) => resolveInputFile(path, workingDirectory, roots));
  const plansRoot = resolve(workingDirectory, ".plans");
  if (context.agent === "conductor" && !isWithin(plansRoot, workOrderPath)) {
    await context.ask({
      permission: "claude_implement_spawn",
      patterns: [workOrderPath, workingDirectory],
      always: [],
      metadata: { reason: "Claude will receive workspace-write access for an ad hoc work order" },
    });
  }
  return launch(context, {
    role: "implement",
    runId: input.runId,
    workingDirectory,
    sourcePath: workOrderPath,
    sourceText: readFileSync(workOrderPath, "utf8"),
    contextPaths,
    workOrderPath,
    proofCommand: input.proofCommand,
    profile: resolveClaudeProfile("implement", input.complexity, input.highRisk),
    deadlineSeconds: clampDeadline(input.deadlineSeconds, 1800),
  });
}

function readStatus(manifest: Manifest): Status {
  if (!existsSync(manifest.statusPath)) return { state: "queued" };
  return JSON.parse(readFileSync(manifest.statusPath, "utf8")) as Status;
}

function terminate(manifest: Manifest): void {
  if (!existsSync(manifest.processPath)) return;
  const processInfo = JSON.parse(readFileSync(manifest.processPath, "utf8")) as { workerPid?: number };
  if (!processInfo.workerPid) return;
  try {
    const command = execFileSync("ps", ["-o", "command=", "-p", String(processInfo.workerPid)], {
      encoding: "utf8",
    });
    const manifestPath = resolve(dirname(manifest.processPath), "manifest.json");
    if (!command.includes(WORKER_PATH) || !command.includes(manifestPath)) return;
  } catch {
    return;
  }
  try {
    process.kill(-processInfo.workerPid, "SIGTERM");
  } catch {
    try {
      process.kill(processInfo.workerPid, "SIGTERM");
    } catch {
      // The verified worker already exited.
    }
  }
}

function providerReceipt(payload: Record<string, unknown>): {
  provider: "firstParty" | "unverified" | "non-first-party";
  providers: string[];
} {
  const usage = payload.modelUsage;
  if (!usage || typeof usage !== "object") return { provider: "unverified", providers: [] };
  const providers = [...new Set(Object.values(usage as Record<string, { provider?: unknown }>).map((item) => item?.provider).filter((value): value is string => typeof value === "string"))];
  if (providers.length > 0 && providers.every((provider) => provider === "firstParty")) {
    return { provider: "firstParty", providers };
  }
  return { provider: providers.length ? "non-first-party" : "unverified", providers };
}

export function classifyClaudeOutput(status: Status, stdout: string, stderr: string): Record<string, unknown> {
  let payload: Record<string, unknown> | undefined;
  try {
    payload = stdout.trim() ? JSON.parse(stdout) as Record<string, unknown> : undefined;
  } catch {
    return {
      state: "INVALID",
      reason: "non-json-output",
      exit_code: status.exitCode,
      stderr: stderr.slice(-4000),
    };
  }
  const provider = payload ? providerReceipt(payload) : { provider: "unverified" as const, providers: [] };
  const result = typeof payload?.result === "string" ? payload.result : "";
  if (status.state === "timed_out") {
    return { state: "UNAVAILABLE", reason: "deadline-exceeded", exit_code: status.exitCode };
  }
  if (status.state !== "completed" || status.exitCode !== 0 || payload?.is_error === true) {
    return {
      state: "UNAVAILABLE",
      reason: /not logged in|login|oauth/i.test(`${result}\n${stderr}`) ? "official-auth-unavailable" : "claude-cli-failed",
      exit_code: status.exitCode,
      provider: provider.provider,
      error: (result || stderr).slice(-4000),
    };
  }
  if (provider.provider !== "firstParty") {
    return {
      state: "UNAVAILABLE",
      reason: provider.provider === "non-first-party" ? "non-first-party-provider" : "provider-unverified",
      providers: provider.providers,
    };
  }
  return {
    state: "READY",
    provider: "firstParty",
    result: result.length > 60_000 ? `${result.slice(0, 60_000)}\n[truncated; see stdout_path]` : result,
    session_id: payload?.session_id,
    usage: payload?.usage,
    model_usage: payload?.modelUsage,
  };
}

function delay(milliseconds: number, abort: AbortSignal): Promise<void> {
  return new Promise((resolvePromise, reject) => {
    const onDone = () => {
      abort.removeEventListener("abort", onAbort);
      resolvePromise();
    };
    const timer = setTimeout(onDone, milliseconds);
    const onAbort = () => {
      clearTimeout(timer);
      abort.removeEventListener("abort", onAbort);
      reject(new Error("OpenCode session aborted while waiting for Claude"));
    };
    if (abort.aborted) onAbort();
    else abort.addEventListener("abort", onAbort, { once: true });
  });
}

export async function collectClaude(
  context: RunnerContext,
  input: { handle: string; wait?: boolean; deadlineSeconds?: number },
): Promise<Record<string, unknown>> {
  const manifest = loadManifest(context, input.handle);
  const wait = input.wait ?? false;
  const waitDeadline = clampDeadline(input.deadlineSeconds, manifest.deadlineSeconds);
  const expiresAt = Date.now() + waitDeadline * 1000;
  let status = readStatus(manifest);
  while (wait && ["queued", "running"].includes(status.state) && Date.now() < expiresAt) {
    await delay(250, context.abort);
    status = readStatus(manifest);
  }
  if (["queued", "running"].includes(status.state)) {
    if (wait) {
      terminate(manifest);
      return {
        state: "UNAVAILABLE",
        reason: "collect-deadline-exceeded",
        handle: manifest.handle,
        receipt_dir: dirname(manifest.stdoutPath),
      };
    }
    return {
      state: "RUNNING",
      handle: manifest.handle,
      role: manifest.role,
      transport: manifest.transport,
      model: manifest.profile.model,
      effort: manifest.profile.effort,
      started_at: manifest.startedAt,
    };
  }
  if (!existsSync(manifest.promptPath) || sha256(readFileSync(manifest.promptPath, "utf8")) !== manifest.promptSha256) {
    return {
      state: "INVALID",
      reason: "prompt-integrity-mismatch",
      handle: manifest.handle,
      receipt_dir: dirname(manifest.stdoutPath),
    };
  }
  const stdout = existsSync(manifest.stdoutPath) ? readFileSync(manifest.stdoutPath, "utf8") : "";
  const stderr = existsSync(manifest.stderrPath) ? readFileSync(manifest.stderrPath, "utf8") : "";
  return {
    ...classifyClaudeOutput(status, stdout, stderr),
    handle: manifest.handle,
    role: manifest.role,
    transport: manifest.transport,
    model: manifest.profile.model,
    effort: manifest.profile.effort,
    prompt_sha256: manifest.promptSha256,
    stdout_path: manifest.stdoutPath,
    stderr_path: manifest.stderrPath,
    receipt_dir: dirname(manifest.stdoutPath),
  };
}

export async function resumeClaude(
  context: RunnerContext,
  input: { handle: string; deltaPath: string; deadlineSeconds?: number },
): Promise<Record<string, unknown>> {
  const previous = loadManifest(context, input.handle);
  const previousStatus = readStatus(previous);
  if (["queued", "running"].includes(previousStatus.state)) {
    throw new Error("Cannot resume a Claude run that is still active");
  }
  if (!previous.readOnly && !new Set(["conductor", "repo-worker"]).has(context.agent)) {
    throw new Error(`Cannot resume a writer run from agent ${context.agent}`);
  }
  const roots = contextRoots(context);
  const deltaPath = resolveInputFile(input.deltaPath, previous.workingDirectory, roots);
  return launch(context, {
    role: previous.role,
    runId: previous.runId,
    workingDirectory: previous.workingDirectory,
    sourcePath: deltaPath,
    sourceText: readFileSync(deltaPath, "utf8"),
    contextPaths: previous.contextPaths,
    workOrderPath: previous.workOrderPath,
    proofCommand: previous.proofCommand,
    profile: previous.profile,
    deadlineSeconds: clampDeadline(input.deadlineSeconds, previous.deadlineSeconds),
    sessionId: previous.sessionId,
    parentHandle: previous.handle,
  });
}
