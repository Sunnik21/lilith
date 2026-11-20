#!/usr/bin/env python3
"""Builds a fake 'vibecoded' app in a temp folder and checks the scanner finds the holes.

Fake keys are assembled at runtime so this repo never contains strings that
look like real secrets (and GitHub push protection stays quiet).
Run: python3 tests/test_scan.py
"""
import base64
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.join(HERE, "..", "skills", "lilith", "scripts", "lilith_scan.py")


def b64(d):
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")


def fake(prefix, n=40):
    return prefix + ("A1b2C3d4E5" * 10)[:n]


SERVICE_JWT = "eyJ" + b64({"alg": "HS256"})[3:] + "." + b64({"iss": "supabase", "role": "service_role", "ref": "abcdefghijklmnop"}) + "." + "s1gnatureS1gnatureS1gnature"
ANON_JWT = "eyJ" + b64({"alg": "HS256"})[3:] + "." + b64({"iss": "supabase", "role": "anon", "ref": "abcdefghijklmnop"}) + "." + "s1gnatureS1gnatureS1gnature"

BAD_APP = {
    "package.json": json.dumps({"dependencies": {"next": "15.0.0", "@supabase/supabase-js": "2", "openai": "4", "stripe": "16"}}),
    ".gitignore": "node_modules\n",
    ".env": f"OPENAI_API_KEY={fake('sk-' + 'proj-')}\nSUPABASE_SERVICE_ROLE_KEY={SERVICE_JWT}\n",
    ".env.example": "OPENAI_API_KEY=\n",
    "lib/ai.ts": "const key = process.env.NEXT_PUBLIC_OPENAI_API_KEY;\n",
    "components/Chat.tsx": '"use client";\nimport OpenAI from "openai";\nconst openai = new OpenAI({ apiKey: k, dangerouslyAllowBrowser: true });\nconsole.log("hi");\nexport default function Chat(){ return <div dangerouslySetInnerHTML={{__html: msg}} /> }\n',
    "lib/supabaseAdmin.ts": f'export const admin = createClient(url, "{SERVICE_JWT}");\n',
    "lib/supabase.ts": f'export const supabase = createClient(url, "{ANON_JWT}");\n',
    "lib/stripe.ts": f'const stripe = new Stripe("{fake("sk_" + "live_", 30)}");\n',
    "app/api/notes/route.ts": "export async function POST(req){ const b = await req.json(); await supabase.from('notes').insert(b); return Response.json({ok:true}) }\n",
    "app/api/stripe/webhook/route.ts": "export async function POST(req){ const event = await req.json(); if(event.type==='checkout.session.completed'){ await grantPro(event) } }\n",
    "app/api/chat/route.ts": "import OpenAI from 'openai';\nexport async function POST(req){ const s = await auth(); const r = await openai.chat.completions.create({}); }\n",
    "app/api/seed/route.ts": "export async function GET(){ await db.user.create({ data: { email: 'admin@admin.com', password: 'admin123' } }) }\n",
    "supabase/migrations/001.sql": "create table public.notes (id uuid primary key, user_id uuid, body text);\ncreate policy \"anyone\" on public.notes for all using (true) with check (true);\n",
    "firestore.rules": "service cloud.firestore { match /databases/{db}/documents { match /{d=**} { allow read, write: if true; } } }\n",
    "app/page.tsx": "export default function P(){ return <section><p>FEATURES</p><h1>John Doe loves it</h1><button onClick={() => {}}>Go</button></section> }\n// TODO: real data\n",
    "README.md": "# Welcome to your Lovable project\n",
    # server-side patterns added with the benchmark (written differently from bench fixtures)
    "server/lib/session.ts": "import jwt from 'jsonwebtoken';\nexport function readUser(t){ return jwt.decode(t) }\n",
    "server/lib/settings.ts": "export const signingKey = process.env.SESSION_SECRET ?? 'dev-session-key-123';\n",
    "server/routes/profile.js": "router.put('/profile/:id', requireAuth, async (req,res)=>{ await db.profile.update({ where: { id: req.params.id }, data: req.body }) })\n",
    "server/routes/files.js": "const up = multer();\nrouter.post('/files', requireAuth, up.single('f'), (req,res)=>res.json({}))\n",
    "server/errors.js": "app.use((e, req, res, next) => res.status(500).send({ message: e.message, stack: e.stack }))\n",
    "server/cors.ts": "res.setHeader('Access-Control-Allow-Origin', req.headers.origin);\nres.setHeader('Access-Control-Allow-Credentials', 'true');\n",
    "app/api/pay/route.ts": "export async function POST(req){ const s = await getCurrentUser(); const { amount } = await req.json(); await stripe.checkout.sessions.create({ line_items: [{ price_data: { currency: 'eur', unit_amount: amount,\n product_data: {name:'x'} } }] }) }\n",
    "supabase/migrations/002.sql": "create table public.invoices (id uuid, user_id uuid);\nalter table public.invoices enable row level security;\ncreate policy \"members\" on public.invoices for select to authenticated using (true);\n",
}

