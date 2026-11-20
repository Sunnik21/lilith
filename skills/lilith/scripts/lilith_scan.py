#!/usr/bin/env python3
"""Lilith quick scan: find leads for security and cleanup checks.

Usage:
  python3 lilith_scan.py [project-root] [--brief | --full] [--json] [--plan-limit N]

Prints the project size, one line per security lead, cleanup as grouped
counts, and a READ PLAN: the files to read to confirm or rule out each check,
most suspicious first. Every hit is a LEAD for the agent to confirm by
reading the code, not a confirmed finding. --full lists every lead.
Secrets are always masked. Python 3.8+, standard library only.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
from typing import Iterator, List, Set, Tuple

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit", ".astro",
    ".output", ".vercel", ".netlify", "coverage", ".venv", "venv", "__pycache__", ".turbo",
    ".expo", "ios", "android", ".cache", "out", "vendor", ".idea", ".vscode",
    ".claude", ".cursor", ".agents", ".codex", ".windsurf",  # agent configs and installed skills
}
SELF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # this skill's folder
SKIP_FILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "poetry.lock", "Cargo.lock"}
CODE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".py", ".rb", ".go", ".php", ".html"}
TEXT_EXT = CODE_EXT | {".json", ".yml", ".yaml", ".toml", ".sql", ".rules", ".md", ".env", ".txt", ".sh", ".tf", ".ini", ".cfg"}
MAX_BYTES = 1_000_000
BIG_FILE_LINES = 400
LONG_FILE_LINES = 300          # read plan gives line ranges for files longer than this
PLAN_LIMIT = 25
SKIPPED_SHOWN = 6             # gitignored folders named in the text output
SIZE_CLASSES = [("small", 60, 8_000), ("medium", 400, 60_000)]  # (name, max files, max lines); else large
RULE_FILES = ("firestore.rules", "storage.rules", "database.rules.json")
LEAD_WEIGHT = {"critical": 8, "high": 4, "medium": 2, "info": 0.5, "cleanup": 0}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "cleanup": 3, "info": 4}

CHECK_TITLES = {
    "S1": "Secret keys in code or git",
    "S2": "Secret keys sent to the browser",
    "S3": "Database rules may be open",
    "S4": "API routes to check for login",
    "S5": "Records loaded without an owner check",
    "S6": "Server trusts what the browser sends",
    "S7": "Webhook without signature check",
    "S8": "Endpoints to check for rate limits",
    "S9": "Unsafe HTML / code execution",
    "S10": "Storage / upload to check",
    "S12": "Debug / test doors",
    "S13": "Packages",
    "S14": "CORS / headers",
    "C1": "Leftover logs and debugger",
    "C2": "Fake / placeholder data",
    "C3": "TODOs and empty handlers",
    "C6": "Giant files",
    "C8": "Template leftovers",
}

# ---------------------------------------------------------------- secrets (S1)

SECRET_PATTERNS = [
    ("Stripe live secret key", r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,}", "critical"),
    ("Stripe test secret key", r"\b(?:sk|rk)_test_[0-9A-Za-z]{16,}", "medium"),
    ("Stripe webhook secret", r"\bwhsec_[0-9A-Za-z]{20,}", "critical"),
    ("OpenAI key", r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{32,}", "critical"),
    ("Anthropic key", r"\bsk-ant-[A-Za-z0-9_\-]{32,}", "critical"),
    ("AWS access key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "critical"),
    ("GitHub token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{50,}", "critical"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}", "critical"),
    ("Google API key", r"\bAIza[0-9A-Za-z_\-]{35}", "info"),
    ("Private key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----\s*[A-Za-z0-9+/=\\n]{40,}", "critical"),
    ("Database URL with password", r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|rediss)://[^\s:/@'\"`]+:[^\s@'\"`]{3,}@[^\s'\"`]+", "critical"),
    ("SendGrid key", r"\bSG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}", "critical"),
    ("Resend key", r"\bre_[A-Za-z0-9]{8,}_[A-Za-z0-9]{16,}", "critical"),
    ("Twilio key", r"\bSK[0-9a-fA-F]{32}\b", "high"),
    ("Groq key", r"\bgsk_[A-Za-z0-9]{40,}", "critical"),
    ("Hugging Face token", r"\bhf_[A-Za-z0-9]{30,}", "high"),
    ("Replicate token", r"\br8_[A-Za-z0-9]{30,}", "critical"),
]
SECRET_RX = [(name, re.compile(rx), sev) for name, rx, sev in SECRET_PATTERNS]
JWT_RX = re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")
PLACEHOLDER_RX = re.compile(r"(?i)(x{6,}|your[_\-]?(?:api[_\-]?)?key|example|placeholder|dummy|<[^>]+>|\*{4,}|\.\.\.|changeme|replace[_\-]?me)")

PUBLIC_PREFIX_RX = re.compile(
    r"\b(NEXT_PUBLIC_|VITE_|REACT_APP_|EXPO_PUBLIC_|PUBLIC_|NUXT_PUBLIC_|GATSBY_)"
    r"([A-Z0-9_]*(?:SECRET|SERVICE_ROLE|SERVICE_KEY|PRIVATE|OPENAI|ANTHROPIC|GROQ|GEMINI_API|STRIPE_SECRET|STRIPE_SK|"
    r"RESEND|SENDGRID|TWILIO_AUTH|DATABASE_URL|DB_PASS|ADMIN_KEY|WEBHOOK_SECRET|REPLICATE)[A-Z0-9_]*)\b"
)


def mask(value):
    value = value.strip()
    if len(value) <= 12:
        return value[:3] + "••••"
    return value[:8] + "••••" + value[-4:]


def jwt_role(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role")
    except Exception:
        return None


# ------------------------------------------------------------- code patterns

CLIENT_SECRET_USE = [
    (re.compile(r"new\s+OpenAI\s*\("), "OpenAI client"),
    (re.compile(r"new\s+Anthropic\s*\("), "Anthropic client"),
    (re.compile(r"api\.openai\.com|api\.anthropic\.com|api\.groq\.com"), "direct AI API call"),
    (re.compile(r"dangerouslyAllowBrowser\s*:\s*true"), "dangerouslyAllowBrowser"),
    (re.compile(r"(?i)service[_\-]?role"), "Supabase service_role"),
    (re.compile(r"new\s+Stripe\s*\("), "Stripe secret client"),
]

DANGEROUS_SINKS = [
    (re.compile(r"dangerouslySetInnerHTML"), "dangerouslySetInnerHTML"),
    (re.compile(r"\bv-html\b"), "v-html"),
    (re.compile(r"\{@html\b"), "{@html}"),
    (re.compile(r"\.innerHTML\s*=(?!=)"), ".innerHTML ="),
    (re.compile(r"document\.write\s*\("), "document.write"),
    (re.compile(r"(?<![\w.])eval\s*\("), "eval("),
    (re.compile(r"new\s+Function\s*\("), "new Function("),
    (re.compile(r"child_process|\bexecSync\s*\(|\bexec\s*\(\s*[`'\"].*\$\{"), "shell exec"),
    (re.compile(r"\$queryRawUnsafe|\$executeRawUnsafe|\.raw\s*\(\s*`[^`]*\$\{|sql\.unsafe\s*\("), "raw SQL with interpolation"),
]

CORS_RX = [
    (re.compile(r"Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*"), "Allow-Origin: *"),
    (re.compile(r"key\s*:\s*['\"]Access-Control-Allow-Origin['\"]\s*,\s*value\s*:\s*['\"]\*"), "Allow-Origin: *"),
    (re.compile(r"Access-Control-Allow-Origin['\"]\s*,\s*(?:origin\b|(?:req|request)\.headers)"), "Allow-Origin reflects the request origin"),
    (re.compile(r"origin\s*:\s*(?:true|['\"]\*['\"])"), "cors origin any"),
]
CREDENTIALS_RX = re.compile(r"credentials\s*:\s*true|Allow-Credentials['\"]?\s*[:,]\s*['\"]?true")

LOG_RX = re.compile(r"(?<![\w.])console\.(?:log|debug|trace|table)\s*\(|^\s*debugger\s*;?\s*$", re.M)
TODO_RX = re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b")
EMPTY_HANDLER_RX = re.compile(r"on[A-Z]\w*=\{\s*\(\s*\)\s*=>\s*\{\s*\}\s*\}|href=['\"]#['\"]")
FAKE_DATA_RX = re.compile(
    r"(?i)\b(?:lorem ipsum|mock(?:Data|Users|Products|Orders)?\b|fake(?:Data|Users)\b|dummy(?:Data)?\b|sample(?:Data|Users|Products)\b|"
    r"John Doe|Jane (?:Doe|Smith)|Acme(?: Inc| Corp)?)\b|placehold\.co|via\.placeholder\.com|picsum\.photos|test@example\.com"
)
TEMPLATE_RX = re.compile(r"(?i)Welcome to your Lovable project|Get started by editing|Vite \+ React|Create Next App|bolt\.new|This project was bootstrapped")
DEBUG_ROUTE_RX = re.compile(r"(?i)(?:^|/)(?:debug|seed|test|testing|dev|_dev|admin-?test)(?:/|$|\.)")
TEST_CRED_RX = re.compile(r"(?i)['\"](?:admin@admin\.com|admin@example\.com|test@test\.com)['\"]|password\s*[:=]\s*['\"](?:password|password123|admin|123456|admin123|test123)['\"]")

TEST_FILE_RX = re.compile(r"(?i)(?:^|/)(?:tests?|__tests__|spec|specs|e2e|cypress|playwright)/|\.(?:test|spec)\.[jt]sx?$")
AUTH_ENDPOINT_RX = re.compile(r"(?i)sign-?up|sign-?in|log-?in|register|reset-?password|forgot-?password|otp|magic-?link")
AUTH_ROUTE_STRING_RX = re.compile(r"(?i)\.(?:post|put)\s*\(\s*['\"`][^'\"`]*(?:sign-?up|sign-?in|log-?in|register|reset|forgot|otp|magic-?link)")
FALLBACK_SECRET_RX = re.compile(r"process\.env\.[A-Z0-9_]*(?:SECRET|PRIVATE|PASSWORD|TOKEN|API_KEY)[A-Z0-9_]*\s*(?:\|\||\?\?)\s*['\"`][^'\"`]{6,}['\"`]")
JWT_DECODE_RX = re.compile(r"\bjwt\.decode\s*\(|\bjwtDecode\s*\(")
JWT_VERIFY_RX = re.compile(r"\bjwt\.verify\s*\(|\bjwtVerify\s*\(|\bverifyJwt\s*\(")
STACK_LEAK_RX = re.compile(r"\bstack\s*:\s*(?:err|error|e)\.stack\b")
MASS_ASSIGN_RX = re.compile(r"\bdata\s*:\s*req\.body\b|\.(?:update|insert|upsert)\s*\(\s*(?:req\.body|body|await\s+req\.json\(\))\s*\)")
CLIENT_PRICE_RX = re.compile(r"\bunit_amount\s*:\s*(?:body\.|req\.body\.)?[a-z_]\w*\s*[,}\n]")
ID_FROM_REQUEST_RX = re.compile(
    r"where\s*:\s*\{\s*id\s*:\s*(?:req\.params|req\.query|req\.body|params)\.\w+\s*\}|"
    r"\.eq\(\s*['\"]id['\"]\s*,\s*(?:params|req\.params|searchParams)\b"
)
OWNER_FILTER_RX = re.compile(r"(?i)\b(?:user_?id|owner_?id|author_?id|created_by)\b\s*[:,]|\.eq\(\s*['\"](?:user_id|owner_id|author_id|created_by)")
ADMIN_CLIENT_RX = re.compile(r"(?i)supabaseAdmin|service_?role|adminClient")
UPLOAD_RISK_RX = re.compile(r"multer\s*\(\s*\)|multer\s*\(\s*\{\s*(?:storage|dest)\s*(?::\s*[^,}]+)?\s*\}\s*\)|cb\s*\(\s*null\s*,\s*file\.originalname\s*\)")

AUTH_HINT_RX = re.compile(
    r"getUser\(|getServerSession|auth\(\)|currentUser\(|getAuth\(|verifyIdToken|requireAuth|requireUser|withAuth|"
    r"clerkClient|getToken\(|session\?\.user|jwt\.verify|verifyJwt|getKindeServerSession|validateRequest|lucia|"
    r"Authorization|authenticate|isAuthenticated|protectedProcedure|auth\.api\.getSession|"
    r"\b(?:get|require|ensure|check|verify)(?:Current|Logged[Ii]n)?(?:User|Admin|Session|Auth)\w*\s*\("
)
RATELIMIT_HINT_RX = re.compile(r"(?i)ratelimit|rate-limit|rate_limit|limiter|slowDown|throttle")
WEBHOOK_VERIFY_RX = re.compile(r"constructEvent|constructEventAsync|svix|Webhook\(|verifySignature|createHmac|timingSafeEqual|verifyWebhook|validateEvent|x-signature|signature", re.I)
AI_USE_RX = re.compile(r"openai|anthropic|generateText|streamText|chat\.completions|messages\.create|groq|gemini|replicate", re.I)
EMAIL_USE_RX = re.compile(r"resend|sendgrid|nodemailer|postmark|mailgun|twilio", re.I)


# ------------------------------------------------------------------ helpers

def git_tracked(root):
    try:
        out = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True, timeout=20)
        if out.returncode == 0:
            return set(out.stdout.splitlines())
    except Exception:
        pass
    return None


def git_ignored(root: str) -> Tuple[Set[str], Set[str]]:
    """Gitignored (folders, files) under root, relative to it. Empty without git or inside an ignored folder."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory"],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:
        return set(), set()
    if out.returncode != 0:
        return set(), set()
    paths = [p for p in out.stdout.split("\0") if p]
    return {p.rstrip("/") for p in paths if p.endswith("/")}, {p for p in paths if not p.endswith("/")}


