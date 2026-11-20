// Copy the skill folder into agent skill directories, or remove it again.
import { cpSync, existsSync, readFileSync, rmSync, mkdirSync } from "node:fs";
import { basename, join, resolve } from "node:path";

export const SKILL_NAME = "lilith";

const SKIP_NAMES = new Set(["__pycache__", ".DS_Store"]);

// Pick the agents to act on: the ones asked for, or the ones found on this machine.
export function selectAgents(table, requested, existsFn = existsSync) {
  if (requested.length > 0) {
    const unknown = requested.filter((id) => !(id in table));
    if (unknown.length > 0) {
      throw new Error(
        `Unknown agent: ${unknown.join(", ")}. Known: ${Object.keys(table).join(", ")}`
      );
    }
    return requested;
  }
  return Object.keys(table).filter((id) => existsFn(table[id].detectDir));
}

// One target folder per skills directory; several agents can share one.
export function planTargets(table, agentIds, { project, cwd }) {
  const byDir = new Map();
  for (const id of agentIds) {
    const base = project ? resolve(cwd, table[id].projectDir) : table[id].globalDir;
    const dir = join(base, SKILL_NAME);
    const agents = byDir.get(dir) ?? [];
    byDir.set(dir, [...agents, table[id].name]);
  }
  return [...byDir].map(([dir, agents]) => ({ dir, agents }));
}

// True when the folder holds a Lilith skill (safe to replace or remove).
export function isOurSkill(dir) {
  const skillFile = join(dir, "SKILL.md");
  if (!existsSync(skillFile)) return false;
  const head = readFileSync(skillFile, "utf8").slice(0, 500);
  return new RegExp(`^name:\\s*${SKILL_NAME}\\s*$`, "m").test(head);
}

function copySkill(sourceDir, targetDir) {
  mkdirSync(join(targetDir, ".."), { recursive: true });
  cpSync(sourceDir, targetDir, {
    recursive: true,
    filter: (src) => !SKIP_NAMES.has(basename(src)) && !src.endsWith(".pyc"),
  });
}

export function installTo(sourceDir, target, { force }) {
  if (existsSync(target.dir)) {
    if (!isOurSkill(target.dir) && !force) {
      return { ...target, status: "skipped", reason: "folder exists and is not Lilith (use --force)" };
    }
    rmSync(target.dir, { recursive: true, force: true });
    copySkill(sourceDir, target.dir);
    return { ...target, status: "updated" };
  }
  copySkill(sourceDir, target.dir);
  return { ...target, status: "installed" };
}

export function uninstallFrom(target) {
  if (!existsSync(target.dir)) return { ...target, status: "absent" };
  if (!isOurSkill(target.dir)) {
    return { ...target, status: "skipped", reason: "folder is not Lilith, left as is" };
  }
  rmSync(target.dir, { recursive: true, force: true });
  return { ...target, status: "removed" };
}