CLEAN_APP = {
    "package.json": json.dumps({"dependencies": {"next": "15.0.0", "@supabase/ssr": "0.5"}}),
    "package-lock.json": "{}",
    ".gitignore": "node_modules\n.env*\n!.env.example\n",
    ".env.example": "SUPABASE_URL=\nSUPABASE_ANON_KEY=\n",
    "app/api/notes/route.ts": "export async function POST(req){ const { data: { user } } = await supabase.auth.getUser(); if(!user) return new Response('no',{status:401}); await supabase.from('notes').insert({ user_id: user.id }); }\n",
    "supabase/migrations/001.sql": "create table public.notes (id uuid primary key, user_id uuid);\nalter table public.notes enable row level security;\ncreate policy \"own\" on public.notes for select to authenticated using ((select auth.uid()) = user_id);\n",
    "README.md": "# Notes app\n",
    "app/layout.tsx": "export default function L(){ return <script type=\"application/ld+json\" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} /> }\n",
    "__tests__/login.test.ts": "it('logs in', async () => { await login({ email: 'a@b.co', password: 'password123' }) })\n",
    "app/api/auth/login/route.ts": "export async function POST(req){ const r = await ratelimit.limit(ip); const { email, password } = await req.json(); await supabase.auth.signInWithPassword({ email, password }); }\n",
    "app/api/admin/plan/route.ts": "export async function POST(req){ const a = await requireAdmin(); await supabaseAdmin.from('profiles').update({ plan: 'pro' }).eq('id', a.id) }\n",
    "middleware.ts": "const ALLOWED_ORIGINS = ['https://app.example.org'];\nif (ALLOWED_ORIGINS.includes(origin)) { res.headers.set('Access-Control-Allow-Origin', origin); res.headers.set('Access-Control-Allow-Credentials', 'true') }\n",
    "supabase/migrations/002.sql": "create table public.contact (id uuid, email text);\nalter table public.contact enable row level security;\ncreate policy \"send\" on public.contact for insert to anon with check (true);\n",
}


# A CLI repo with a gitignored scratch folder: ignored folders are skipped, a local .env and new files are not.
IGNORED_APP = {
    "package.json": json.dumps({"name": "tool", "bin": {"tool": "bin/tool.mjs"}}),
    "package-lock.json": "{}",
    ".gitignore": ".env\nscratch/\n",
    "bin/tool.mjs": "export const run = () => 1;\n",
    "tools/check.py": "def check() -> int:\n    return 1\n",
    "fixtures/expected.json": json.dumps({"bugs": [{"check": "S2", "note": "NEXT_PUBLIC_OPENAI_API_KEY in the bundle"}]}),
}
IGNORED_APP_LOCAL = {
    "scratch/copy/pay.ts": f"export const key = '{fake('sk_' + 'live_', 30)}';\n",
    "new/pay.ts": f"export const key = '{fake('sk_' + 'live_', 30)}';\n",
    ".env": f"VITE_OPENAI_API_KEY={fake('sk-' + 'proj-')}\n",
}


def check_ignored_app(failures):
    """Gitignored folders are skipped and reported; the stack is named; JSON manifests are not criticals."""
    with tempfile.TemporaryDirectory() as root:
        write_app(root, IGNORED_APP)
        write_app(root, IGNORED_APP_LOCAL, commit=False)
        data = run_json(root)
        leads = data["findings"]
        if any(x["file"].startswith("scratch/") for x in leads):
            failures.append("ignored app: leads from a gitignored folder")
        if "scratch/" not in data.get("skipped_ignored", []):
            failures.append("ignored app: skipped gitignored folder not reported")
        if not any(x["file"] == "new/pay.ts" and x["check"] == "S1" for x in leads):
            failures.append("ignored app: untracked (not ignored) file was not scanned")
        if not any(x["file"] == ".env" and x["check"] == "S2" and x["severity"] == "critical" for x in leads):
            failures.append("ignored app: gitignored .env must still be checked for public-prefixed secrets")
        if any(x["file"].endswith("expected.json") and x["severity"] in ("critical", "high") for x in leads):
            failures.append("ignored app: env name inside a JSON data file flagged as critical/high")
        for name in ("Node CLI", "Python"):
            if name not in data["stack"]:
                failures.append(f"ignored app: stack does not name {name}: {data['stack']}")
        brief = subprocess.run([sys.executable, SCANNER, root], capture_output=True, text=True, check=True).stdout
        if "Skipped (gitignored): scratch/" not in brief:
            failures.append("ignored app: brief output does not list skipped folders")


