#!/usr/bin/env python3
"""Approximate token cost of a Lilith run (chars / 4).

Prints:
- the size of every file in skills/lilith/,
- the instructions loaded per mode (MODES below says which files each mode
  reads; files tagged with a stack only load when the scanner detects it),
- the size of lilith_scan.py and count_tells.py output on a sample project
  (the nextjs-saas benchmark app: Next.js + Supabase + Stripe + OpenAI).

With --claude it also runs the skill with `claude -p` on the sample app and
records the real usage the CLI reports (tokens and cost). That costs money
and varies between runs; it is never run in CI.

Usage:
  python3 bench/tokens.py [--json] [--claude] [--requests "/lilith,/lilith full"]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import build_app  # noqa: E402

BENCH = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(BENCH, "..", "skills", "lilith"))
SAMPLE_APP = "nextjs-saas"
SAMPLE_STACK = {"supabase", "stripe", "ai"}

# Which skill files the agent reads in each mode: (file, None) always loads,
# (file, "stack") only when the scanner detects that stack. Keep in sync with
# the routing in SKILL.md.
Load = Tuple[str, Optional[str]]
MODES: Dict[str, List[Load]] = {
    "security": [
        ("SKILL.md", None), ("guides/security-core.md", None), ("templates/report.md", None),
        ("guides/stacks/supabase.md", "supabase"),  # supabase_check.sql is copied with cp, not read
        ("guides/stacks/firebase.md", "firebase"), ("checks/firebase_check.md", "firebase"),
        ("guides/stacks/stripe.md", "stripe"), ("guides/stacks/ai.md", "ai"),
    ],
    "cleanup": [
        ("SKILL.md", None), ("guides/cleanup-code.md", None), ("guides/cleanup-ui.md", None),
        ("templates/report.md", None),
    ],
    "server": [("SKILL.md", None), ("guides/server.md", None)],
    "fix one check (S7)": [("guides/fixing.md", None), ("guides/fixes/S7.md", None)],
}
MODES["full"] = list(dict.fromkeys(MODES["security"] + MODES["cleanup"]))
DEFAULT_MODE = "security"  # what a plain "/lilith" runs

CLAUDE_PROMPT = """Use the Lilith skill. Its files are in {skill}. Read {skill}/SKILL.md and follow it for the request "{request}" on the project in the current folder.
Non-interactive measurement run: do not ask questions, do not change files, skip the live database step (mark it NOT checked), stop after the report."""


def tokens(text: str) -> int:
    return round(len(text) / 4)


def file_tokens() -> Dict[str, int]:
    sizes = {}
    for dirpath, _dirs, files in os.walk(SKILL):
        for name in files:
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="replace") as fh:
                sizes[os.path.relpath(path, SKILL)] = tokens(fh.read())
    return dict(sorted(sizes.items()))


def mode_tokens(sizes: Dict[str, int], stack: set) -> Dict[str, dict]:
    out = {}
    for mode, files in MODES.items():
        wanted = [f for f, cond in files if cond is None or cond in stack]
        out[mode] = {"tokens": sum(sizes.get(f, 0) for f in wanted), "files": wanted,
                     "missing": [f for f in wanted if f not in sizes]}
    return out


def tool_output_tokens(app_dir: str) -> Dict[str, int]:
    scripts = os.path.join(SKILL, "scripts")
    runs = {
        "lilith_scan.py": [sys.executable, os.path.join(scripts, "lilith_scan.py"), app_dir],
        "count_tells.py": [sys.executable, os.path.join(scripts, "count_tells.py"), app_dir],
    }
    return {name: tokens(subprocess.run(cmd, capture_output=True, text=True).stdout) for name, cmd in runs.items()}


def claude_usage(app_dir: str, request: str) -> dict:
    cmd = ["claude", "-p", CLAUDE_PROMPT.format(skill=SKILL, request=request), "--output-format", "json",
           "--add-dir", SKILL, "--no-session-persistence",
           "--allowedTools", "Read,Grep,Glob,Bash(python3:*),Bash(git:*),Bash(ls:*),Bash(find:*),Bash(wc:*)"]
    cmd += ["--bare"] if os.environ.get("ANTHROPIC_API_KEY") else ["--setting-sources", "project,local"]
    proc = subprocess.run(cmd, cwd=app_dir, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1000:] or proc.stdout[-1000:])
    data = json.loads(proc.stdout)
    usage = data.get("usage", {})
    model = max((data.get("modelUsage") or {"unknown": {}}).items(), key=lambda kv: kv[1].get("costUSD", 0))[0]
    return {
        "request": request,
        "model": model,
        "input_tokens": usage.get("input_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "turns": data.get("num_turns"),
        "cost_usd": data.get("total_cost_usd"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Approximate token cost of a Lilith run")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--claude", action="store_true", help="also run claude -p on the sample app and record real usage")
    ap.add_argument("--requests", default="/lilith", help="comma-separated requests for --claude (default: /lilith)")
    args = ap.parse_args()

    sizes = file_tokens()
    report = {"files": sizes, "total_skill_tokens": sum(sizes.values()), "default_mode": DEFAULT_MODE,
              "modes": mode_tokens(sizes, SAMPLE_STACK), "sample_app": SAMPLE_APP}
    with tempfile.TemporaryDirectory(prefix="lilith-tokens-") as tmp:
        app_dir = build_app(SAMPLE_APP, "vulnerable", tmp)
        report["tool_output"] = tool_output_tokens(app_dir)
        if args.claude:
            report["claude"] = [claude_usage(app_dir, r.strip()) for r in args.requests.split(",") if r.strip()]

    if args.json:
        print(json.dumps(report, indent=2))
        return
    print("Skill files (approx tokens = chars/4):")
    for path, n in sizes.items():
        print(f"  {n:>6}  {path}")
    print(f"  {report['total_skill_tokens']:>6}  TOTAL\n")
    print(f"Instructions loaded per mode (sample stack: {', '.join(sorted(SAMPLE_STACK))}; plain /lilith = {DEFAULT_MODE}):")
    for mode, row in report["modes"].items():
        note = f"  (missing: {', '.join(row['missing'])})" if row["missing"] else ""
        print(f"  {row['tokens']:>6}  {mode}{note}")
    print(f"\nTool output on the {SAMPLE_APP} sample app:")
    for name, n in report["tool_output"].items():
        print(f"  {n:>6}  {name}")
    for u in report.get("claude", []):
        print(f"\nclaude -p '{u['request']}' ({u['model']}): input {u['input_tokens']} + cache write "
              f"{u['cache_creation_input_tokens']} + cache read {u['cache_read_input_tokens']}, "
              f"output {u['output_tokens']}, {u['turns']} turns, ${u['cost_usd']:.2f}")


if __name__ == "__main__":
    main()
