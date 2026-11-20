-- Lilith: live database check for Supabase
-- ---------------------------------------------------------------------------
-- WHAT THIS DOES, IN PLAIN WORDS
--   This query only READS your database SETTINGS (which tables exist, which
--   rules protect them, who is allowed to do what). It never reads the rows
--   inside your tables, and it never changes anything.
--
-- HOW TO USE
--   Supabase dashboard -> SQL Editor -> New query -> paste all of this -> Run.
--   Copy the result table back into the chat with your AI.
--
-- WHAT YOU GET
--   One table with columns: severity, check_id, object, problem, fix_sql.
--   fix_sql is a ready statement where one is safe to suggest; otherwise it is
--   a short instruction. Do not run fix_sql blindly: read it first, or let your
--   AI explain it.
--
-- This is a first check, written for Lilith. For the fuller official check,
-- also open Supabase dashboard -> Advisors -> Security Advisor.
-- Works on Supabase and on plain PostgreSQL 12+ (storage checks are skipped
-- when there is no storage schema, role checks are skipped without anon).
-- ---------------------------------------------------------------------------
with
-- Roles a visitor can act as: anon (not logged in) and authenticated.
api_roles as (
  select oid, rolname from pg_roles where rolname in ('anon', 'authenticated')
),
-- Tables in the public schema (normal and partitioned), not owned by extensions.
pub_tables as (
  select c.oid, c.relname, c.relrowsecurity as rls_on,
         format('public.%I', c.relname) as qname,
         (select count(*) from pg_policy p where p.polrelid = c.oid) as n_policies
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relkind in ('r', 'p')
    and not exists (select 1 from pg_depend d
                    where d.classid = 'pg_class'::regclass and d.objid = c.oid and d.deptype = 'e')
),
-- Which API role can touch which public table (includes grants to PUBLIC).
table_access as (
  select t.oid, r.rolname,
         has_table_privilege(r.oid, t.oid, 'select') as can_select,
         has_table_privilege(r.oid, t.oid, 'insert, update, delete') as can_write
  from pub_tables t cross join api_roles r
),
-- Policies in public and storage, with readable expressions.
pols as (
  select schemaname, tablename, policyname, permissive, roles, cmd,
         coalesce(qual, '') as qual, coalesce(with_check, '') as with_check
  from pg_policies
  where schemaname in ('public', 'storage')
),
findings as (

  -- a. RLS off on a table the API roles can reach: anyone with the public anon
  --    key can read or change every row.
  select 'critical' as severity, 'rls_disabled' as check_id, t.qname as object,
         'Row Level Security is OFF and ' ||
         string_agg(distinct a.rolname, ' and ') ||
         ' can ' ||
         case when bool_or(a.can_write) then 'read and change' else 'read' end ||
         ' every row.' as problem,
         format('alter table %s enable row level security; -- then add policies so each user only sees their own rows', t.qname) as fix_sql
  from pub_tables t
  join table_access a on a.oid = t.oid and (a.can_select or a.can_write)
  where not t.rls_on and t.n_policies = 0
  group by t.qname

  union all
  -- b. Policies exist but RLS is off: the policies do nothing.
  select 'critical', 'policies_ignored', t.qname,
         'This table has ' || t.n_policies || ' policies, but Row Level Security is OFF, so the policies are ignored and the table is open.',
         format('alter table %s enable row level security;', t.qname)
  from pub_tables t
  where not t.rls_on and t.n_policies > 0

  union all
  -- c. Write policies that let everyone write: condition is literally true, or
  --    an explicit anon write policy that never checks who the user is.
  select 'critical', 'open_write_policy',
         format('%I.%I (policy "%s")', p.schemaname, p.tablename, p.policyname),
         case
           when p.qual = 'true' or p.with_check = 'true'
             then 'Policy for ' || lower(p.cmd) || ' has condition "true": anyone it applies to (' || array_to_string(p.roles, ', ') || ') can do it to any row.'
           else 'Policy lets anon (visitors who are not logged in) ' || lower(p.cmd) || ' without checking who they are.'
         end,
         format('drop policy %I on %I.%I; -- then add one that checks (select auth.uid()) = user_id', p.policyname, p.schemaname, p.tablename)
  from pols p
  where p.permissive = 'PERMISSIVE'
    and p.cmd in ('INSERT', 'UPDATE', 'DELETE', 'ALL')
    and (
      p.qual = 'true' or p.with_check = 'true'
      or ('anon' = any (p.roles) and (p.qual || p.with_check) not like '%auth.uid()%'
                                 and (p.qual || p.with_check) not like '%auth.jwt()%')
    )

  union all
  -- d. Read policies with USING (true): fine only for truly public data.
  select 'info', 'public_read_policy',
         format('%I.%I (policy "%s")', p.schemaname, p.tablename, p.policyname),
         'Everyone it applies to (' || array_to_string(p.roles, ', ') || ') can read every row. Fine for public data like blog posts or products, not for anything private.',
         'If this data is private: replace the policy with one that checks (select auth.uid()) = user_id.'
  from pols p
  where p.schemaname = 'public' and p.permissive = 'PERMISSIVE'
    and p.cmd = 'SELECT' and p.qual = 'true'

  union all
  -- e. RLS on but no policies: locked for everyone using the API.
  select 'info', 'rls_no_policies', t.qname,
         'Row Level Security is on but there are no policies, so nobody can use this table through the API. Safe, but the app may be broken if it needs this table.',
         'If the app needs this table, add policies for the logged-in owner. If only the server uses it, leave it.'
  from pub_tables t
  where t.rls_on and t.n_policies = 0

  union all
  -- f. Views that run with the creator's rights skip RLS on the tables they read.
  select 'high', 'view_bypasses_rls', format('public.%I', v.relname),
         'This view reads ' || string_agg(distinct format('public.%I', src.relname), ', ') ||
         ' with the owner''s rights, so Row Level Security there is skipped for anyone who can read the view.',
         format('alter view public.%I set (security_invoker = true);', v.relname)
  from pg_class v
  join pg_namespace n on n.oid = v.relnamespace and n.nspname = 'public'
  join pg_rewrite rw on rw.ev_class = v.oid
  join pg_depend d on d.classid = 'pg_rewrite'::regclass and d.objid = rw.oid
                  and d.refclassid = 'pg_class'::regclass and d.refobjid <> v.oid
  join pg_class src on src.oid = d.refobjid and src.relrowsecurity
  where v.relkind in ('v', 'm')
    and coalesce(array_to_string(v.reloptions, ','), '') !~* 'security_invoker=(true|on|1|yes)'
    and exists (select 1 from api_roles r where has_table_privilege(r.oid, v.oid, 'select'))
  group by v.relname

  union all
  -- g. SECURITY DEFINER functions anyone can call: they run with the owner's
  --    rights and skip RLS.
  select 'medium', 'definer_function_anon',
         format('public.%I(%s)', p.proname, pg_get_function_identity_arguments(p.oid)),
         'This function runs with its owner''s rights (SECURITY DEFINER) and visitors who are not logged in can call it.',
         format('revoke execute on function public.%I(%s) from public, anon; -- then grant execute to authenticated if logged-in users need it',
                p.proname, pg_get_function_identity_arguments(p.oid))
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
  join api_roles r on r.rolname = 'anon'
  where p.prosecdef
    and has_function_privilege(r.oid, p.oid, 'execute')
    and not exists (select 1 from pg_depend d
                    where d.classid = 'pg_proc'::regclass and d.objid = p.oid and d.deptype = 'e')

  union all
  -- h1. Public storage buckets: every file can be downloaded by anyone with the link.
  --     Read through query_to_xml so the query still runs without a storage schema.
  select 'medium', 'public_bucket', 'storage bucket "' || b.name || '"',
         'This bucket is public: anyone with a file''s link can download it, no login needed. Fine for logos and product photos, not for invoices, IDs or private user files.',
         format('update storage.buckets set public = false where id = %L; -- then serve files with signed URLs', b.id)
  from xmltable('/table/row' passing
         case when to_regclass('storage.buckets') is not null
              then query_to_xml('select id::text as id, name::text as name from storage.buckets where public', true, false, '')
         end
         columns id text path 'id', name text path 'name') as b

  union all
  -- h2. storage.objects without RLS: every file in every bucket is open.
  select 'high', 'storage_rls_disabled', 'storage.objects',
         'Row Level Security is OFF on storage.objects, so file access rules are ignored for every bucket.',
         'alter table storage.objects enable row level security; -- then add policies per bucket'
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'storage'
  where c.relname = 'objects' and not c.relrowsecurity

  union all
  -- h3. storage.objects with RLS on and no policies: uploads through the API are blocked.
  select 'info', 'storage_no_policies', 'storage.objects',
         'File storage has no policies, so logged-in users cannot upload or read files through the API. Safe, but uploads in the app will fail.',
         'If the app uploads files: add policies that limit each user to their own folder, e.g. (storage.foldername(name))[1] = auth.uid()::text.'
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'storage'
  where c.relname = 'objects' and c.relrowsecurity
    and not exists (select 1 from pg_policy p where p.polrelid = c.oid)

  union all
  -- i. Sensitive-looking columns that visitors who are not logged in can read:
  --    anon can select the column AND rows are visible (RLS off, or a read
  --    policy with "true" that applies to anon).
  select 'high', 'sensitive_column_exposed', format('%s.%I', t.qname, a.attname),
         'A column named "' || a.attname || '" can be read by visitors who are not logged in.',
         'Move this column to a separate table with no anon access, or store a hash instead. Never send it to the browser.'
  from pub_tables t
  join pg_attribute a on a.attrelid = t.oid and a.attnum > 0 and not a.attisdropped
  join api_roles r on r.rolname = 'anon'
  where a.attname ~* '(^|_)(password|passwd|pwd|token|secret|api_?key|ssn|card|card_?number|credit_?card|cvv|cvc|iban)($|_)'
    and has_column_privilege(r.oid, t.oid, a.attnum, 'select')
    and (
      not t.rls_on
      or exists (select 1 from pols p
                 where p.schemaname = 'public' and p.tablename = t.relname
                   and p.permissive = 'PERMISSIVE' and p.cmd in ('SELECT', 'ALL')
                   and p.qual = 'true'
                   and ('anon' = any (p.roles) or 'public' = any (p.roles)))
    )
)
select severity, check_id, object, problem, fix_sql
from (
  select * from findings
  union all
  select 'info', 'all_checks_passed', '(whole database)',
         'No critical, high or medium problems found. Checked: RLS on public tables, policies that do nothing, open write policies, public read policies, tables locked by RLS, views that skip RLS, SECURITY DEFINER functions, storage buckets and storage rules, sensitive columns.',
         'Also open Supabase dashboard -> Advisors -> Security Advisor for the fuller official check.'
  where not exists (select 1 from findings where severity in ('critical', 'high', 'medium'))
) result
order by case severity when 'critical' then 0 when 'high' then 1 when 'medium' then 2 else 3 end,
         check_id, object;
