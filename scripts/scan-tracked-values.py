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
    # ADAPT -- neutralised before INFRA is stripped (ladder order)
    "forge": r"<private-forge-host>",
    "path": r"/home/<user>",
    "ip": r"\b192\.168\.\d+\.\d+\b|\b10\.\d+\.\d+\.\d+\b",
    "personal": r"\+alrcatraz",
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
