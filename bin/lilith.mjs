#!/usr/bin/env node
// Lilith installer: puts the skill where your coding agents find it.
import { spawnSync } from "node:child_process";
import { readFileSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { agentTable } from "../src/agents.mjs";
import { installTo, planTargets, selectAgents, uninstallFrom, SKILL_NAME } from "../src/install.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SKILL_DIR = join(ROOT, "skills", SKILL_NAME);
const SCANNER = join(SKILL_DIR, "scripts", "lilith_scan.py");
const AGENT_IDS = Object.keys(agentTable({}, "~"));

const HELP = `Lilith: security check for vibecoded apps

Usage:
  npx lilith-skill                 install for every agent found on this machine
  npx lilith-skill install [opts]  same, with options
  npx lilith-skill uninstall       remove it again
  npx lilith-skill scan [path]     run the quick scan (needs Python 3.8+)
  npx lilith-skill agents          list supported agents and where they look

Options:
  -a, --agent <id>   only this agent (repeatable): ${AGENT_IDS.join(", ")}
  -p, --project      install into the current project instead of your home folder
  -f, --force        replace a folder named "${SKILL_NAME}" that is not Lilith
  -h, --help         show this help
  -v, --version      show the version

Then open your project and tell your AI /${SKILL_NAME}.`;

const OPTIONS = {
  agent: { type: "string", short: "a", multiple: true, default: [] },
  project: { type: "boolean", short: "p", default: false },
  force: { type: "boolean", short: "f", default: false },
  help: { type: "boolean", short: "h", default: false },
  version: { type: "boolean", short: "v", default: false },
};

function version() {
  return JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")).version;
}

function splitAgents(values) {
  return values.flatMap((v) => v.split(",")).map((v) => v.trim()).filter(Boolean);
}

function describe(result) {
  const where = `${result.dir}  (${result.agents.join(", ")})`;
  const reason = result.reason ? `: ${result.reason}` : "";
  return `  ${result.status.padEnd(9)} ${where}${reason}`;
}

function targetsFor(opts, ctx) {
  const table = agentTable(ctx.env, ctx.home);
  const ids = selectAgents(table, splitAgents(opts.agent));
  if (ids.length === 0) {
    ctx.out.error(
      "No coding agent found in your home folder.\n" +
        `Pick one: npx lilith-skill --agent claude   (known: ${AGENT_IDS.join(", ")})`
    );
    return null;
  }
  return planTargets(table, ids, { project: opts.project, cwd: ctx.cwd });
}

function runInstall(opts, ctx) {
  const targets = targetsFor(opts, ctx);
  if (!targets) return 1;
  const results = targets.map((t) => installTo(SKILL_DIR, t, { force: opts.force }));
  ctx.out.log(`Lilith ${version()}`);
  results.forEach((r) => ctx.out.log(describe(r)));
  const ok = results.some((r) => r.status !== "skipped");
  if (ok) ctx.out.log(`\nDone. Open your project and tell your AI /${SKILL_NAME}`);
  return ok ? 0 : 1;
}

function runUninstall(opts, ctx) {
  const targets = targetsFor(opts, ctx);
  if (!targets) return 1;
  targets.map(uninstallFrom).forEach((r) => ctx.out.log(describe(r)));
  return 0;
}

function runAgents(ctx) {
  const table = agentTable(ctx.env, ctx.home);
  for (const [id, a] of Object.entries(table)) {
    ctx.out.log(`  ${id.padEnd(9)} ${a.name.padEnd(15)} ${a.globalDir}  (project: ${a.projectDir})`);
  }
  return 0;
}

function runScan(args, ctx) {
  const candidates = process.platform === "win32" ? ["py", "python", "python3"] : ["python3", "python"];
  for (const py of candidates) {
    const res = spawnSync(py, [SCANNER, ...args], { stdio: "inherit" });
    if (res.error?.code === "ENOENT") continue;
    if (res.error) {
      ctx.out.error(`Could not run ${py}: ${res.error.message}`);
      return 1;
    }
    return res.status ?? 1;
  }
  ctx.out.error(
    "The quick scan needs Python 3.8+ (python.org). Without it, /lilith still works: the agent checks by reading."
  );
  return 1;
}

function dispatch(command, rest, ctx) {
  if (command === "scan") return runScan(rest, ctx);
  const opts = parseArgs({ args: rest, options: OPTIONS, allowPositionals: false }).values;
  if (opts.help || command === "help") return ctx.out.log(HELP), 0;
  if (opts.version) return ctx.out.log(version()), 0;
  if (command === "install") return runInstall(opts, ctx);
  if (command === "uninstall") return runUninstall(opts, ctx);
  if (command === "agents") return runAgents(ctx);
  ctx.out.error(`Unknown command: ${command}\n\n${HELP}`);
  return 2;
}

export function main(argv, overrides = {}) {
  const ctx = { env: process.env, home: homedir(), cwd: process.cwd(), out: console, ...overrides };
  const words = argv.length === 0 || argv[0].startsWith("-") ? ["install", ...argv] : argv;
  const [command, ...rest] = words;
  try {
    return dispatch(command, rest, ctx);
  } catch (err) {
    const usage = err.code?.startsWith("ERR_PARSE_ARGS") ? `\n\n${HELP}` : "";
    ctx.out.error(`Error: ${err.message}${usage}`);
    return usage ? 2 : 1;
  }
}

function isEntryPoint() {
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isEntryPoint()) process.exitCode = main(process.argv.slice(2));