def reportable_ignored(ignored_dirs: Set[str]) -> List[str]:
    """Skipped gitignored folders worth telling the agent about (not node_modules and the like)."""
    def is_noise(path: str) -> bool:
        return any(part in SKIP_DIRS or part.startswith(".git") for part in path.split("/"))
    return sorted(d + "/" for d in ignored_dirs if not is_noise(d))


def git_history_env(root):
    try:
        out = subprocess.run(
            ["git", "-C", root, "log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            return sorted({p for p in out.stdout.splitlines() if is_env_file(os.path.basename(p))})
    except Exception:
        pass
    return []


def is_env_file(name):
    n = name.lower()
    if not (n == ".env" or n.startswith(".env.") or n.endswith(".env")):
        return False
    return not any(x in n for x in ("example", "sample", "template", "defaults"))


def iter_files(root: str, ignored_dirs: Set[str] = frozenset(), ignored_files: Set[str] = frozenset()) -> Iterator[str]:
    """Text files to scan. Gitignored folders are skipped; gitignored files too, except env files."""
    def rel_of(dirpath: str, name: str) -> str:
        return os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")
                       and os.path.abspath(os.path.join(dirpath, d)) != SELF_DIR
                       and rel_of(dirpath, d) not in ignored_dirs]
        for f in filenames:
            if f in SKIP_FILES:
                continue
            if not is_env_file(f) and rel_of(dirpath, f) in ignored_files:
                continue
            path = os.path.join(dirpath, f)
            ext = os.path.splitext(f)[1].lower()
            if ext not in TEXT_EXT and not is_env_file(f) and f not in ("Dockerfile", ".gitignore"):
                continue
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield path


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def is_minified(text):
    lines = text.splitlines() or [""]
    return len(text) > 5000 and len(lines) < 10


def is_client_file(rel, text, project):
    if '"use client"' in text[:300] or "'use client'" in text[:300]:
        return True
    if '"use server"' in text[:300] or "'use server'" in text[:300]:
        return False
    low = rel.replace("\\", "/").lower()
    server_markers = ("/api/", "pages/api", "app/api", "/server/", "supabase/functions", "netlify/functions",
                      "/functions/", "route.ts", "route.js", "+server.", "+page.server", ".server.", "middleware.",
                      "server.ts", "server.js", "/trpc/", "/actions/", "convex/")
    if any(m in low for m in server_markers):
        return False
    if project["spa"] and low.startswith(("src/", "app/", "components/")) and low.endswith((".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte")):
        return True
    if low.endswith((".tsx", ".jsx")) and ("components/" in low or "/pages/" in low and "pages/api" not in low):
        return True
    return False


def detect_project(root):
    info = {"stack": [], "spa": False}
    pkg = read(os.path.join(root, "package.json"))
    deps = {}
    has_bin = False
    if pkg:
        try:
            data = json.loads(pkg)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            has_bin = bool(data.get("bin"))
        except Exception:
            pass
    names = set(deps)
    def has(*xs):
        return any(x in names for x in xs)
    if has("next"): info["stack"].append("Next.js")
    if has("vite") and not has("next", "@sveltejs/kit", "astro", "@remix-run/react"):
        info["stack"].append("Vite"); info["spa"] = True
    if has("react-scripts"): info["stack"].append("Create React App"); info["spa"] = True
    if has("@sveltejs/kit"): info["stack"].append("SvelteKit")
    if has("nuxt"): info["stack"].append("Nuxt")
    if has("astro"): info["stack"].append("Astro")
    if has("expo", "react-native"): info["stack"].append("Expo/React Native"); info["spa"] = True
    if has("express", "fastify", "hono", "koa"): info["stack"].append("Node server")
    if has("@supabase/supabase-js", "@supabase/ssr") or os.path.isdir(os.path.join(root, "supabase")): info["stack"].append("Supabase")
    if has("firebase", "firebase-admin") or os.path.exists(os.path.join(root, "firebase.json")): info["stack"].append("Firebase")
    if has("convex"): info["stack"].append("Convex")
    if has("@prisma/client", "prisma"): info["stack"].append("Prisma")
    if has("drizzle-orm"): info["stack"].append("Drizzle")
    if has("stripe", "@stripe/stripe-js"): info["stack"].append("Stripe")
    if has("openai", "@anthropic-ai/sdk", "ai", "@ai-sdk/openai", "groq-sdk", "@google/generative-ai"): info["stack"].append("AI API")
    if has("@clerk/nextjs", "@clerk/clerk-react"): info["stack"].append("Clerk")
    if has("recharts", "chart.js", "react-chartjs-2", "@nivo/core", "victory", "d3", "apexcharts", "react-apexcharts",
           "echarts", "echarts-for-react", "@tremor/react", "highcharts", "@visx/visx", "lightweight-charts", "plotly.js"):
        info["stack"].append("Charts")
    if has("@lemonsqueezy/lemonsqueezy.js", "@paddle/paddle-js", "@paddle/paddle-node-sdk"): info["stack"].append("Payments")
    if has("next-auth", "@auth/core", "better-auth", "lucia"): info["stack"].append("Auth library")
    if os.path.exists(os.path.join(root, "vercel.json")): info["stack"].append("Vercel")
    if os.path.exists(os.path.join(root, "netlify.toml")): info["stack"].append("Netlify")
    if os.path.exists(os.path.join(root, "Dockerfile")) or os.path.exists(os.path.join(root, "docker-compose.yml")): info["stack"].append("Docker")
    if has_bin: info["stack"].insert(0, "Node CLI")
    elif pkg and not info["stack"]: info["stack"].append("Node.js")
    if any(os.path.exists(os.path.join(root, py)) for py in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile")):
        info["stack"].append("Python")
    info["has_lockfile"] = any(os.path.exists(os.path.join(root, f)) for f in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"))
    info["has_package_json"] = bool(pkg)
    return info


def is_server_route(rel, text):
    low = rel.replace("\\", "/").lower()
    if re.search(r"(^|/)(app|src/app)/.*api/.*route\.(t|j)sx?$", low): return True
    if re.search(r"(^|/)pages/api/", low): return True
    if "supabase/functions/" in low and low.endswith(("index.ts", "index.js")): return True
    if "netlify/functions/" in low or re.search(r"(^|/)api/[^/]+\.(t|j)s$", low): return True
    if re.search(r"\+server\.(t|j)s$", low): return True
    if ('"use server"' in text[:300] or "'use server'" in text[:300]): return True
    if re.search(r"\b(?:app|router)\.(?:get|post|put|patch|delete)\s*\(", text): return True
    return False


def scan_server_code(rel, text, add):
    """Leads that only make sense in server code: tokens, ownership, trusted input, uploads, errors."""
    if JWT_DECODE_RX.search(text) and not JWT_VERIFY_RX.search(text):
        m = JWT_DECODE_RX.search(text)
        add("S4", "critical", rel, line_of(text, m.start()), "token is decoded but never verified: anyone can make their own token")
    for m in ID_FROM_REQUEST_RX.finditer(text):
        if OWNER_FILTER_RX.search(text[m.start():m.start() + 300]):
            continue
        if m.group(0).startswith(".eq") and not ADMIN_CLIENT_RX.search(text):
            continue  # user's own Supabase client: RLS decides, see S3
        add("S5", "high", rel, line_of(text, m.start()), "record loaded by an id from the request with no owner filter: check users can't open each other's data")
    for m in MASS_ASSIGN_RX.finditer(text):
        add("S6", "high", rel, line_of(text, m.start()), "whole request body written to the database: users can set fields like role or plan")
    if re.search(r"req\.json\(\)|req\.body", text):
        for m in CLIENT_PRICE_RX.finditer(text):
            add("S6", "high", rel, line_of(text, m.start()), "payment amount may come from the request: look prices up on the server")
    for m in UPLOAD_RISK_RX.finditer(text):
        add("S10", "medium", rel, line_of(text, m.start()), "upload with no size/type limit or with the user's file name")
        break
    for m in STACK_LEAK_RX.finditer(text):
        add("S12", "medium", rel, line_of(text, m.start()), "stack trace sent in the response: return a generic error, log details on the server")


def plan_hints(rel, name, ext, text, is_code, client):
    """Checks a file is worth reading for, even when no regex fired."""
    low = rel.replace("\\", "/").lower()
    checks = set()
    if ext in (".sql", ".rules") or name in RULE_FILES:
        checks.add("S3")
    if not is_code or TEST_FILE_RX.search(low):
        return checks
    if is_server_route(rel, text):
        checks.update(("S4", "S5", "S6"))
        if "webhook" in low or "webhook" in text[:2000].lower():
            checks.add("S7")
        if AI_USE_RX.search(text) or EMAIL_USE_RX.search(text) or AUTH_ENDPOINT_RX.search(low):
            checks.add("S8")
        if DEBUG_ROUTE_RX.search(low):
            checks.add("S12")
    if client and (AI_USE_RX.search(text) or "process.env" in text or "import.meta.env" in text):
        checks.add("S2")
    if client and re.search(r"(?i)useSearchParams|searchParams|[?&]success", text) and re.search(r"(?i)\.update\(|\bplan\b|premium|isPro", text):
        checks.add("S7")
    if any(rx.search(text) for rx, _label in DANGEROUS_SINKS):
        checks.add("S9")
    if re.search(r"(?i)multer|formidable|busboy|storage\.from\(|createBucket|\.upload\(", text):
        checks.add("S10")
    if re.search(r"(?i)system_?prompt|role\s*:\s*['\"]system['\"]|\btools\s*:\s*\[", text):
        checks.add("S11")
    if re.search(r"Access-Control-Allow|\bcors\s*\(", text) or name.startswith(("middleware.", "next.config")):
        checks.add("S14")
    return checks


def size_class(files, lines):
    for name, max_files, max_lines in SIZE_CLASSES:
        if files <= max_files and lines <= max_lines:
            return name
    return "large"


def read_plan(findings, hints, file_lines, limit=PLAN_LIMIT):
    """Files to read, most suspicious first: (entries, number left out)."""
    score, checks, lines = {}, {}, {}
    for f in findings:
        if not f["check"].startswith("S"):
            continue
        rel = f["file"]
        score[rel] = score.get(rel, 0) + LEAD_WEIGHT[f["severity"]]
        checks.setdefault(rel, set()).add(f["check"])
        if f["line"]:
            lines.setdefault(rel, []).append(f["line"])
    for rel, cs in hints.items():
        score[rel] = score.get(rel, 0) + len(cs)
        checks.setdefault(rel, set()).update(cs)
    order = sorted(score, key=lambda r: (-score[r], r))
    entries = []
    for rel in order[:limit]:
        n = file_lines.get(rel, 0)
        span = None
        if n > LONG_FILE_LINES and rel in lines:
            span = [max(1, min(lines[rel]) - 10), min(n, max(lines[rel]) + 30)]
        entries.append({"file": rel, "checks": sorted(checks[rel], key=lambda c: int(c[1:])), "lines": span, "file_lines": n})
    return entries, max(0, len(order) - limit)


# --------------------------------------------------------------------- scan

def scan(root, max_examples):
    root = os.path.abspath(root)
    project = detect_project(root)
    tracked = git_tracked(root)
    ignored_dirs, ignored_files = git_ignored(root)
    findings = []

    def add(check, severity, rel, line, note):
        findings.append({"check": check, "severity": severity, "file": rel, "line": line, "note": note})

    # env files and gitignore
    gitignore = read(os.path.join(root, ".gitignore")) or ""
    has_env_files = any(is_env_file(f) for f in os.listdir(root))
    if (project["has_package_json"] or has_env_files) and not re.search(r"^\s*\.env", gitignore, re.M) and not re.search(r"^\s*\*\.env|^\s*\.env\*", gitignore, re.M):
        add("S1", "medium", ".gitignore", 0, ".env is not in .gitignore")
    if tracked is not None:
        for p in sorted(tracked):
            if is_env_file(os.path.basename(p)):
                add("S1", "critical", p, 0, "env file is committed to git (keys inside are exposed to anyone with the repo)")
        tracked_set = set(tracked)
        for p in git_history_env(root):
            if p not in tracked_set:
                add("S1", "high", p, 0, "env file was committed in git history (deleted now, keys still in history: rotate them)")
    if project["has_package_json"] and not project["has_lockfile"]:
        add("S13", "info", "package.json", 0, "no lockfile: installs are not reproducible")

    big_files = []
    totals = {"C1": 0, "C3": 0}
    hints, file_lines = {}, {}
    n_files = n_lines_total = 0
    has_python = False

    for path in iter_files(root, ignored_dirs, ignored_files):
        rel = os.path.relpath(path, root)
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        text = read(path)
        if text is None or is_minified(text):
            continue
        is_env = is_env_file(name)
        is_example_env = name.lower().startswith(".env") and not is_env
        is_code = ext in CODE_EXT
        is_doc = ext in (".md", ".txt")
        is_data = ext == ".json"  # manifests and fixtures name env vars without bundling them
        has_python = has_python or ext == ".py"
        client = is_code and is_client_file(rel, text, project)
        file_lines[rel.replace(os.sep, "/")] = text.count("\n") + 1
        if is_code or ext in (".sql", ".rules") or name in RULE_FILES:
            n_files += 1
            n_lines_total += file_lines[rel.replace(os.sep, "/")]
        file_hints = plan_hints(rel, name, ext, text, is_code, client)
        if file_hints:
            hints[rel.replace(os.sep, "/")] = file_hints

        # S1 secrets
        if not is_example_env:
            for label, rx, sev in SECRET_RX:
                for m in rx.finditer(text):
                    val = m.group(0)
                    if PLACEHOLDER_RX.search(val):
                        continue
                    s = sev
                    if is_doc and s == "critical":
                        s = "high"
                    if is_env and tracked is not None and rel.replace(os.sep, "/") not in tracked:
                        continue  # local untracked .env is the right place for secrets
                    if is_env and tracked is None:
                        s = "info"  # no git: a local .env is fine as long as it is never shared
                    note = f"{label}: {mask(val)}"
                    if label == "Google API key":
                        note += " (often a public Firebase/Maps key: check it is restricted in Google Cloud)"
                    add("S1", s, rel, line_of(text, m.start()), note)
            for m in JWT_RX.finditer(text):
                if jwt_role(m.group(0)) == "service_role":
                    if is_env and tracked is not None and rel.replace(os.sep, "/") not in tracked:
                        continue
                    add("S1", "info" if is_env and tracked is None else "critical", rel, line_of(text, m.start()), f"Supabase service_role key hard-coded: {mask(m.group(0))}")

        if is_code:
            for m in FALLBACK_SECRET_RX.finditer(text):
                add("S1", "high", rel, line_of(text, m.start()), "secret has a hard-coded fallback value: if the env var is missing, this public value is used")

        # S2 public-prefixed secret env names
        for m in PUBLIC_PREFIX_RX.finditer(text):
            var = m.group(0)
            if "PUBLISHABLE" in var or "ANON" in var:
                continue
            add("S2", "info" if is_doc or is_data else "critical", rel, line_of(text, m.start()), f"{var} is bundled into browser code (public prefix on a secret)")

        # S2 secret clients in browser code
        if client:
            for rx, label in CLIENT_SECRET_USE:
                for m in rx.finditer(text):
                    add("S2", "critical" if label != "Stripe secret client" or "sk_" in text else "high",
                        rel, line_of(text, m.start()), f"{label} in browser code")
                    break

        # S3 database rules
        low = rel.replace("\\", "/").lower()
        if ext == ".sql":
            for m in re.finditer(r"(?is)create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?\"?(\w+)\"?", text):
                table = m.group(1)
                if not re.search(rf"(?is)alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?(?:public\.)?\"?{re.escape(table)}\"?\s+enable\s+row\s+level\s+security", text):
                    add("S3", "high", rel, line_of(text, m.start()), f"table '{table}' created without 'enable row level security' in this file (check other migrations)")
            for m in re.finditer(r"(?is)create\s+policy\s+(.{0,120}?)\s+on\s+([\w.\"]+)(.{0,300}?);", text):
                body = m.group(3).lower()
                if re.search(r"for\s+insert", body) and re.search(r"with\s+check\s*\(\s*true\s*\)", body):
                    add("S3", "info", rel, line_of(text, m.start()), f"policy on {m.group(2)} lets anyone add rows (true): OK for a contact form, add a rate limit")
                elif re.search(r"for\s+(update|delete|all)", body) and re.search(r"(using|with\s+check)\s*\(\s*true\s*\)", body):
                    add("S3", "critical", rel, line_of(text, m.start()), f"policy on {m.group(2)} allows writes for everyone (true)")
                elif re.search(r"for\s+select", body) and re.search(r"to\s+authenticated", body) and re.search(r"using\s*\(\s*true\s*\)", body):
                    add("S3", "medium", rel, line_of(text, m.start()), f"policy on {m.group(2)} lets every logged-in user read every row: check this data is not private")
                elif re.search(r"for\s+select", body) and re.search(r"using\s*\(\s*true\s*\)", body):
                    add("S3", "info", rel, line_of(text, m.start()), f"policy on {m.group(2)} lets everyone read: fine only for public data")
            for m in re.finditer(r"(?i)disable\s+row\s+level\s+security", text):
                add("S3", "critical", rel, line_of(text, m.start()), "row level security is disabled")
        if name in ("firestore.rules", "storage.rules", "database.rules.json") or ext == ".rules":
            for m in re.finditer(r"allow\s+[\w, ]+:\s*if\s+true|\"\.(?:read|write)\"\s*:\s*true|request\.time\s*<\s*timestamp", text):
                add("S3", "critical", rel, line_of(text, m.start()), "Firebase rule open to everyone (or test mode)")

        if not is_code:
            if is_doc or ext in (".json",):
                if TEMPLATE_RX.search(text) and name.lower().startswith("readme"):
                    add("C8", "info", rel, 1, "README still has template text")
            continue

        # Routes: auth, rate limit, webhooks
        is_test = bool(TEST_FILE_RX.search(low))
        if is_server_route(rel, text) and not is_test:
            auth_endpoint = bool(AUTH_ENDPOINT_RX.search(low) or AUTH_ROUTE_STRING_RX.search(text))
            writes = re.search(r"\.(?:insert|update|upsert|delete|create|createMany|updateMany|deleteMany)\s*\(|\bPOST\b|\bPUT\b|\bDELETE\b|\bPATCH\b", text)
            if "webhook" in low or "webhook" in text[:2000].lower():
                if not WEBHOOK_VERIFY_RX.search(text):
                    add("S7", "critical", rel, 1, "webhook handler with no signature verification found")
            elif writes and not auth_endpoint and not AUTH_HINT_RX.search(text):
                add("S4", "high", rel, 1, "server route/action changes data, no login check found in this file (check middleware)")
            if (AI_USE_RX.search(text) or EMAIL_USE_RX.search(text) or auth_endpoint) and not RATELIMIT_HINT_RX.search(text):
                add("S8", "medium", rel, 1, "AI / email / auth endpoint with no rate limit found in this file")
        if DEBUG_ROUTE_RX.search(low) and (is_server_route(rel, text) or "/pages/" in low or "/app/" in low):
            add("S12", "medium", rel, 1, "debug/seed/test route: delete or protect before launch")
        for ln in sorted({line_of(text, m.start()) for m in TEST_CRED_RX.finditer(text)}):
            add("S12", "info" if is_test else "medium", rel, ln,
                "test credentials in a test file (fine if never used in production)" if is_test else "hard-coded test credentials")
        if not is_test and not client:
            scan_server_code(rel, text, add)

        # S9 sinks
        for rx, label in DANGEROUS_SINKS:
            for m in rx.finditer(text):
                if label == "dangerouslySetInnerHTML" and re.match(r"\s*=\s*\{\{\s*__html\s*:\s*JSON\.stringify\(", text[m.end():m.end() + 80]):
                    add("S9", "info", rel, line_of(text, m.start()), "dangerouslySetInnerHTML with JSON.stringify (JSON-LD): fine for your own data")
                    continue
                if label == ".innerHTML =":
                    rhs = text[m.end():text.find("\n", m.end()) if "\n" in text[m.end():] else len(text)].strip()
                    if rhs[:1] in ("'", '"') or (rhs[:1] == "`" and "${" not in rhs) or rhs.startswith(("''", '""')):
                        continue
                add("S9", "medium", rel, line_of(text, m.start()), f"{label}: check if user/AI text can reach it")

        # S10 storage
        for m in re.finditer(r"createBucket\([^)]*public\s*:\s*true|getPublicUrl\(", text):
            add("S10", "info", rel, line_of(text, m.start()), "public storage URL: fine for public files only")

        # S14 CORS
        cors_hit = None
        for rx, label in CORS_RX:
            m = rx.search(text)
            if m:
                cors_hit = (m, label)
                break
        if cors_hit:
            sev = "high" if CREDENTIALS_RX.search(text) else "info"
            if "reflects" in cors_hit[1] and re.search(r"(?i)allow(?:ed)?_?(?:list|origins)|whitelist|\.has\(\s*origin\s*\)|\.includes\(\s*origin\s*\)", text):
                sev = "info"  # origin is checked against an allowlist first
            add("S14", sev, rel, line_of(text, cors_hit[0].start()), cors_hit[1] + (" with credentials" if sev == "high" else ""))

        # Cleanup
        logs = list(LOG_RX.finditer(text))
        if logs:
            totals["C1"] += len(logs)
            add("C1", "cleanup", rel, line_of(text, logs[0].start()), f"{len(logs)} console.log/debugger")
        todos = list(TODO_RX.finditer(text)) + list(EMPTY_HANDLER_RX.finditer(text))
        if todos:
            totals["C3"] += len(todos)
            add("C3", "cleanup", rel, line_of(text, todos[0].start()), f"{len(todos)} TODO/FIXME or empty handler")
        fakes = list(FAKE_DATA_RX.finditer(text))
        if fakes:
            add("C2", "cleanup", rel, line_of(text, fakes[0].start()), f"{len(fakes)} fake/placeholder data: e.g. '{fakes[0].group(0)[:30]}'")
        if TEMPLATE_RX.search(text):
            m = TEMPLATE_RX.search(text)
            add("C8", "info", rel, line_of(text, m.start()), "template text left in the app")
        n_lines = text.count("\n") + 1
        if n_lines > BIG_FILE_LINES:
            big_files.append((n_lines, rel))

    for n_lines, rel in sorted(big_files, reverse=True):
        add("C6", "cleanup", rel, 0, f"{n_lines} lines")

    for f in findings:
        f["file"] = f["file"].replace(os.sep, "/")
    project["size"] = {"files": n_files, "lines": n_lines_total, "class": size_class(n_files, n_lines_total)}
    if has_python and "Python" not in project["stack"]:
        project["stack"] = project["stack"] + ["Python"]
    project["skipped_ignored"] = reportable_ignored(ignored_dirs)
    project["hints"] = hints
    project["file_lines"] = file_lines
    return project, findings, totals


ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡", "cleanup": "⚪", "info": "💡"}
NOT_COVERED = ("Regex covers only simple forms of S5, S6, S7 (premium unlocked in the browser), S11 and "
               "per-column Supabase policies: read the plan. S13: run `npm audit --omit=dev`.")
CLEANUP_UNITS = {"C1": "console.log/debugger", "C3": "TODO/FIXME or empty handlers"}


def header_lines(project, findings):
    size = project["size"]
    counts = {k: 0 for k in SEVERITY_ORDER}
    for f in findings:
        counts[f["severity"]] += 1
    head = (f"Lilith quick scan · {', '.join(project['stack']) or 'unknown stack'} · "
            f"{size['files']} files, {size['lines']:,} lines ({size['class']})")
    leads = "Leads (hints, confirm by reading): " + " ".join(f"{ICONS[k]}{v}" for k, v in counts.items() if v)
    return [head, leads] + skipped_lines(project.get("skipped_ignored", []))


def skipped_lines(skipped: List[str]) -> List[str]:
    if not skipped:
        return []
    more = f" +{len(skipped) - SKIPPED_SHOWN} more" if len(skipped) > SKIPPED_SHOWN else ""
    return [f"Skipped (gitignored): {' '.join(skipped[:SKIPPED_SHOWN])}{more}. Scan one separately if it gets deployed."]


def plan_lines(entries, left_out):
    if not entries:
        return []
    out = [f"Read plan ({len(entries)} files, most suspicious first" + (f"; {left_out} more left out" if left_out else "") + "):"]
    for e in entries:
        span = f":{e['lines'][0]}-{e['lines'][1]}" if e["lines"] else ""
        out.append(f"  {e['file']}{span}  {' '.join(e['checks'])}")
    return out


def cleanup_lines(findings):
    out = []
    by_check = {}
    for f in findings:
        if f["check"].startswith("C"):
            by_check.setdefault(f["check"], []).append(f)
    for check in sorted(by_check, key=lambda c: int(c[1:])):
        items = by_check[check]
        if check in CLEANUP_UNITS:
            n = sum(int(re.match(r"\d+", i["note"]).group(0)) for i in items)
            out.append(f"⚪ {check} {n} {CLEANUP_UNITS[check]} in {len(items)} files")
        elif check == "C6":
            names = ", ".join(f"{i['file']} ({i['note'].split()[0]})" for i in items[:3])
            out.append(f"⚪ C6 {len(items)} files over {BIG_FILE_LINES} lines: {names}" + (" ..." if len(items) > 3 else ""))
        else:
            names = ", ".join(i["file"] for i in items[:3]) + (" ..." if len(items) > 3 else "")
            out.append(f"{ICONS[items[0]['severity']]} {check} {CHECK_TITLES.get(check, '')}: {len(items)} files ({names})")
    return out


def summarize_brief(project, findings, plan, left_out, per_check=4):
    out = header_lines(project, findings)
    security = sorted((f for f in findings if f["check"].startswith("S")),
                      key=lambda f: (SEVERITY_ORDER[f["severity"]], int(f["check"][1:]), f["file"]))
    shown = {}
    hidden = {}
    for f in security:
        if shown.get(f["check"], 0) >= per_check:
            hidden[f["check"]] = hidden.get(f["check"], 0) + 1
            continue
        shown[f["check"]] = shown.get(f["check"], 0) + 1
        loc = f["file"] + (f":{f['line']}" if f["line"] else "")
        out.append(f"{ICONS[f['severity']]} {f['check']} {loc}  {f['note']}")
    if hidden:
        out.append("  more: " + ", ".join(f"{n} {c}" for c, n in sorted(hidden.items())) + " (--full lists all)")
    out += cleanup_lines(findings)
    if not findings:
        out.append("No leads. Still read the plan: most real holes need reading, not regex.")
    out += plan_lines(plan, left_out)
    out.append(NOT_COVERED)
    return "\n".join(out)


def summarize(project, findings, max_examples):
    out = []
    out.append("Lilith quick scan")
    out.append("Stack: " + (", ".join(project["stack"]) or "unknown"))
    size = project["size"]
    out.append(f"Size: {size['files']} files, {size['lines']:,} lines ({size['class']})")
    out += skipped_lines(project.get("skipped_ignored", []))
    out.append("Every item below is a LEAD. Confirm by reading the code before reporting it.\n")
    by_check = {}
    for f in findings:
        by_check.setdefault(f["check"], []).append(f)
    def check_key(item):
        check, items = item
        worst = min(SEVERITY_ORDER[i["severity"]] for i in items)
        return (worst, check[0] != "S", int(re.sub(r"\D", "", check) or 0))
    icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "cleanup": "⚪", "info": "💡"}
    counts = {k: 0 for k in SEVERITY_ORDER}
    for f in findings:
        counts[f["severity"]] += 1
    out.append("Leads: " + "  ".join(f"{icons[k]} {k} {v}" for k, v in counts.items() if v))
    out.append("")
    for check, items in sorted(by_check.items(), key=check_key):
        items.sort(key=lambda i: SEVERITY_ORDER[i["severity"]])
        worst = items[0]["severity"]
        out.append(f"{icons[worst]} {check} {CHECK_TITLES.get(check, '')} ({len(items)})")
        for i in items[:max_examples]:
            loc = i["file"] + (f":{i['line']}" if i["line"] else "")
            out.append(f"   {icons[i['severity']]} {loc}  {i['note']}")
        if len(items) > max_examples:
            out.append(f"   ... and {len(items) - max_examples} more")
    if not findings:
        out.append("No leads found. Still read the code for S3-S7: most real holes need reading, not regex.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Lilith quick scan")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--brief", action="store_true", help="compact output (default)")
    mode.add_argument("--full", action="store_true", help="every lead, grouped by check")
    ap.add_argument("--max-examples", type=int, default=6, help="leads per check with --full")
    ap.add_argument("--plan-limit", type=int, default=PLAN_LIMIT, help=f"files in the read plan (default {PLAN_LIMIT})")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        print(f"Not a folder: {args.root}", file=sys.stderr)
        sys.exit(2)
    project, findings, totals = scan(args.root, args.max_examples)
    plan, left_out = read_plan(findings, project["hints"], project["file_lines"], args.plan_limit)
    if args.json:
        print(json.dumps({"stack": project["stack"], "size": project["size"], "findings": findings, "totals": totals,
                          "read_plan": plan, "read_plan_left_out": left_out,
                          "skipped_ignored": project["skipped_ignored"]}, indent=2, ensure_ascii=False))
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.full:
        text = summarize(project, findings, args.max_examples)
        text += "\n\n" + "\n".join(plan_lines(plan, left_out) + [NOT_COVERED])
    else:
        text = summarize_brief(project, findings, plan, left_out)
    print(text)


if __name__ == "__main__":
    main()
