#!/usr/bin/env python3
"""Runs the full Lilith skill headlessly with `claude -p` and grades its reports.

Optional and NOT run in CI: it needs the Claude Code CLI, a logged-in account,
takes several minutes and costs money. Results vary between runs and models.

For each vulnerable fixture app:
1. Build it into a temp folder (fake keys injected at runtime).
2. Run `claude -p` in that folder, telling it to follow skills/lilith/SKILL.md
   read-only, skip the live database step, and end the report with a JSON list
   of its security findings (the only change from a normal run; it is needed
   for machine grading).
3. Grade the findings against bench/<app>/expected.json:
   - a finding matches a planted bug when the file matches and either the check
     id matches (or one of the bug's "also" checks) or its line falls inside
     the bug's line range;
   - found / missed bugs, false alarms (critical/high/medium findings that match
     no planted bug), decoys wrongly flagged, and severity agreement (exact).

User-level settings, hooks and plugins are not loaded (--setting-sources
project,local) so personal setups don't change the result. With
ANTHROPIC_API_KEY set, --bare is used instead for a fully clean run.

Reports are saved to bench/.agent-runs/<timestamp>/ (gitignored) and the
summary to bench/RESULTS.md.

Usage:
  python3 bench/run_agent.py [--model MODEL] [--apps lovable-style,nextjs-saas] [--timeout 1800]
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
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import APPS, build_app, load_manifest  # noqa: E402

BENCH = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.normpath(os.path.join(BENCH, "..", "skills", "lilith"))
RUNS_DIR = os.path.join(BENCH, ".agent-runs")
RESULTS_MD = os.path.join(BENCH, "RESULTS.md")
COUNTED = ("critical", "high", "medium")
LINE_SLACK = 3
ALLOWED_TOOLS = "Read,Grep,Glob,Bash(python3:*),Bash(git:*),Bash(ls:*),Bash(cat:*),Bash(find:*),Bash(wc:*),Bash(head:*)"

PROMPT = """Use the Lilith skill. Its files are in {skill_dir}. Read {skill_dir}/SKILL.md and follow it for the request "/lilith" on the project in the current folder.

This is a non-interactive benchmark run:
- Do not ask questions and do not change any files. Stop after the report; do not fix anything.
- Skip the live database step: nobody can paste results, so mark "Live database: NOT checked".
- Write the report in English. Keep the cleanup section short.

