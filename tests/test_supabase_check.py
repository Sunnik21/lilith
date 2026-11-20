#!/usr/bin/env python3
"""Runs skills/lilith/checks/supabase_check.sql against a throwaway Postgres.

Starts a temporary cluster with initdb (nothing is installed or left behind),
builds a fake Supabase-like schema with one instance of each problem plus clean
tables, runs the check in a READ ONLY transaction and asserts each check fires
exactly for its planted object. Also runs it on plain Postgres (no anon role,
no storage schema) to prove it does not crash there.

If no Postgres binaries are found, the test is SKIPPED (exit 0) with a message.
Run: python3 tests/test_supabase_check.py
"""
from __future__ import annotations

import csv
import glob
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Set

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_SQL = os.path.join(HERE, "..", "skills", "lilith", "checks", "supabase_check.sql")

SUPABASE_LIKE = r"""
create role anon nologin;
create role authenticated nologin;
create schema auth;
create function auth.uid() returns uuid language sql stable as $$ select null::uuid $$;
grant usage on schema public to anon, authenticated;
alter default privileges in schema public grant all on tables to anon, authenticated;
alter default privileges in schema public grant all on functions to anon, authenticated;

create schema storage;
create table storage.buckets (id text primary key, name text not null, public boolean default false);
create table storage.objects (id uuid primary key, bucket_id text, name text, owner uuid);
alter table storage.objects enable row level security;
insert into storage.buckets values ('avatars', 'avatars', true), ('invoices', 'invoices', false);

-- clean: RLS on, owner-only policies
create table public.notes (id uuid primary key, user_id uuid, body text);
alter table public.notes enable row level security;
create policy "own read" on public.notes for select to authenticated using ((select auth.uid()) = user_id);
create policy "own write" on public.notes for insert to authenticated with check ((select auth.uid()) = user_id);
-- clean: view with security_invoker
create view public.my_notes with (security_invoker = true) as select id, body from public.notes;
-- clean: anon write policy that does check the user (should not fire c)
create table public.feedback (id uuid primary key, user_id uuid, msg text);
alter table public.feedback enable row level security;
create policy "anon own" on public.feedback for insert to anon, authenticated with check ((select auth.uid()) = user_id);
-- clean: security definer function only for authenticated
create function public.safe_fn() returns int language sql security definer as $$ select 1 $$;
revoke execute on function public.safe_fn() from public, anon;

-- a. RLS off, anon can reach it
create table public.profiles (id uuid primary key, full_name text);
-- b. policies exist but RLS off
create table public.orders (id uuid primary key, user_id uuid);
create policy "own orders" on public.orders for select using ((select auth.uid()) = user_id);
-- c. write policy with true
create table public.messages (id uuid primary key, body text);
alter table public.messages enable row level security;
create policy "anyone writes" on public.messages for all using (true) with check (true);
-- d. public read policy (also the planted i: sensitive column readable by anon)
create table public.posts (id uuid primary key, title text, api_key text);
alter table public.posts enable row level security;
create policy "public read" on public.posts for select using (true);
-- e. RLS on, no policies
create table public.audit_log (id uuid primary key, event text);
alter table public.audit_log enable row level security;
-- f. view without security_invoker over an RLS table
create view public.all_notes as select id, body from public.notes;
-- g. security definer function callable by anon
create function public.delete_everything() returns void language sql security definer as $$ select $$;
"""

EXPECTED: Dict[str, Set[str]] = {
    "rls_disabled": {"public.profiles"},
    "policies_ignored": {"public.orders"},
    "open_write_policy": {'public.messages (policy "anyone writes")'},
    "public_read_policy": {'public.posts (policy "public read")'},
    "rls_no_policies": {"public.audit_log"},
    "view_bypasses_rls": {"public.all_notes"},
    "definer_function_anon": {"public.delete_everything()"},
    "public_bucket": {'storage bucket "avatars"'},
    "storage_no_policies": {"storage.objects"},
    "sensitive_column_exposed": {"public.posts.api_key"},
}
CLEAN_OBJECTS = ("notes", "my_notes", "feedback", "safe_fn", "invoices")


