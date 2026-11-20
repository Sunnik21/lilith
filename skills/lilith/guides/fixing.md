# Fixing (load only after the user said yes)

1. Suggest a save point first: `git add -A && git commit -m "before lilith fixes"`.
2. Load only `fixes/S<n>.md` for the checks being fixed. Nothing else.
3. **Security fixes: one at a time**, most dangerous first. After each, one line on what changed.
4. **Group fixes of the same kind into one step** (e.g. "add the login check to these 4 routes"), and say the group before starting.
5. **Mechanical cleanup** (leftover logs, unused imports, trailing debug code): prefer one command or codemod over file-by-file edits, e.g. `npx eslint --fix --rule 'no-console: [error, {allow: [warn, error]}]' src` or `npx knip --fix --fix-type exports,dependencies`. **Never apply a bulk change without first showing the diff summary** (files and line counts, `git diff --stat`) and getting a yes. Keep `console.error`/`console.warn` in real error handlers.
6. Run the scanner again and show before/after counts.
7. Things only the owner can do go in a short checklist with exact clicks. Most common: **a leaked key must be rotated (replaced) in the provider's dashboard**; deleting it from the code is not enough, it stays in git history and old deploys.
