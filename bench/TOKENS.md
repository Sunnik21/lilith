# What a Lilith run costs in tokens

Measured with `python3 bench/tokens.py` (file sizes as characters / 4, a rough token estimate) and
`python3 bench/tokens.py --claude` (real usage reported by `claude -p --output-format json`).
Sample project: the `nextjs-saas` benchmark app (Next.js + Supabase + Stripe + OpenAI).

## Baseline (2026-11-20, before the token work)

Instructions the agent loads per mode, from the files SKILL.md sends it to:

| Mode | Files | Approx tokens |
|---|---|---|
| Plain `/lilith` (= full check) | SKILL.md, security.md, cleanup-code.md, cleanup-ui.md, report.md, supabase_check.sql | 11,432 |
| Security only | SKILL.md, security.md, report.md, supabase_check.sql | 9,125 |
| Cleanup only | SKILL.md, cleanup-code.md, cleanup-ui.md, report.md | 4,569 |
| Server | SKILL.md, server.md | 2,760 |

Biggest files: lilith_scan.py 7,982 and count_tells.py 3,624 (run, not read, so they cost only their output), security.md 3,896, supabase_check.sql 2,967, SKILL.md 1,772.

Tool output on the sample app: `lilith_scan.py` 440 tokens, `count_tells.py` 196 tokens.

One real run of plain `/lilith` on the sample app (claude-opus-5-5, Claude Code 2.1.318, user settings not loaded):

| Input (uncached) | Cache write | Cache read | Output | Turns | Cost |
|---|---|---|---|---|---|
| 14 | 28,465 | 296,914 | 4,480 | 9 | $0.38 |

Most input tokens are cache reads: every turn re-sends Claude Code's own system prompt and the conversation so far. That is why fewer turns and fewer files read matter more than the size of any single guide.

## Changes, step by step (same sample app, chars / 4)

| Step | What changed | Instructions, plain `/lilith` | Scanner output | Note |
|---|---|---|---|---|
| Baseline | | 11,432 | 440 | |
| Read plan | scanner prints size, compact leads and a read plan; SKILL.md gets reading rules | 11,612 | 469 | +29 output tokens for the plan; the saving is in files the agent no longer opens |
| Split guides | lean SKILL.md router (919 tokens); security.md → security-core + stacks/* + fixes/*; cleanup-ui split (charts, surface, examples load on demand); SQL check handed over with `cp` instead of read; compact count_tells | 6,288 | 469 | security only: 9,125 → 4,216; cleanup: 4,569 → 3,634; server: 2,760 → 1,906; count_tells output on the sample 196 → 2 |
| Modes | plain `/lilith` = security only, then one question; `/lilith full` for everything; report shows cleanup as counts; grouped fixes, codemods with a diff first | 4,388 | 469 | full check (now `/lilith full`): 6,460; SKILL.md 998 tokens |
