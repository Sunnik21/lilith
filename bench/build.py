#!/usr/bin/env python3
"""Builds the benchmark fixture apps into bench/.build/ (gitignored).

Fixture sources in bench/<app>/vulnerable/ contain placeholders like
{{OPENAI_KEY}} instead of secrets. This script swaps in fake keys that are
assembled at runtime, so nothing secret-shaped is ever committed and GitHub
push protection stays quiet. Files named dot.X become .X.

bench/<app>/fixed/ is an overlay: its files replace or add to the vulnerable
version, and paths listed in fixed/DELETE are removed.

Each built app becomes its own git repo with one commit, so checks like
"is .env committed?" behave as in a real project.

Usage:
  python3 bench/build.py            # build all apps, print their paths
  python3 bench/build.py --check    # also verify every manifest snippet sits in its line range
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Tuple

BENCH = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(BENCH, ".build")
APPS = ("lovable-style", "nextjs-saas", "express-api")
VARIANTS = ("vulnerable", "fixed")


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


def _fake(prefix: str, n: int = 40) -> str:
    return prefix + ("A1b2C3d4E5" * 10)[:n]


def fake_values() -> Dict[str, str]:
    """Secret-shaped strings, built from pieces so the source never contains one."""
    header = "eyJ" + _b64({"alg": "HS256", "typ": "JWT"})[3:]
    anon = header + "." + _b64({"iss": "supabase", "ref": "abcdefghijklmnop", "role": "anon"}) + ".f4keS1gnatureF4keS1gnature"
    return {
        "OPENAI_KEY": _fake("sk-" + "proj-", 48),
        "ANON_JWT": anon,
        "STRIPE_PK": _fake("pk_" + "live_", 40),
        "DB_PASSWORD": "Tk" + "9vQ2mLx7Rp",
    }


def _target_name(rel: str) -> str:
    head, base = os.path.split(rel)
    if base.startswith("dot."):
        base = base[3:]
    return os.path.join(head, base)


def _copy_tree(src: str, dst: str, values: Dict[str, str]) -> None:
    for dirpath, _dirs, files in os.walk(src):
        for name in files:
            if name == "DELETE" and dirpath == src:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, src)
            out = os.path.join(dst, _target_name(rel))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for key, value in values.items():
                text = text.replace("{{" + key + "}}", value)
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(text)


def _git_commit(root: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "bench", "GIT_AUTHOR_EMAIL": "bench@localhost",
           "GIT_COMMITTER_NAME": "bench", "GIT_COMMITTER_EMAIL": "bench@localhost"}
    git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-C", root]
    subprocess.run(["git", "init", "-q", root], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "initial commit"], check=True, env=env)


def build_app(app: str, variant: str, out_root: str = DEFAULT_OUT) -> str:
    """Builds one app variant and returns its folder."""
    if app not in APPS or variant not in VARIANTS:
        raise ValueError(f"unknown app/variant: {app}/{variant}")
    dst = os.path.join(out_root, app, variant)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    values = fake_values()
    _copy_tree(os.path.join(BENCH, app, "vulnerable"), dst, values)
    if variant == "fixed":
        overlay = os.path.join(BENCH, app, "fixed")
        _copy_tree(overlay, dst, values)
        delete_list = os.path.join(overlay, "DELETE")
        if os.path.exists(delete_list):
            with open(delete_list) as fh:
                for rel in filter(None, (line.strip() for line in fh)):
                    target = os.path.join(dst, _target_name(rel))
                    if os.path.exists(target):
                        os.remove(target)
    _git_commit(dst)
    return dst


def build_all(out_root: str = DEFAULT_OUT) -> Dict[Tuple[str, str], str]:
    return {(a, v): build_app(a, v, out_root) for a in APPS for v in VARIANTS}


def load_manifest(app: str) -> dict:
    with open(os.path.join(BENCH, app, "expected.json"), encoding="utf-8") as fh:
        return json.load(fh)


def check_manifest(app: str, root: str) -> List[str]:
    """Every bug/decoy snippet must appear inside its stated line range."""
    errors = []
    manifest = load_manifest(app)
    for item in manifest["bugs"] + manifest["decoys"]:
        path = os.path.join(root, item["file"])
        if not os.path.exists(path):
            errors.append(f"{app} {item['id']}: missing file {item['file']}")
            continue
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        start, end = item["lines"]
        window = "\n".join(lines[start - 1:end])
        if item["snippet"] not in window:
            errors.append(f"{app} {item['id']}: snippet not in {item['file']}:{start}-{end}")
    return errors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT, help="output folder (default: bench/.build)")
    ap.add_argument("--check", action="store_true", help="verify manifest line ranges")
    args = ap.parse_args()
    built = build_all(args.out)
    for (app, variant), path in built.items():
        print(f"{app}/{variant}: {path}")
    if args.check:
        errors = [e for app in APPS for e in check_manifest(app, built[(app, "vulnerable")])]
        if errors:
            print("Manifest errors:\n" + "\n".join(errors))
            sys.exit(1)
        print("Manifests OK")


if __name__ == "__main__":
    main()
