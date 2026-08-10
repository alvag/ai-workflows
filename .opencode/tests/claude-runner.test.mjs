import assert from "node:assert/strict";
import { chmodSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import {
  classifyClaudeOutput,
  collectClaude,
  proofBinaries,
  resolveClaudeProfile,
  resumeClaude,
  sanitizeClaudeEnvironment,
  spawnImplementation,
  spawnReadonly,
  stripFrontmatter,
  workerRuntime,
} from "../lib/claude-runner.ts";

const completed = { state: "completed", exitCode: 0 };

test("Claude profile policy is role-driven and escalates complex work", () => {
  assert.deepEqual(resolveClaudeProfile("explore"), { model: "claude-sonnet-5", effort: "medium" });
  assert.deepEqual(resolveClaudeProfile("implement"), { model: "claude-sonnet-5", effort: "high" });
  assert.deepEqual(resolveClaudeProfile("pr"), { model: "claude-opus-5", effort: "xhigh" });
  assert.deepEqual(resolveClaudeProfile("explore", "complex"), { model: "claude-opus-5", effort: "xhigh" });
  assert.deepEqual(resolveClaudeProfile("implement", "normal", true), { model: "claude-opus-5", effort: "xhigh" });
});

test("Compiled OpenCode launches the worker with Node, not its own binary", () => {
  assert.equal(workerRuntime("/opt/opencode/bin/opencode"), "node");
  assert.equal(workerRuntime("/usr/local/bin/node"), "/usr/local/bin/node");
  assert.equal(workerRuntime("/usr/local/bin/bun"), "/usr/local/bin/bun");
});

test("Claude environment removes alternate providers but keeps OAuth and basics", () => {
  const result = sanitizeClaudeEnvironment({
    PATH: "/bin",
    HOME: "/tmp/home",
    ANTHROPIC_BASE_URL: "http://127.0.0.1:3456",
    ANTHROPIC_API_KEY: "secret",
    MERIDIAN_TOKEN: "secret",
    CLAUDE_CODE_USE_BEDROCK: "1",
    CLAUDE_CODE_OAUTH_TOKEN: "official-oauth",
  });
  assert.equal(result.PATH, "/bin");
  assert.equal(result.CLAUDE_CODE_OAUTH_TOKEN, "official-oauth");
  assert.equal(result.ANTHROPIC_BASE_URL, undefined);
  assert.equal(result.ANTHROPIC_API_KEY, undefined);
  assert.equal(result.MERIDIAN_TOKEN, undefined);
  assert.equal(result.CLAUDE_CODE_USE_BEDROCK, undefined);
});

test("Proof command grants only supported executable families", () => {
  assert.deepEqual(proofBinaries("npm test && npx vitest run"), ["npm", "npx"]);
  assert.throws(() => proofBinaries("rm -rf ."), /Unsupported proof binary/);
  assert.throws(() => proofBinaries("npm test $(whoami)"), /command substitution/);
});

test("Frontmatter is excluded from the reusable role contract", () => {
  assert.equal(stripFrontmatter("---\nmodel: x\n---\n\n# Body\n"), "# Body");
});

test("Collector accepts only first-party Claude output", () => {
  const ready = classifyClaudeOutput(completed, JSON.stringify({
    result: "OK",
    is_error: false,
    session_id: "session",
    modelUsage: { "claude-sonnet-5": { provider: "firstParty" } },
  }), "");
  assert.equal(ready.state, "READY");
  assert.equal(ready.provider, "firstParty");

  const rejected = classifyClaudeOutput(completed, JSON.stringify({
    result: "API answer",
    is_error: false,
    modelUsage: { "claude-sonnet-5": { provider: "apiKey" } },
  }), "");
  assert.equal(rejected.state, "UNAVAILABLE");
  assert.equal(rejected.reason, "non-first-party-provider");

  const unauthenticated = classifyClaudeOutput(
    { state: "failed", exitCode: 1 },
    JSON.stringify({ result: "Not logged in · Please run /login", is_error: true }),
    "",
  );
  assert.equal(unauthenticated.reason, "official-auth-unavailable");
});

test("Spawn is nonblocking and collect reads a durable first-party receipt", async () => {
  const root = mkdtempSync(join(tmpdir(), "opencode-claude-runner-"));
  const bin = join(root, "bin");
  mkdirSync(bin);
  const fakeClaude = join(bin, "claude");
  writeFileSync(fakeClaude, `#!/bin/sh\ncat >/dev/null\nprintf '%s' '{"result":"FAKE_OK","session_id":"fake-session","is_error":false,"usage":{"input_tokens":1},"modelUsage":{"claude-sonnet-5":{"provider":"firstParty"}}}'\n`);
  chmodSync(fakeClaude, 0o755);
  const prompt = join(root, "prompt.md");
  writeFileSync(prompt, "Map the fixture.");
  const previousPath = process.env.PATH;
  process.env.PATH = `${bin}:${previousPath}`;
  const context = {
    agent: "conductor",
    directory: root,
    worktree: root,
    abort: new AbortController().signal,
    ask: async () => { throw new Error("unexpected permission prompt"); },
    metadata: () => {},
  };
  try {
    const launched = await spawnReadonly(context, {
      role: "explore",
      promptPath: prompt,
      workingDir: root,
      runId: "test-run",
      deadlineSeconds: 30,
    });
    assert.equal(launched.status, "SPAWNED");
    const receipt = await collectClaude(context, {
      handle: String(launched.handle),
      wait: true,
      deadlineSeconds: 30,
    });
    assert.equal(receipt.state, "READY");
    assert.equal(receipt.provider, "firstParty");
    assert.equal(receipt.result, "FAKE_OK");
    const manifest = JSON.parse(readFileSync(join(String(launched.receipt_dir), "manifest.json"), "utf8"));
    assert.equal(manifest.transport, "cli-exec");
    assert.equal(manifest.cliArguments.includes("--safe-mode"), true);
    assert.equal(manifest.cliArguments.includes("--permission-mode"), true);
    assert.equal(manifest.cliArguments.includes("--session-id"), true);
    assert.equal(manifest.cliArguments.some((arg) => arg === "--allowedTools=Read,Grep,Glob"), true);

    const delta = join(root, "delta.md");
    writeFileSync(delta, "Challenge the first answer.");
    const resumed = await resumeClaude(context, {
      handle: String(launched.handle),
      deltaPath: delta,
      deadlineSeconds: 30,
    });
    const resumedReceipt = await collectClaude(context, {
      handle: String(resumed.handle),
      wait: true,
      deadlineSeconds: 30,
    });
    assert.equal(resumedReceipt.state, "READY");
    assert.equal(resumedReceipt.transport, "cli-resume");
    const resumedManifest = JSON.parse(readFileSync(join(String(resumed.receipt_dir), "manifest.json"), "utf8"));
    assert.equal(resumedManifest.sessionId, manifest.sessionId);
    assert.equal(resumedManifest.cliArguments.includes("--resume"), true);

    const plans = join(root, ".plans");
    mkdirSync(plans);
    const workOrder = join(plans, "work-order.md");
    writeFileSync(workOrder, "Implement the fixture without changing scope.");
    const writer = await spawnImplementation(context, {
      workOrderPath: workOrder,
      workingDir: root,
      runId: "writer-run",
      proofCommand: "npm test",
      deadlineSeconds: 30,
    });
    const writerReceipt = await collectClaude(context, {
      handle: String(writer.handle),
      wait: true,
      deadlineSeconds: 30,
    });
    assert.equal(writerReceipt.state, "READY");
    const writerManifest = JSON.parse(readFileSync(join(String(writer.receipt_dir), "manifest.json"), "utf8"));
    assert.equal(writerManifest.readOnly, false);
    assert.equal(writerManifest.allowedTools.includes("Edit(./**)"), true);
    assert.equal(writerManifest.allowedTools.includes("Write(./**)"), true);
    assert.equal(writerManifest.allowedTools.includes("Bash(npm:*)"), true);

    await assert.rejects(
      spawnImplementation({ ...context, agent: "explorer" }, {
        workOrderPath: workOrder,
        workingDir: root,
        runId: "unauthorized-writer",
      }),
      /not available to agent explorer/,
    );
  } finally {
    process.env.PATH = previousPath;
    rmSync(root, { recursive: true, force: true });
  }
});
