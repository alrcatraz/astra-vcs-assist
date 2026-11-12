#!/usr/bin/env python3
r"""Measure a remote's trust level (trust-level-verification.md section 2).

Scans tracked files for the values the L0-L3 ladder acts on and prints
file:line hits grouped by category, plus any INFRA files. Findings go to
stdout; "total leaks: 0" means the content measured is clean for the level
tested. Run from anywhere inside the repository:

    python3 references/scan-tracked-values.py

Write patterns here, not in a shell one-liner: regex alternation (| and \d)
is quoted differently by sh, bash, and python, so a shell pipeline reports
silently wrong counts.
"""
import os
import re
import subprocess
import sys

PATTERNS = {
    # Neutral placeholders. Each value is an instance fact, so this file ships with the
    # pattern *classes* only: export the SCAN_* variables (or pass them in the environment)
    # to make the scan specific to one fleet. An unset pattern matches nothing.
    "forge": os.environ.get("SCAN_FORGE_HOST", r"(?!)"),
    "path": os.environ.get("SCAN_HOME_PATH", r"(?!)"),
    "ip": r"\b192\.168\.\d+\.\d+\b|\b10\.\d+\.\d+\.\d+\b",
    "personal": os.environ.get("SCAN_PERSONAL_VERSION", r"(?!)"),
    "machine": os.environ.get("SCAN_MACHINE_NAMES", r"(?!)"),
}
INFRA_SEGMENTS = ("workflows/", ".gitea/", ".github/", "Dockerfile", "flake.nix")
RX = re.compile("|".join("(?P<%s>%s)" % (k, v) for k, v in PATTERNS.items()))


def main():
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True).stdout.strip()
    os.chdir(top)
    files = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()
    total = 0
    for path in files:
        if not os.path.exists(path):
            continue
        if any(seg in path for seg in INFRA_SEGMENTS):
            print("  INFRA    %s" % path)
            total += 1
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in RX.finditer(line):
                print("  %-8s %s:%d  %s" % (m.group(0), path, lineno, line.strip()[:90]))
                total += 1
    print("  total leaks: %d" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
