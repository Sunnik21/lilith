import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { main } from "../bin/lilith.mjs";
import { agentTable } from "../src/agents.mjs";
import { planTargets, selectAgents } from "../src/install.mjs";

function sandbox() {
  const root = mkdtempSync(join(tmpdir(), "lilith-cli-"));
  const home = join(root, "home");
  const cwd = join(root, "project");
  mkdirSync(home, { recursive: true });
  mkdirSync(cwd, { recursive: true });
  const logs = [];
  const out = { log: (m) => logs.push(m), error: (m) => logs.push(m) };
  const run = (...argv) => main(argv, { env: {}, home, cwd, out });
  return { root, home, cwd, logs, run, cleanup: () => rmSync(root, { recursive: true, force: true }) };
}

test("installs into every detected agent and skips undetected ones", (t) => {
  const s = sandbox();
  t.after(s.cleanup);
  mkdirSync(join(s.home, ".claude"));
  mkdirSync(join(s.home, ".cursor"));

  assert.equal(s.run(), 0);

  for (const dir of [".claude/skills/lilith", ".cursor/skills/lilith"]) {
    const skill = readFileSync(join(s.home, dir, "SKILL.md"), "utf8");
    assert.match(skill, /^name: lilith$/m);
    assert.ok(existsSync(join(s.home, dir, "scripts", "lilith_scan.py")));
    assert.ok(!existsSync(join(s.home, dir, "scripts", "__pycache__")));
  }
  assert.ok(!existsSync(join(s.home, ".gemini")));
});

test("fails with a hint when no agent is detected", (t) => {
  const s = sandbox();
  t.after(s.cleanup);
  assert.equal(s.run("install"), 1);
  assert.match(s.logs.join("\n"), /No coding agent found/);
});

test("--project installs into the project and shares .agents/skills", (t) => {
  const s = sandbox();
  t.after(s.cleanup);

  assert.equal(s.run("install", "--project", "-a", "claude,codex", "-a", "cursor"), 0);

  assert.ok(existsSync(join(s.cwd, ".claude/skills/lilith/SKILL.md")));
  assert.ok(existsSync(join(s.cwd, ".agents/skills/lilith/SKILL.md")));
  assert.ok(!existsSync(join(s.home, ".claude")));
});

test("updates its own copy but never overwrites a foreign folder without --force", (t) => {
  const s = sandbox();
  t.after(s.cleanup);
  const own = join(s.home, ".claude/skills/lilith");
  assert.equal(s.run("-a", "claude"), 0);
  writeFileSync(join(own, "stale.txt"), "old");
  assert.equal(s.run("-a", "claude"), 0);
  assert.ok(!existsSync(join(own, "stale.txt")), "update replaces the old copy");

  const foreign = join(s.home, ".cursor/skills/lilith");
  mkdirSync(foreign, { recursive: true });
  writeFileSync(join(foreign, "SKILL.md"), "---\nname: something-else\n---\n");
  assert.equal(s.run("-a", "cursor"), 1);
  assert.match(readFileSync(join(foreign, "SKILL.md"), "utf8"), /something-else/);

  assert.equal(s.run("-a", "cursor", "--force"), 0);
  assert.match(readFileSync(join(foreign, "SKILL.md"), "utf8"), /^name: lilith$/m);
});

test("uninstall removes only Lilith folders", (t) => {
  const s = sandbox();
  t.after(s.cleanup);
  assert.equal(s.run("-a", "claude"), 0);
  const foreign = join(s.home, ".gemini/skills/lilith");
  mkdirSync(foreign, { recursive: true });
  writeFileSync(join(foreign, "notes.md"), "mine");

  assert.equal(s.run("uninstall", "-a", "claude,gemini"), 0);

  assert.ok(!existsSync(join(s.home, ".claude/skills/lilith")));
  assert.ok(existsSync(join(foreign, "notes.md")));
});

test("rejects unknown agents, options and commands", (t) => {
  const s = sandbox();
  t.after(s.cleanup);
  assert.equal(s.run("-a", "notepad"), 1);
  assert.match(s.logs.join("\n"), /Unknown agent: notepad/);
  assert.equal(s.run("--nope"), 2);
  assert.equal(s.run("frobnicate"), 2);
});

test("help and version print without touching the disk", (t) => {
  const s = sandbox();
  t.after(s.cleanup);
  assert.equal(s.run("--help"), 0);
  assert.match(s.logs.join("\n"), /npx lilith-skill/);
  assert.equal(s.run("-v"), 0);
  assert.match(s.logs.at(-1), /^\d+\.\d+\.\d+$/);
});

test("agent paths honour CLAUDE_CONFIG_DIR, CODEX_HOME and XDG_CONFIG_HOME", () => {
  const table = agentTable(
    { CLAUDE_CONFIG_DIR: "/c", CODEX_HOME: "/x", XDG_CONFIG_HOME: "/cfg" },
    "/h"
  );
  assert.equal(table.claude.globalDir, join("/c", "skills"));
  assert.equal(table.codex.detectDir, "/x");
  assert.equal(table.opencode.globalDir, join("/cfg", "opencode", "skills"));
});

test("planTargets merges agents that share a folder", () => {
  const table = agentTable({}, "/h");
  const found = new Set([join("/h", ".cursor"), join("/h", ".gemini")]);
  assert.deepEqual(selectAgents(table, [], (dir) => found.has(dir)), ["cursor", "gemini"]);
  const targets = planTargets(table, ["codex", "cursor", "claude"], { project: true, cwd: "/p" });
  assert.deepEqual(
    targets.map((t) => [t.dir, t.agents]),
    [
      [join("/p", ".agents/skills/lilith"), ["Codex", "Cursor"]],
      [join("/p", ".claude/skills/lilith"), ["Claude Code"]],
    ]
  );
});
