#!/usr/bin/env python3
"""Lightweight secret scanner.

Fails if obvious credential patterns are found in tracked files. This is a fast
CI guard, not a substitute for GitHub secret scanning or a dedicated tool.

Usage: ``python scripts/scan_secrets.py``
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*"
            r"['\"][A-Za-z0-9/+_-]{20,}['\"]"
        ),
    ),
]

#: This file itself contains the patterns, so skip it.
ALLOWLIST = {"scripts/scan_secrets.py"}

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def iter_files():
    try:
        listing = subprocess.check_output(["git", "ls-files"], text=True, stderr=subprocess.DEVNULL)
        for line in listing.splitlines():
            if line.strip():
                yield Path(line)
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    for path in Path(".").rglob("*"):
        if path.is_file() and not (SKIP_DIRS & set(path.parts)):
            yield path


def main() -> int:
    findings: list[tuple[str, str, str]] = []
    for path in iter_files():
        normalized = str(path).replace("\\", "/")
        if normalized in ALLOWLIST:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, pattern in PATTERNS:
            for match in pattern.finditer(text):
                findings.append((normalized, name, match.group(0)[:24]))

    if findings:
        print("Potential secrets found:")
        for path, name, snippet in findings:
            print(f"  {path}: {name} ({snippet}...)")
        return 1
    print("No hardcoded secrets detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
