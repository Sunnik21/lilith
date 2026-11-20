# Cleanup eval results

Written by `python3 bench/ui/run.py`. One run per fixture; results vary between runs.

## external: 2026-11-20 00:37, claude-opus-5-5, $1.33

| Suite | Fixture | Result | Failures |
|---|---|---|---|
| ui | claims | pass |  |
| ui | clean | pass |  |
| ui | form | pass |  |
| ui | i18n | pass |  |
| ui | nav-menu | FAIL | Header.tsx: lost 'Begin your journey', lost 'Discover Untamed Wilderness', still has 'Polar expeditions' |
| ui | real-state | pass |  |

Passed 5 of 6.

## lilith: 2026-11-20 00:37, claude-opus-5-5, $2.08

| Suite | Fixture | Result | Failures |
|---|---|---|---|
| ui | claims | pass |  |
| ui | clean | pass |  |
| ui | form | FAIL | signup.html: still has "We'll use this email address" |
| ui | i18n | FAIL | en.json: still has '🚀', still has 'Seamlessly', still has 'all in one place' |
| ui | nav-menu | FAIL | Header.tsx: lost 'Begin your journey', lost 'Discover Untamed Wilderness', lost 'Small-ship voyages' |
| ui | real-state | pass |  |
| code | dynamic-import | pass |  |
| code | error-handler | pass |  |
| code | mock-in-use | pass |  |

Passed 6 of 9.

