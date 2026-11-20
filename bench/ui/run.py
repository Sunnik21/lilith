#!/usr/bin/env python3
"""Cleanup evals: run a skill on small fixtures with `claude -p` and check what it did.

The UI fixtures (fixtures/, expect.json) and the checker logic are derived
from MIT-licensed work (see LICENSE-third-party). They check
the half a counter can't see: what has to survive (real state, accessible
names, a clean screen, text owned by a translation file) and that nothing is
invented. code-fixtures/ and code-expect.json are Lilith's own, for code
cleanup (C1 to C6): a real console.error, a mock the UI still imports, a
component loaded by a dynamic import.

Each run copies a fixture to a temp folder, installs the skill into its
.claude/skills/, and runs the skill's slash command headlessly with edits
allowed. User-level settings are not loaded (--setting-sources project,local).

Not in CI: it needs the Claude Code CLI, costs money and varies between runs.

Usage:
  python3 bench/ui/run.py --skill lilith                 UI + code fixtures with Lilith
  python3 bench/ui/run.py --skill external --external-dir /path/to/skills/<name>   UI fixtures with another skill
  python3 bench/ui/run.py --skill lilith form claims     only these fixtures
  python3 bench/ui/run.py --check DIR --skill lilith     check copies already edited in DIR
Results are appended to bench/UI_RESULTS.md with date and model.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
LILITH_SKILL = os.path.normpath(os.path.join(HERE, "..", "..", "skills", "lilith"))
RESULTS_MD = os.path.join(HERE, "..", "UI_RESULTS.md")
SUITES = {
    "ui": (os.path.join(HERE, "fixtures"), os.path.join(HERE, "expect.json")),
    "code": (os.path.join(HERE, "code-fixtures"), os.path.join(HERE, "code-expect.json")),
}
PROMPTS = {
    "lilith": "/lilith clean .\n\nThe owner has already agreed to apply the cleanup edits in this folder. Do not ask; edit, then report.",
}
SKILLS = ["external", "lilith"]
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
TIMEOUT_SECONDS = 900


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def check_file(before: str, after: str, spec: dict) -> List[str]:
    """Failures for one file, as short strings (same rules as the original checker)."""
    if spec.get("unchanged"):
        return [] if before == after else ["changed, expected no edit"]
    failures = ["lost {!r}".format(s) for s in spec.get("keep", []) if s not in after]
    failures += ["lost /{}/".format(p) for p in spec.get("keep_regex", []) if not re.search(p, after)]
    failures += ["still has {!r}".format(s) for s in spec.get("cut", []) if s in after]
    failures += ["still has /{}/".format(p) for p in spec.get("cut_regex", []) if re.search(p, after)]
    if spec.get("no_new_numbers"):
        invented = sorted(set(NUMBER.findall(after)) - set(NUMBER.findall(before)))
        if invented:
            failures.append("new numbers {}".format(", ".join(invented)))
    if spec.get("valid_json"):
        try:
            json.loads(after)
        except ValueError as exc:
            failures.append("invalid JSON: {}".format(exc))
    return failures


def check_fixture(fixtures: str, name: str, spec: dict, after_dir: str, report: str) -> Dict[str, List[str]]:
    failed: Dict[str, List[str]] = {}
    for filename, file_spec in spec["files"].items():
        after_path = os.path.join(after_dir, filename)
        if not os.path.exists(after_path):
            failed[filename] = ["file deleted"]
            continue
        failures = check_file(read(os.path.join(fixtures, name, filename)), read(after_path), file_spec)
        if failures:
            failed[filename] = failures
    missing = [s for s in spec.get("report_has", []) if s not in report]
    if missing:
        failed["report"] = ["does not mention {!r}".format(s) for s in missing]
    return failed


def skill_source(skill: str, external_dir: Optional[str]) -> str:
    """Folder holding the skill's SKILL.md. An external skill is invoked by its folder name."""
    src = LILITH_SKILL if skill == "lilith" else os.path.normpath(external_dir or "")
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        raise SystemExit(f"no SKILL.md in skill folder: {src}")
    return src


def prompt_for(skill: str, external_dir: Optional[str]) -> str:
    if skill == "lilith":
        return PROMPTS["lilith"]
    return f"/{os.path.basename(skill_source(skill, external_dir))} ."


def install_skill(target: str, skill: str, external_dir: Optional[str]) -> None:
    src = skill_source(skill, external_dir)
    shutil.copytree(src, os.path.join(target, ".claude", "skills", os.path.basename(src)))


