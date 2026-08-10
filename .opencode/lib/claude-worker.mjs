import { spawn } from "node:child_process";
import { closeSync, openSync, readFileSync, renameSync, writeFileSync } from "node:fs";

const manifestPath = process.argv[2];
if (!manifestPath) process.exit(64);
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

function writeJson(path, value) {
  const temporary = `${path}.tmp-${process.pid}`;
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  renameSync(temporary, path);
}

function sanitizedEnvironment() {
  const clean = { ...process.env };
  const exact = new Set([
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
  ]);
  for (const key of Object.keys(clean)) {
    if (key.startsWith("ANTHROPIC_") || key.startsWith("MERIDIAN_") || exact.has(key)) delete clean[key];
  }
  return clean;
}

const startedAt = new Date().toISOString();
writeJson(manifest.statusPath, { state: "running", workerPid: process.pid, startedAt });
const stdoutFd = openSync(manifest.stdoutPath, "w", 0o600);
const stderrFd = openSync(manifest.stderrPath, "w", 0o600);
let child;
let timedOut = false;
let timeout;
let finished = false;

function finish(state, exitCode, signal, error) {
  if (finished) return;
  finished = true;
  if (timeout) clearTimeout(timeout);
  try { closeSync(stdoutFd); } catch {}
  try { closeSync(stderrFd); } catch {}
  writeJson(manifest.statusPath, {
    state,
    workerPid: process.pid,
    claudePid: child?.pid,
    exitCode,
    signal,
    startedAt,
    endedAt: new Date().toISOString(),
    ...(error ? { error } : {}),
  });
}

try {
  child = spawn("claude", manifest.cliArguments, {
    cwd: manifest.workingDirectory,
    env: sanitizedEnvironment(),
    stdio: ["pipe", stdoutFd, stderrFd],
  });
  writeJson(manifest.processPath, { workerPid: process.pid, claudePid: child.pid, startedAt });
  child.stdin.end(readFileSync(manifest.promptPath, "utf8"));
  timeout = setTimeout(() => {
    timedOut = true;
    child.kill("SIGTERM");
    setTimeout(() => child.kill("SIGKILL"), 5000).unref();
  }, manifest.deadlineSeconds * 1000);
  timeout.unref();

  child.once("error", (error) => {
    finish("failed", null, null, error.message);
    process.exitCode = 1;
  });
  child.once("close", (code, signal) => {
    finish(timedOut ? "timed_out" : code === 0 ? "completed" : "failed", code, signal, undefined);
    process.exitCode = code ?? 1;
  });
  for (const signal of ["SIGTERM", "SIGINT"]) {
    process.once(signal, () => {
      child?.kill("SIGTERM");
      finish("terminated", null, signal, undefined);
      process.exit(143);
    });
  }
} catch (error) {
  finish("failed", null, null, error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
