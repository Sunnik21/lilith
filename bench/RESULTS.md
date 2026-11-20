# Agent benchmark results

- Date: 2026-11-20 01:24 (local time)
- Model: claude-opus-5-5
- Claude Code: 2.1.318 (Claude Code)
- Runner: `python3 bench/run_agent.py` (one run per app; results vary between runs)
- Live database step skipped (no one to paste results), so S3 is judged from migration files only.

| App | Bugs found | False alarms | Decoys flagged | Severity agrees | Cost |
|---|---|---|---|---|---|
| lovable-style | 11/11 (100%) | 1 | 0/5 | 10/11 (91%) | $0.41 |
| nextjs-saas | 10/10 (100%) | 1 | 0/6 | 8/10 (80%) | $0.44 |
| express-api | 10/10 (100%) | 0 | 0/6 | 10/10 (100%) | $0.35 |
| **Total** | **31/31 (100%)** | **2** | **0/17** | **28/31 (90%)** | |

## Missed bugs

- none

## False alarms

- lovable-style: S6 medium `src/pages/Admin.tsx`: Admin page has no admin check
- nextjs-saas: S13 medium `package.json`: next 14.2.5 has known advisories; npm audit not run

## Severity disagreements (found bugs)

- lovable-style L8: expected high, reported critical
- nextjs-saas N9: expected high, reported critical
- nextjs-saas N10: expected medium, reported high