def find_pg_bin() -> Optional[str]:
    candidates = [os.path.dirname(p) for p in [shutil.which("initdb")] if p]
    candidates += sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True)
    candidates += sorted(glob.glob("/opt/homebrew/opt/postgresql@*/bin"), reverse=True)
    candidates += sorted(glob.glob("/usr/local/opt/postgresql@*/bin"), reverse=True)
    for d in candidates:
        if all(os.path.exists(os.path.join(d, b)) for b in ("initdb", "pg_ctl", "psql")):
            return d
    return None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TempPostgres:
    def __init__(self, bin_dir: str) -> None:
        self.bin = bin_dir
        self.dir = tempfile.mkdtemp(prefix="lilith-pg-")
        self.data = os.path.join(self.dir, "data")
        self.port = free_port()

    def __enter__(self) -> "TempPostgres":
        self._run("initdb", "-D", self.data, "-U", "postgres", "-A", "trust", "--no-sync",
                  "--locale=C", "-E", "UTF8")
        opts = f"-p {self.port} -c listen_addresses=127.0.0.1 -c unix_socket_directories=''"
        self._run("pg_ctl", "-D", self.data, "-o", opts, "-w", "-l", os.path.join(self.dir, "log"), "start")
        return self

    def __exit__(self, *exc: object) -> None:
        subprocess.run([os.path.join(self.bin, "pg_ctl"), "-D", self.data, "-m", "immediate", "stop"],
                       capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _run(self, exe: str, *args: str) -> None:
        env = {**os.environ, "LC_ALL": "C", "LANG": "C"}
        r = subprocess.run([os.path.join(self.bin, exe), *args], capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"{exe} failed: {r.stderr or r.stdout}")

    def psql(self, db: str, sql: str, read_only: bool = False) -> str:
        env = {**os.environ, "PGOPTIONS": "-c default_transaction_read_only=on" if read_only else ""}
        r = subprocess.run(
            [os.path.join(self.bin, "psql"), "-X", "-q", "-v", "ON_ERROR_STOP=1", "--csv",
             "-h", "127.0.0.1", "-p", str(self.port), "-U", "postgres", "-d", db],
            input=sql, capture_output=True, text=True, env=env,
        )
        if r.returncode != 0:
            raise RuntimeError(r.stderr)
        return r.stdout


def run_check(pg: TempPostgres, db: str) -> List[Dict[str, str]]:
    with open(CHECK_SQL) as fh:
        out = pg.psql(db, fh.read(), read_only=True)
    return list(csv.DictReader(io.StringIO(out)))


def check_supabase_like(pg: TempPostgres) -> List[str]:
    pg.psql("postgres", "create database supa;")
    pg.psql("supa", SUPABASE_LIKE)
    rows = run_check(pg, "supa")
    failures = []
    got: Dict[str, List[str]] = {}
    for r in rows:
        got.setdefault(r["check_id"], []).append(r["object"])
        if set(r) != {"severity", "check_id", "object", "problem", "fix_sql"}:
            failures.append(f"unexpected columns: {sorted(r)}")
        if r["severity"] not in ("critical", "high", "medium", "info"):
            failures.append(f"bad severity {r['severity']}")
    for check, objects in EXPECTED.items():
        found = got.get(check, [])
        if sorted(found) != sorted(objects):
            failures.append(f"{check}: expected {sorted(objects)}, got {found}")
    for check in got:
        if check not in EXPECTED:
            failures.append(f"unexpected check fired: {check} {got[check]}")
    for r in rows:
        if r["severity"] != "info" and any(f"public.{c}" in r["object"] or f'"{c}"' in r["object"] for c in CLEAN_OBJECTS):
            failures.append(f"clean object flagged: {r}")
    if "all_checks_passed" in got:
        failures.append("all_checks_passed shown although problems exist")

    # After applying every ready fix_sql the check must report all clear.
    fixes = "\n".join(r["fix_sql"].split("--")[0] for r in rows
                      if r["severity"] != "info" and r["fix_sql"].lstrip().lower().startswith(("alter", "drop", "revoke", "update")))
    fixes += "\nalter table public.posts drop column api_key;"
    pg.psql("supa", fixes)
    after = run_check(pg, "supa")
    serious = [r for r in after if r["severity"] in ("critical", "high", "medium")]
    if serious:
        failures.append(f"still serious after applying fix_sql: {serious}")
    if not any(r["check_id"] == "all_checks_passed" for r in after):
        failures.append("all_checks_passed row missing after fixes")
    return failures


def check_open_storage(pg: TempPostgres) -> List[str]:
    pg.psql("postgres", "create database store;")
    pg.psql("store", """
        create schema storage;
        create table storage.buckets (id text primary key, name text, public boolean);
        create table storage.objects (id uuid primary key, bucket_id text, name text);
        create policy "anyone uploads" on storage.objects for insert to anon with check (true);
    """)
    got = sorted((r["check_id"], r["object"]) for r in run_check(pg, "store"))
    want = [("open_write_policy", 'storage.objects (policy "anyone uploads")'),
            ("storage_rls_disabled", "storage.objects")]
    return [] if got == want else [f"open storage: expected {want}, got {got}"]


def check_plain_postgres(pg: TempPostgres) -> List[str]:
    pg.psql("postgres", "create database plain;")
    pg.psql("plain", "create table public.t (id int); create view public.v as select * from public.t;")
    rows = run_check(pg, "plain")
    if [r["check_id"] for r in rows] != ["all_checks_passed"]:
        return [f"plain postgres: expected only all_checks_passed, got {rows}"]
    return []


def main() -> None:
    bin_dir = find_pg_bin()
    if not bin_dir:
        print("SKIP: no PostgreSQL binaries (initdb, pg_ctl, psql) found; supabase_check.sql was not tested")
        return
    with TempPostgres(bin_dir) as pg:
        failures = check_plain_postgres(pg)  # first: roles are cluster-wide
        failures += check_supabase_like(pg) + check_open_storage(pg)
    if failures:
        print("FAIL\n" + "\n".join(failures))
        sys.exit(1)
    print(f"OK: {len(EXPECTED)} database checks fire once each, clean objects ignored, "
          "fix_sql clears every serious row, runs read-only, runs on plain Postgres")


if __name__ == "__main__":
    main()
