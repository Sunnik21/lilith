#!/usr/bin/env python3
"""Scores the regex scanner (skills/lilith/scripts/lilith_scan.py) on the benchmark.

Builds every fixture app, scans it, and matches scanner leads to the planted
bugs in bench/<app>/expected.json:

- A lead counts if it is a security check (S1..S14) with severity critical,
  high or medium. Info and cleanup leads are hints, not findings.
- A lead matches a bug when the file is the same (or one of its "also_files")
  and the check is the bug's check (or one of its "also" checks). If the file has several bugs with that
  check, the lead's line must also fall inside the bug's line range.
- Recall    = planted bugs matched by at least one lead / planted bugs.
- Precision = leads that match a planted bug / all counted leads.
- Decoys    = things that look bad but are fine; a counted lead on one is a
  false alarm. For cleanup decoys (C1...) any lead counts.
- Fixed apps must produce zero critical/high security leads.

Deterministic, standard library only.

Usage:
  python3 bench/run_scanner.py [--json] [--min-recall 0.5] [--min-precision 0.8] [--max-decoys 0]
Exit code 1 if a threshold is missed or a fixed app has critical/high leads.
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
from build import APPS, build_app, load_manifest  # noqa: E402

SCANNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "lilith", "scripts", "lilith_scan.py")
COUNTED = ("critical", "high", "medium")
LINE_SLACK = 2


def scan(root: str) -> List[dict]:
    out = subprocess.run([sys.executable, SCANNER, root, "--json"], capture_output=True, text=True, check=True)
    leads = json.loads(out.stdout)["findings"]
    for lead in leads:
        lead["file"] = lead["file"].replace(os.sep, "/")
    return leads


def is_counted(lead: dict) -> bool:
    return lead["check"].startswith("S") and lead["severity"] in COUNTED


def _checks(item: dict) -> List[str]:
    return [item["check"]] + item.get("also", [])


def _in_range(lead: dict, item: dict) -> bool:
    start, end = item["lines"]
    return start - LINE_SLACK <= lead["line"] <= end + LINE_SLACK


def matching_item(lead: dict, items: List[dict]) -> Optional[dict]:
    """The bug/decoy this lead points at, using line numbers only to break ties."""
    candidates = [i for i in items
                  if lead["file"] in [i["file"]] + i.get("also_files", []) and lead["check"] in _checks(i)]
    if len(candidates) > 1:
        candidates = [i for i in candidates if _in_range(lead, i)]
    return candidates[0] if candidates else None


def score_app(app: str, leads: List[dict]) -> dict:
    manifest = load_manifest(app)
    bugs, decoys = manifest["bugs"], manifest["decoys"]
    counted = [lead for lead in leads if is_counted(lead)]
    found, true_leads, false_leads = set(), 0, []
    for lead in counted:
        bug = matching_item(lead, bugs + decoys)
        if bug and bug in bugs:
            found.add(bug["id"])
            true_leads += 1
        else:
            false_leads.append(lead)
    flagged = []
    for decoy in decoys:
        pool = leads if decoy["check"].startswith("C") else counted
        if any(matching_item(lead, [decoy] + [b for b in bugs if b["file"] == decoy["file"]]) is decoy for lead in pool):
            flagged.append(decoy["id"])
    return {
        "app": app,
        "bugs": [{**b, "found": b["id"] in found} for b in bugs],
        "counted_leads": len(counted),
        "true_leads": true_leads,
        "false_leads": false_leads,
        "decoys": len(decoys),
        "decoys_flagged": flagged,
    }


def score_fixed(leads: List[dict]) -> Tuple[List[dict], List[dict]]:
    serious = [lead for lead in leads if lead["check"].startswith("S") and lead["severity"] in ("critical", "high")]
    medium = [lead for lead in leads if lead["check"].startswith("S") and lead["severity"] == "medium"]
    return serious, medium


def ratio(a: int, b: int) -> float:
    return a / b if b else 0.0


def summarize(results: List[dict], fixed: Dict[str, Tuple[List[dict], List[dict]]]) -> dict:
    all_bugs = [b for r in results for b in r["bugs"]]
    regex_bugs = [b for b in all_bugs if b.get("regex")]
    per_check: Dict[str, Dict[str, int]] = {}
    for b in all_bugs:
        row = per_check.setdefault(b["check"], {"planted": 0, "found": 0})
        row["planted"] += 1
        row["found"] += b["found"]
    counted = sum(r["counted_leads"] for r in results)
    true_leads = sum(r["true_leads"] for r in results)
    return {
        "bugs": len(all_bugs),
        "found": sum(b["found"] for b in all_bugs),
        "recall": ratio(sum(b["found"] for b in all_bugs), len(all_bugs)),
        "regex_findable": len(regex_bugs),
        "regex_found": sum(b["found"] for b in regex_bugs),
        "recall_regex_findable": ratio(sum(b["found"] for b in regex_bugs), len(regex_bugs)),
        "counted_leads": counted,
        "true_leads": true_leads,
        "precision": ratio(true_leads, counted),
        "decoys": sum(r["decoys"] for r in results),
        "decoys_flagged": sum(len(r["decoys_flagged"]) for r in results),
        "fixed_critical_high": sum(len(v[0]) for v in fixed.values()),
        "fixed_medium": sum(len(v[1]) for v in fixed.values()),
        "per_check": dict(sorted(per_check.items(), key=lambda kv: int(kv[0][1:]))),
    }


def print_report(results: List[dict], fixed: Dict[str, Tuple[List[dict], List[dict]]], total: dict) -> None:
    print("Lilith scanner benchmark\n")
    print(f"{'app':<16}{'found':>8}{'leads':>8}{'precision':>11}{'decoys hit':>12}{'fixed crit/high':>17}")
    for r in results:
        found = sum(b["found"] for b in r["bugs"])
        print(f"{r['app']:<16}{found:>4}/{len(r['bugs']):<3}{r['counted_leads']:>8}"
              f"{ratio(r['true_leads'], r['counted_leads']):>11.0%}"
              f"{len(r['decoys_flagged']):>8}/{r['decoys']:<3}{len(fixed[r['app']][0]):>17}")
    print("\nPer check (planted bugs found by the scanner):")
    for check, row in total["per_check"].items():
        print(f"  {check:<4} {row['found']}/{row['planted']}")
    print("\nMissed bugs:")
    for r in results:
        for b in r["bugs"]:
            if not b["found"]:
                print(f"  {b['id']:<4}{b['check']:<5}{b['file']}: {b['description']}")
    false_leads = [(r["app"], lead) for r in results for lead in r["false_leads"]]
    if false_leads:
        print("\nFalse alarms (counted leads that match no planted bug):")
        for app, lead in false_leads:
            print(f"  {app}: {lead['check']} {lead['severity']} {lead['file']}:{lead['line']} {lead['note']}")
    for app, (serious, _medium) in fixed.items():
        for lead in serious:
            print(f"\nFIXED APP LEAD {app}: {lead['check']} {lead['severity']} {lead['file']}:{lead['line']} {lead['note']}")
    print(f"\nTotal: recall {total['found']}/{total['bugs']} = {total['recall']:.0%} "
          f"(regex-findable bugs: {total['regex_found']}/{total['regex_findable']} = {total['recall_regex_findable']:.0%}), "
          f"precision {total['true_leads']}/{total['counted_leads']} = {total['precision']:.0%}, "
          f"decoys flagged {total['decoys_flagged']}/{total['decoys']}, "
          f"fixed apps critical/high leads {total['fixed_critical_high']} (medium {total['fixed_medium']})")


def run(out_root: str) -> Tuple[List[dict], Dict[str, Tuple[List[dict], List[dict]]], dict]:
    results, fixed = [], {}
    for app in APPS:
        results.append(score_app(app, scan(build_app(app, "vulnerable", out_root))))
        fixed[app] = score_fixed(scan(build_app(app, "fixed", out_root)))
    return results, fixed, summarize(results, fixed)


def main() -> None:
    ap = argparse.ArgumentParser(description="Score lilith_scan.py against the benchmark fixtures")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-recall", type=float, default=0.0)
    ap.add_argument("--min-precision", type=float, default=0.0)
    ap.add_argument("--max-decoys", type=int, default=None)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="lilith-bench-") as tmp:
        results, fixed, total = run(tmp)
    if args.json:
        print(json.dumps({"total": total, "apps": results}, indent=2))
    else:
        print_report(results, fixed, total)
    problems = []
    if total["recall"] < args.min_recall:
        problems.append(f"recall {total['recall']:.2f} < {args.min_recall}")
    if total["precision"] < args.min_precision:
        problems.append(f"precision {total['precision']:.2f} < {args.min_precision}")
    if args.max_decoys is not None and total["decoys_flagged"] > args.max_decoys:
        problems.append(f"decoys flagged {total['decoys_flagged']} > {args.max_decoys}")
    if total["fixed_critical_high"]:
        problems.append(f"fixed apps have {total['fixed_critical_high']} critical/high leads")
    if problems:
        print("\nFAIL: " + "; ".join(problems), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
