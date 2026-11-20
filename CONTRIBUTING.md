# Contributing to Lilith

Lilith is for beginners, so every change should keep it simple.

## Add a check (10 minutes)

1. Pick the guide: `skills/lilith/guides/security-core.md` (Spot it / Why), a file in `guides/stacks/` for stack-specific details, `guides/fixes/S<n>.md` for fix code, or `cleanup-code.md` / `cleanup-ui.md`.
2. Add a section in the same shape as the others:
   - **Spot it.** What to look for in the code (file names, function names, patterns).
   - **Why.** One real consequence, in plain words.
   - **Fix.** The smallest change, with a code snippet if it helps.
3. Security checks only: it must pass the test "[who] can [do what] to [whose data or money]". Best practices with no attacker go under "Nice to have".
4. If a regex can find it, add it to `skills/lilith/scripts/lilith_scan.py` and a case to `tests/test_scan.py`. Build fake secrets at runtime (see `fake()` in the test) so the repo never contains real-looking keys.
5. Run `python3 tests/test_scan.py`.

## Style

- Plain words. Explain any technical term once.
- Short. A beginner should read a check in 30 seconds.
- No made-up statistics.
