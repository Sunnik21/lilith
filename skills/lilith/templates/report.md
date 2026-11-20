# Report template

Fill this in. Skip any section that's empty. Write in the user's language.

- 🔴 and 🟠: in full, what / why / fix, up to 3 short lines each.
- 🟡: one line each.
- ⚪ Cleanup: grouped counts only ("34 leftover logs in 12 files"). Details only if the user asks.
- 💡: one line each, or skip.

| Level | Meaning |
|---|---|
| 🔴 Critical | A stranger, without logging in, can today: read or change your database, spend your money (API keys, payments), take over accounts, or run code on your server. Fix before launch. |
| 🟠 High | A logged-in user can see or change other users' data, become admin, or skip paying. Fix before launch. |
| 🟡 Medium | A real problem with limited damage or unusual conditions (no rate limit on login, verbose errors). Fix soon. |
| ⚪ Cleanup | Not dangerous. Makes the app look AI-made or harder to change later. |
| 💡 Nice to have | Good practice, no real attack path found. |

```markdown
# 🛡️ Security check: <project name>

**Stack:** <e.g. Next.js + Supabase + Stripe, hosted on Vercel>
**Live database:** <"checked (Supabase query results pasted)" / "checked (Firebase rules pasted)" / "NOT checked: only the code was read, the database rules running now may differ" / "no database"> (never leave this line out)
**Verdict:** <one line, e.g. "2 things to fix before launch, then you're good to go">

| 🔴 Critical | 🟠 High | 🟡 Medium | ⚪ Cleanup |
|---|---|---|---|
| 1 | 1 | 2 | 9 |

## 🔴 Fix before launch

### 1. Your OpenAI key is visible to every visitor (S2)
**What:** `NEXT_PUBLIC_OPENAI_KEY` in `src/lib/ai.ts:4` is sent to the browser.
**Why it matters:** anyone can copy it and spend your OpenAI budget.
**Fix:** move the call to a server route (I can do this), then create a new key in the OpenAI dashboard and delete the old one (only you can do this).

## 🟠 High
...

## 🟡 Medium
- No rate limit on login (S8): `app/api/auth/login/route.ts`, add a per-IP limit.

## ⚪ Cleanup (counts only, ask me for details)
- 34 leftover logs in 12 files (C1) · 3 fake testimonials (C2) · 6 eyebrow labels, 4 emoji headings (U1, U11)

## Kept on purpose (cleanup runs only)
- `{isLive && <Badge>Live</Badge>}`: shows real state (U9)

## ✅ Checked, no problems found
S4 login checks on API routes, S5 other users' data, S9 unsafe HTML ...

## ⏭️ Didn't apply
S7 payments (no payments in this app), server guide (hosted on Vercel)

## 📋 Only you can do this
- [ ] Rotate the OpenAI key: platform.openai.com → API keys
- [ ] Set a monthly spending limit with your AI provider
- [ ] Supabase → Advisors → Security Advisor: fix every red item
- [ ] If "Live database: NOT checked": run `checks/supabase_check.sql` in the SQL Editor (or paste your Firebase rules) and send me the result

---
Fix the critical ones, or continue to cleanup?

<sub>Checked with Lilith, a security check for vibecoded apps · github.com/Sunnik21/lilith · found N issues in M checks. This is a check, not a guarantee.</sub>
```
