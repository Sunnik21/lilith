# Security checks (core)

The 14 holes AI-built apps have most often. Here: how to spot each one and why it matters. Stack details live in `stacks/` (loaded only for the detected stack). Fix code lives in `fixes/S<n>.md` (loaded only when the user agrees to fix that check).

A finding counts only if you can finish **"[who] can [do what] to [whose data or money]"** from the code. If it depends on something you can't see (a dashboard setting, a deployed config), report "worth checking" with the exact thing to look at.

## S1. Secret keys in the code or in git 🔴
**Spot it.** Scanner hits for live keys (`sk_live_`, `sk-proj-`, `sk-ant-`, `AKIA`, `ghp_`, private keys, database URLs with a password, Supabase `service_role` JWTs), hard-coded fallbacks (`process.env.JWT_SECRET || "..."`), `.env` files tracked by git (`git ls-files | grep -i '\.env'`, also `git log --all --oneline -- .env`).
**Why.** Anyone who sees the repo can use the key: spend your money, read the whole database, sign their own login tokens.
**Not secrets:** Supabase anon key, Firebase web `apiKey`, Stripe `pk_` key, domain-restricted Maps keys. Their safety comes from S3 and dashboard restrictions.

## S2. Secret keys sent to the browser 🔴
**Spot it.** Env names with a public prefix (`NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`, `EXPO_PUBLIC_`, `PUBLIC_`) holding a secret; secret clients created in browser code (`"use client"` files, React components, any Vite/CRA app with no server).
**Why.** Everything with these prefixes ships in the JavaScript every visitor downloads.

## S3. Database open to everyone 🔴
**Spot it.** Database rules in migrations or rules files that let anyone read or write; tables with no access rules at all. Details per stack: `stacks/supabase.md`, `stacks/firebase.md`. The live database can differ from the repo: run the live check.
**Why.** The public client key is in every browser. With open rules it can read, change or delete every row.

## S4. API routes with no login check 🔴/🟠
**Spot it.** Every server entry point (API routes, server actions, edge functions, Express routes) that reads or changes private data without a session check at the top, or with a check that doesn't verify anything (`jwt.decode` instead of `jwt.verify`). Server actions are public endpoints too. Login and signup routes are public by design (check them for S8 instead).
**Why.** Hiding a button doesn't protect the endpoint. Anyone can call it with curl.

## S5. Users can open other users' data 🟠
**Spot it.** A record loaded by an id from the URL or body with no owner filter (`findUnique({ where: { id } })`, an admin/service client with `.eq('id', params.id)`), or a read rule that lets every logged-in user read every row.
**Why.** User A changes `/invoices/41` to `/42` and sees user B's invoice.

## S6. Trusting what the browser says 🟠
**Spot it.** The server takes `price`, `amount`, `role`, `isAdmin`, `plan`, `credits`, `userId` from the request; `data: req.body` written straight to the database; admin pages protected only in a React component; users allowed to update their own `role`/`plan` column.
**Why.** Anyone can edit the request in DevTools and pay $0.01 or set `role: "admin"`.

## S7. Payments not verified 🔴
**Spot it.** Payment webhooks without a signature check; the body parsed as JSON before verifying; premium unlocked in the browser (a success page with `?success=true` that updates the plan).
**Why.** Anyone can send a fake "payment succeeded" event or open the success URL and get the paid plan.

## S8. No limits on expensive or sensitive actions 🟡 (🟠 for AI)
**Spot it.** No rate limit or per-user cap on AI endpoints, email/SMS sending, login, signup, password reset, OTP, uploads, public forms.
**Why.** A bot runs up your AI bill overnight, guesses passwords, or sends spam from your domain.

## S9. Unsafe HTML and code execution 🟠
**Spot it.** `dangerouslySetInnerHTML`, `v-html`, `{@html}`, `.innerHTML =`, `eval(`, `new Function(`, Markdown with raw HTML, `exec` with user input, SQL built from strings (`$queryRawUnsafe`, template literals). A finding needs user- or AI-controlled text reaching the sink; static HTML and JSON-LD from your own object are fine.
**Why.** Other users' browsers run the attacker's script (session theft), or your server runs their SQL/commands.

## S10. File uploads 🟡
**Spot it.** No size or type limit; the user's file name used on disk; public buckets or public folders holding private files (IDs, invoices).
**Why.** Private documents become downloadable by link; someone uploads a huge file or an HTML page served from your domain.

## S11. AI features 🟡/🟠
**Spot it.** Secrets, internal URLs or logins in system prompts; AI tools that can write data or send things, fed with user or web text; model output passed to `eval`, SQL, shell or raw HTML.
**Why.** Prompt injection makes the AI act for the attacker, and system prompts can always be extracted.

## S12. Leftover debug and test doors 🟡 (🔴 if it grants access)
**Spot it.** `/api/debug`, `/api/seed`, `/admin/setup` without a server check; routes that return `process.env`; hard-coded test accounts (`admin@admin.com`); stack traces or SQL errors sent to the browser. Test credentials inside test files are fine.
**Why.** Attackers scan for these paths automatically.

## S13. Vulnerable packages 🟡
**Spot it.** `npm audit --omit=dev` (or pnpm/yarn/pip-audit): report only critical/high in packages used at runtime. No lockfile. Package names that don't exist on npm (AI sometimes invents them).
**Why.** Bots exploit known holes in old packages.

## S14. Headers, CORS and HTTPS 💡 (🟠 for credentialed CORS)
**Spot it.** Any origin allowed (`*`, `origin: true`, the request origin reflected) **together with** credentials on an API that uses cookies. If auth uses a Bearer header and no cookies, there is no attack path: 💡 at most. Missing security headers are hardening only.
**Why.** Credentialed CORS that trusts any site lets another website act as the logged-in user.

## Only the owner can check (add to the report checklist when relevant)
- Every leaked key rotated in the provider dashboard; AI provider spending limit set.
- Production env vars set in the hosting dashboard, not the repo; backups on.
