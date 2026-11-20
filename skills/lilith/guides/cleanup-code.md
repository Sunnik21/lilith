# Code cleanup

AI tools leave the same mess in every project. None of this is dangerous, but it makes the app look unfinished and harder to change. All items are ⚪ Cleanup unless noted.

**The one rule: cleanup never changes what the app does.** If removing something could change behavior, don't remove it. List it as a task for the owner.

## C1. Leftover logs and debug lines

**Spot it.** `console.log`, `console.debug`, `debugger`, `print(` in server code, `alert(` used for testing. The scanner counts them.

**Fix.** Delete them. Keep `console.error` / `console.warn` in real error handlers. 🟡 if a log prints secrets, tokens, passwords or full user objects (S1-level leak into logs).

## C2. Fake data shipped as real

**Spot it.** `mockData`, `fakeUsers`, `dummy`, `sampleProducts`, "John Doe", "Jane Smith", "Acme Inc", `test@example.com`, "Lorem ipsum", placeholder images (`placehold.co`, `via.placeholder.com`, `picsum.photos`), invented stats ("10,000+ happy customers", "99.9% uptime", fake testimonials and logos).

**Fix.** Remove fake data the UI no longer needs, or replace with an empty state. Do not delete invented numbers, testimonials or logos yourself: list them as tasks ("replace with real numbers or remove"). Showing invented customer counts or reviews can be misleading advertising.

## C3. Buttons and pages that do nothing

**Spot it.** `onClick={() => {}}`, `href="#"`, `// TODO: implement`, `FIXME`, "Coming soon" pages linked from the main nav, forms whose submit handler only `console.log`s, settings toggles not saved anywhere.

**Fix.** List each one for the owner: wire it up, hide it, or delete it. Don't guess what it should do.

## C4. Dead code

**Spot it.** Components, files and functions nothing imports; unused imports and variables; large commented-out blocks; old versions next to new ones (`Header.tsx` and `HeaderNew.tsx`, `utils-old.ts`). Unused packages in `package.json` (check with `npx depcheck` or `npx knip` if the user agrees).

**Fix.** Delete what is clearly unused (search the whole project for the name first). If unsure, list it.

## C5. The same thing written three times

**Spot it.** Several near-identical components (three button styles, two modals), the same helper (`formatDate`, `cn`, `fetcher`) copied into multiple files, three different ways to call the API or the database.

**Fix.** Pick the one that is used most, point the others to it, delete the copies. Do this only with permission when it touches more than a few files.

## C6. Giant files

**Spot it.** Files over ~400 lines, especially a single `page.tsx` or `App.tsx` holding the whole app. The scanner lists them.

**Fix.** Don't refactor without asking. Suggest a split ("move the pricing table and FAQ into their own components") and do it only if the user says yes.

## C7. Inconsistent naming and structure

**Spot it.** Mixed `camelCase` / `snake_case` / `kebab-case` file names, components in random folders, `.js` and `.ts` mixed for no reason.

**Fix.** Mention it once in the report as a "later" item. Don't mass-rename before launch.

## C8. Missing basics for launch 💡

- `README` that still says "Welcome to your Lovable project" or the framework's default text.
- Default `<title>`, favicon and meta description from the template.
- No `404` page; no error boundary, so a crash shows a white screen.
- `.env.example` missing, so the owner can't redeploy on a new machine.

List these in the report checklist.
