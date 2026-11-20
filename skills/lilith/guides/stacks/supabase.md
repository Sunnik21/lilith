# Supabase details (load when the scanner detects Supabase)

## S2
`createClient(url, SERVICE_ROLE)` or a `service_role` key anywhere in browser code: the service role skips every database rule.

## S3: Row Level Security (RLS)
- In `supabase/migrations/*.sql`, every `create table` in `public` needs `alter table ... enable row level security;`.
- Policies with `using (true)` or `with check (true)` for update/delete/all let anyone do it. Insert-only `with check (true)` is fine for a contact form (add a rate limit).
- `for select to authenticated using (true)`: every logged-in user reads every row (S5).
- An update policy without column limits lets users change their own `role`, `is_admin` or `plan` (S6).
- `insert into storage.buckets (..., public) values (..., true)` for private files (S10).
- Migrations are not the live database. Always run the live check below.

## Live check (2 minutes, do this whenever the stack has Supabase)
1. Tell the user: "This query only reads your database settings (which tables are protected and how), never the data inside them, and changes nothing."
2. Where: Supabase dashboard → project → **SQL Editor** → **New query**.
3. Copy the query into their project without reading it (saves ~3,000 tokens): `cp <this-skill-folder>/checks/supabase_check.sql ./lilith-supabase-check.sql`. Tell them to open that file, copy everything into the SQL Editor, click **Run**, paste the result table back, then delete the file (it holds no secrets, but it doesn't belong in the app). Only if they can't open files (web chat, phone), read the file and give it to them in one code block.
4. Turn each row into what / why / fix. `severity` critical → 🔴, high → 🟠, medium → 🟡, info → 💡 (✅ for `all_checks_passed`). Explain `fix_sql` before offering it; they run it, never you.
5. `rls_disabled`, `policies_ignored`, `open_write_policy` confirm S3 leads from the code: merge, don't repeat.
6. Point them to **Advisors → Security Advisor** for the fuller official check.
If they skip: the report says **Live database: NOT checked**, and running the check goes on their list.

## S4 / S5
- On the server use `supabase.auth.getUser()` (verifies the token), not `getSession()` alone (reads a cookie the user can change).
- Prefer the user's own client (RLS applies) over the service-role client; with the service role, filter by owner yourself.

## S10
Private buckets + signed URLs; storage policies limiting each user to their folder: `(storage.foldername(name))[1] = auth.uid()::text`.

## Owner checklist
Security Advisor shows no errors; Auth → email confirmation on, minimum password length 8+.
