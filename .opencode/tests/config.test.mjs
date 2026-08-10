import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import test from "node:test";

const root = resolve(import.meta.dirname, "..");

function files(directory, extension) {
  return readdirSync(join(root, directory)).filter((name) => name.endsWith(extension)).sort();
}

test("Agent and command layout is flat", () => {
  assert.equal(existsSync(join(root, "agents", "sdd")), false);
  assert.equal(existsSync(join(root, "command", "sdd")), false);
  assert.deepEqual(files("agents", ".md"), [
    "builder.md",
    "code-reviewer.md",
    "conductor.md",
    "explorer.md",
    "investigator.md",
    "repo-worker.md",
  ]);
  assert.deepEqual(files("command", ".md"), [
    "bitbucket-code-review.md",
    "sdd-orchestrator.md",
    "sdd-pr-feedback.md",
    "sdd.md",
  ]);
});

test("Pinned execution profiles and Claude tool surface are explicit", () => {
  const conductor = readFileSync(join(root, "agents", "conductor.md"), "utf8");
  assert.match(conductor, /model: openai\/gpt-5\.6-sol/);
  assert.match(conductor, /variant: xhigh/);
  const terraProfiles = {
    "explorer.md": "high",
    "investigator.md": "xhigh",
    "builder.md": "high",
    "code-reviewer.md": "high",
    "repo-worker.md": "high",
  };
  for (const [name, effort] of Object.entries(terraProfiles)) {
    const source = readFileSync(join(root, "agents", name), "utf8");
    assert.match(source, /model: openai\/gpt-5\.6-terra/);
    assert.match(source, new RegExp(`variant: ${effort}`));
  }
  assert.deepEqual(files("tools", ".ts"), [
    "claude_collect.ts",
    "claude_implement_spawn.ts",
    "claude_readonly_spawn.ts",
    "claude_resume.ts",
  ]);
});

test("Retired roster and probe files are absent", () => {
  for (const path of [
    "agent-roster.json",
    "model-families.json",
    "agents/claude-cli-probe.md",
  ]) assert.equal(existsSync(join(root, path)), false, path);
});