def write_app(root, files, commit=True):
    for rel, content in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(content)
    if commit:
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        subprocess.run(["git", "init", "-q", root], check=True)
        subprocess.run(["git", "-C", root, "add", "-A", "-f"], check=True)
        subprocess.run(["git", "-C", root, "commit", "-qm", "init"], check=True, env=env)


def run_json(root, *extra):
    out = subprocess.run([sys.executable, SCANNER, root, "--json", *extra], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def run(root):
    return run_json(root)["findings"]


def main():
    failures = []
    with tempfile.TemporaryDirectory() as bad:
        write_app(bad, BAD_APP)
        f = run(bad)
        def has(check, sev=None, text=""):
            return any(x["check"] == check and (sev is None or x["severity"] == sev) and text in (x["file"] + x["note"]) for x in f)
        expect = [
            ("S1", "critical", ".env"),                      # committed env file
            ("S1", "critical", "service_role"),              # hard-coded service role
            ("S1", "critical", "Stripe live"),
            ("S1", "medium", ".gitignore"),
            ("S2", "critical", "NEXT_PUBLIC_OPENAI_API_KEY"),
            ("S2", "critical", "Chat.tsx"),
            ("S3", "critical", "001.sql"),
            ("S3", "high", "notes"),
            ("S3", "critical", "firestore.rules"),
            ("S4", "high", "api/notes"),
            ("S7", "critical", "webhook"),
            ("S8", "medium", "api/chat"),
            ("S9", "medium", "dangerouslySetInnerHTML"),
            ("S12", "medium", "seed"),
            ("C1", "cleanup", "Chat.tsx"),
            ("C2", "cleanup", "page.tsx"),
            ("C3", "cleanup", "page.tsx"),
            ("C8", "info", "README"),
            ("S4", "critical", "session.ts"),            # jwt.decode without verify
            ("S1", "high", "settings.ts"),               # hard-coded fallback secret
            ("S5", "high", "profile.js"),                # id from URL, no owner filter
            ("S6", "high", "profile.js"),                # data: req.body
            ("S10", "medium", "files.js"),               # multer with no limits
            ("S12", "medium", "errors.js"),              # stack trace in response
            ("S14", "high", "cors.ts"),                  # reflected origin + credentials
            ("S6", "high", "api/pay"),                   # amount from the request
            ("S3", "medium", "every logged-in user"),    # select to authenticated using (true)
        ]
        for check, sev, text in expect:
            if not has(check, sev, text):
                failures.append(f"bad app: expected {check} {sev} '{text}'")
        # read plan names the files to read for S3, S4 and S7
        data = run_json(bad)
        plan = {e["file"]: e["checks"] for e in data["read_plan"]}
        for path, check in [("supabase/migrations/001.sql", "S3"), ("firestore.rules", "S3"),
                            ("app/api/notes/route.ts", "S4"), ("app/api/stripe/webhook/route.ts", "S7")]:
            if check not in plan.get(path, []):
                failures.append(f"read plan: expected {path} for {check}, got {plan.get(path)}")
        if data["read_plan"][0]["file"] in ("README.md", "package.json"):
            failures.append("read plan: least suspicious file ranked first")
        if data["size"]["class"] != "small" or data["size"]["files"] < 10:
            failures.append(f"size: unexpected {data['size']}")
        capped = run_json(bad, "--plan-limit", "3")
        if len(capped["read_plan"]) != 3 or capped["read_plan_left_out"] < 1:
            failures.append("read plan: --plan-limit not applied")
        brief = subprocess.run([sys.executable, SCANNER, bad], capture_output=True, text=True, check=True).stdout
        if "Read plan" not in brief or "console.log/debugger in" not in brief or "\n\n" in brief:
            failures.append("brief output: missing read plan, grouped cleanup, or has blank lines")
        # anon key must not be flagged as a secret
        if any("supabase.ts" in x["file"] and x["check"] == "S1" for x in f):
            failures.append("bad app: anon key wrongly flagged")
        # secrets must be masked
        raw = json.dumps(f)
        if fake("sk_" + "live_", 30) in raw or SERVICE_JWT in raw:
            failures.append("bad app: secret printed unmasked")
    with tempfile.TemporaryDirectory() as clean:
        write_app(clean, CLEAN_APP)
        f = run(clean)
        serious = [x for x in f if x["severity"] in ("critical", "high", "medium")]
        if serious:
            failures.append("clean app: unexpected leads " + json.dumps(serious))
    check_ignored_app(failures)
    if failures:
        print("FAIL\n" + "\n".join(failures))
        sys.exit(1)
    print(f"OK: {len(expect)} expected leads found, read plan names S3/S4/S7 files, anon key ignored, secrets masked, clean app has no serious leads, gitignored folders skipped")


if __name__ == "__main__":
    main()