After the report, add one fenced ```json block containing an array with every security finding you reported (not cleanup items), each as:
{{"check": "S1".."S14", "file": "path relative to the project root", "line": number or null, "severity": "critical" | "high" | "medium" | "info", "title": "short title"}}
Use "info" for "Nice to have" / "worth checking" items."""


def run_claude(app_dir: str, model: Optional[str], timeout: int) -> dict:
    cmd = ["claude", "-p", PROMPT.format(skill_dir=SKILL_DIR), "--output-format", "json",
           "--add-dir", SKILL_DIR, "--allowedTools", ALLOWED_TOOLS, "--no-session-persistence"]
    cmd += ["--bare"] if os.environ.get("ANTHROPIC_API_KEY") else ["--setting-sources", "project,local"]
    if model:
        cmd += ["--model", model]
    proc = subprocess.run(cmd, cwd=app_dir, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exited {proc.returncode}: {(proc.stderr or proc.stdout)[-2000:]}")
    return json.loads(proc.stdout)


def main_model(result: dict) -> str:
    usage = result.get("modelUsage") or {}
    if not usage:
        return "unknown"
    return max(usage.items(), key=lambda kv: kv[1].get("costUSD", 0))[0]


def extract_findings(report: str) -> List[dict]:
    blocks = re.findall(r"```json\s*(\[.*?\])\s*```", report, re.S)
    if not blocks:
        return []
    try:
        data = json.loads(blocks[-1])
    except json.JSONDecodeError:
        return []
    findings = []
    for f in data if isinstance(data, list) else []:
        if not isinstance(f, dict) or not f.get("file"):
            continue
        path = str(f["file"]).replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        findings.append({
            "check": str(f.get("check", "")).upper(),
            "file": path,
            "line": f.get("line") if isinstance(f.get("line"), int) else None,
            "severity": str(f.get("severity", "")).lower(),
            "title": str(f.get("title", ""))[:120],
        })
    return findings


def _matches(finding: dict, item: dict) -> bool:
    if finding["file"] not in [item["file"]] + item.get("also_files", []):
        return False
    if finding["check"] in [item["check"]] + item.get("also", []):
        return True
    start, end = item["lines"]
    return finding["line"] is not None and start - LINE_SLACK <= finding["line"] <= end + LINE_SLACK


def _best(bug: dict, matched: List[dict]) -> dict:
    """The finding that describes this bug: same check first, then closest line."""
    start, _end = bug["lines"]
    checks = [bug["check"]] + bug.get("also", [])
    return min(matched, key=lambda f: (f["check"] not in checks, f["check"] != bug["check"],
                                       abs((f["line"] or start) - start)))


def grade(app: str, findings: List[dict]) -> dict:
    manifest = load_manifest(app)
    bugs, decoys = manifest["bugs"], manifest["decoys"]
    by_bug: Dict[str, List[dict]] = {}
    false_alarms, decoys_flagged = [], set()
    for f in findings:
        hits = [b for b in bugs if _matches(f, b)]
        for b in hits:
            by_bug.setdefault(b["id"], []).append(f)
        if hits or f["severity"] not in COUNTED:
            continue
        false_alarms.append(f)
        for d in decoys:
            if _matches(f, d):
                decoys_flagged.add(d["id"])
    rows = []
    for b in bugs:
        matched = by_bug.get(b["id"], [])
        counted = [f for f in matched if f["severity"] in COUNTED]
        worst = _best(b, matched)["severity"] if matched else None
        rows.append({"id": b["id"], "check": b["check"], "file": b["file"], "description": b["description"],
                     "expected": b["severity"], "found": bool(counted), "only_as_info": bool(matched) and not counted,
                     "severity": worst, "severity_agrees": worst == b["severity"]})
    return {"app": app, "bugs": rows, "findings": len(findings), "false_alarms": false_alarms,
            "decoys": len(decoys), "decoys_flagged": sorted(decoys_flagged)}


def regrade(run_dir: str) -> List[dict]:
    """Grades saved reports again (no new agent run). Model and cost come from meta.json."""
    meta_path = os.path.join(run_dir, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    results = []
    for app in APPS:
        path = os.path.join(run_dir, f"{app}.md")
        if not os.path.exists(path):
            continue
        findings = extract_findings(open(path, encoding="utf-8").read())
        graded = grade(app, findings)
        graded.update({**meta.get(app, {"model": "unknown", "cost_usd": None}), "json_block_found": bool(findings)})
        results.append(graded)
    return results


def run_app(app: str, model: Optional[str], timeout: int, out_dir: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"lilith-agent-{app}-") as tmp:
        app_dir = build_app(app, "vulnerable", tmp)
        result = run_claude(app_dir, model, timeout)
    report = result.get("result", "")
    with open(os.path.join(out_dir, f"{app}.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    findings = extract_findings(report)
    graded = grade(app, findings)
    meta = {"model": main_model(result), "cost_usd": result.get("total_cost_usd"), "turns": result.get("num_turns")}
    graded.update({**meta, "json_block_found": bool(findings)})
    meta_path = os.path.join(out_dir, "meta.json")
    saved = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    saved[app] = meta
    with open(meta_path, "w") as fh:
        json.dump(saved, fh, indent=2)
    return graded


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({a / b:.0%})" if b else "0/0"


def write_results(results: List[dict], started: dt.datetime, cli_version: str) -> str:
    models = sorted({r["model"] for r in results})
    bugs = [b for r in results for b in r["bugs"]]
    found = [b for b in bugs if b["found"]]
    agree = [b for b in found if b["severity_agrees"]]
    lines = [
        "# Agent benchmark results",
        "",
        f"- Date: {started.strftime('%Y-%m-%d %H:%M')} (local time)",
        f"- Model: {', '.join(models)}",
        f"- Claude Code: {cli_version}",
        "- Runner: `python3 bench/run_agent.py` (one run per app; results vary between runs)",
        "- Live database step skipped (no one to paste results), so S3 is judged from migration files only.",
        "",
        "| App | Bugs found | False alarms | Decoys flagged | Severity agrees | Cost |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        f = [b for b in r["bugs"] if b["found"]]
        cost = f"${r['cost_usd']:.2f}" if isinstance(r.get("cost_usd"), (int, float)) else "n/a"
        lines.append(f"| {r['app']} | {pct(len(f), len(r['bugs']))} | {len(r['false_alarms'])} | "
                     f"{len(r['decoys_flagged'])}/{r['decoys']} | {pct(sum(b['severity_agrees'] for b in f), len(f))} | {cost} |")
    lines.append(f"| **Total** | **{pct(len(found), len(bugs))}** | **{sum(len(r['false_alarms']) for r in results)}** | "
                 f"**{sum(len(r['decoys_flagged']) for r in results)}/{sum(r['decoys'] for r in results)}** | "
                 f"**{pct(len(agree), len(found))}** | |")
    lines += ["", "## Missed bugs", ""]
    missed = [(r["app"], b) for r in results for b in r["bugs"] if not b["found"]]
    lines += [f"- {app} {b['id']} ({b['check']}, {b['expected']}): {b['description']}"
              + (" (mentioned only as info)" if b["only_as_info"] else "") for app, b in missed] or ["- none"]
    lines += ["", "## False alarms", ""]
    lines += [f"- {r['app']}: {f['check']} {f['severity']} `{f['file']}`: {f['title']}"
              for r in results for f in r["false_alarms"]] or ["- none"]
    lines += ["", "## Severity disagreements (found bugs)", ""]
    lines += [f"- {r['app']} {b['id']}: expected {b['expected']}, reported {b['severity']}"
              for r in results for b in r["bugs"] if b["found"] and not b["severity_agrees"]] or ["- none"]
    if any(not r["json_block_found"] for r in results):
        lines += ["", "Note: some reports had no parsable JSON block and were graded as finding nothing: "
                  + ", ".join(r["app"] for r in results if not r["json_block_found"])]
    text = "\n".join(lines) + "\n"
    with open(RESULTS_MD, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Lilith skill with claude -p and grade it")
    ap.add_argument("--model", default=None, help="model alias or id passed to claude --model")
    ap.add_argument("--apps", default=",".join(APPS))
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per app")
    ap.add_argument("--regrade", metavar="RUN_DIR", help="grade saved reports in bench/.agent-runs/<run> again, no new run")
    args = ap.parse_args()
    if args.regrade:
        stamp = dt.datetime.strptime(os.path.basename(os.path.normpath(args.regrade)), "%Y%m%d-%H%M%S")
        cli = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip() if shutil.which("claude") else "unknown"
        print(write_results(regrade(args.regrade), stamp, cli))
        return
    if not shutil.which("claude"):
        print("SKIP: the claude CLI is not installed; the agent benchmark did not run.")
        return
    apps = [a for a in args.apps.split(",") if a]
    started = dt.datetime.now()
    out_dir = os.path.join(RUNS_DIR, started.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    cli_version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(apps)) as pool:
        futures = {a: pool.submit(run_app, a, args.model, args.timeout, out_dir) for a in apps}
        results = []
        for app in apps:
            try:
                results.append(futures[app].result())
            except Exception as exc:  # report and keep going with the other apps
                print(f"{app}: agent run failed: {exc}", file=sys.stderr)
    if not results:
        print("No agent run finished; RESULTS.md not written.", file=sys.stderr)
        sys.exit(1)
    print(write_results(results, started, cli_version))
    print(f"Reports saved in {out_dir}")


if __name__ == "__main__":
    main()