def run_agent(skill: str, fixtures: str, name: str, workdir: str, model: Optional[str],
              external_dir: Optional[str]) -> Tuple[int, str, dict]:
    target = os.path.join(workdir, name)
    shutil.copytree(os.path.join(fixtures, name), target)
    install_skill(target, skill, external_dir)
    cmd = ["claude", "-p", prompt_for(skill, external_dir), "--output-format", "json", "--permission-mode", "acceptEdits",
           "--setting-sources", "project,local", "--no-session-persistence",
           "--allowedTools", "Read,Edit,Write,Grep,Glob,Bash(python3:*),Bash(ls:*),Bash(grep:*)"]
    if model:
        cmd += ["--model", model]
    try:
        proc = subprocess.run(cmd, cwd=target, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
        data = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
        report, code = data.get("result", proc.stdout + proc.stderr), proc.returncode
    except subprocess.TimeoutExpired:
        data, report, code = {}, f"Timed out after {TIMEOUT_SECONDS}s", 1
    with open(os.path.join(workdir, name + ".report.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    shutil.rmtree(os.path.join(target, ".claude"), ignore_errors=True)
    return code, report, data


def main_model(runs: List[dict]) -> str:
    models = set()
    for data in runs:
        usage = data.get("modelUsage") or {}
        if usage:
            models.add(max(usage.items(), key=lambda kv: kv[1].get("costUSD", 0))[0])
    return ", ".join(sorted(models)) or "unknown"


def write_results(skill: str, rows: List[Tuple[str, str, Dict[str, List[str]]]], model: str, cost: float) -> None:
    lines = [f"## {skill}: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}, {model}, ${cost:.2f}", "",
             "| Suite | Fixture | Result | Failures |", "|---|---|---|---|"]
    for suite, name, failed in rows:
        detail = "; ".join(f"{f}: {', '.join(v)}" for f, v in failed.items()).replace("|", "\\|")
        lines.append(f"| {suite} | {name} | {'FAIL' if failed else 'pass'} | {detail} |")
    passed = sum(1 for _s, _n, f in rows if not f)
    lines += ["", f"Passed {passed} of {len(rows)}.", ""]
    header = "" if os.path.exists(RESULTS_MD) else (
        "# Cleanup eval results\n\nWritten by `python3 bench/ui/run.py`. One run per fixture; results vary "
        "between runs.\n\n")
    with open(RESULTS_MD, "a", encoding="utf-8") as fh:
        fh.write(header + "\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a cleanup skill on the eval fixtures and check the result")
    ap.add_argument("fixtures", nargs="*", help="fixture names (default: all for the skill)")
    ap.add_argument("--skill", choices=SKILLS, default="lilith")
    ap.add_argument("--external-dir", help="folder of another skill (with SKILL.md), for --skill external")
    ap.add_argument("--model", help="model passed to claude --model")
    ap.add_argument("--check", metavar="DIR", help="skip the agent and check edited copies in DIR/<fixture>/")
    args = ap.parse_args()

    suites = ["ui", "code"] if args.skill == "lilith" else ["ui"]
    jobs = []
    for suite in suites:
        fixtures, expect_path = SUITES[suite]
        expect = json.load(open(expect_path, encoding="utf-8"))
        jobs += [(suite, fixtures, n, expect[n]) for n in sorted(expect) if not args.fixtures or n in args.fixtures]
    if not jobs:
        ap.error("no matching fixtures")
    if not args.check and not shutil.which("claude"):
        print("SKIP: the claude CLI is not installed; the eval did not run.")
        return

    workdir = args.check or tempfile.mkdtemp(prefix=f"lilith-ui-eval-{args.skill}-")
    results: Dict[str, Tuple[int, str, dict]] = {}
    if not args.check:
        print(f"Running {args.skill} on {len(jobs)} fixtures in {workdir}", file=sys.stderr)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {name: pool.submit(run_agent, args.skill, fx, name, workdir, args.model, args.external_dir)
                       for _s, fx, name, _e in jobs}
            results = {name: f.result() for name, f in futures.items()}

    rows = []
    for suite, fixtures, name, spec in jobs:
        report_path = os.path.join(workdir, name + ".report.md")
        report = results[name][1] if name in results else (read(report_path) if os.path.exists(report_path) else "")
        failed = check_fixture(fixtures, name, spec, os.path.join(workdir, name), report)
        if name in results and results[name][0]:
            failed["agent"] = [f"exit code {results[name][0]}"]
        rows.append((suite, name, failed))
        print(f"{'FAIL' if failed else 'ok  '}  {suite}/{name}")
        for filename, failures in failed.items():
            for failure in failures:
                print(f"      {filename}: {failure}")
    if results:
        datas = [r[2] for r in results.values()]
        write_results(args.skill, rows, main_model(datas), sum(d.get("total_cost_usd") or 0 for d in datas))
    print(f"\nEdited copies and reports: {workdir}")
    sys.exit(1 if any(f for _s, _n, f in rows) else 0)


if __name__ == "__main__":
    main()
