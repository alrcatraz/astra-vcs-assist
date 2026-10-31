#!/usr/bin/env python3
"""Re-graft integrity audit — run after ANY cherry-pick/rebase onto refactored main.

Auto-merge only shows TEXTUAL conflicts. The damage upstream's refactoring does
to a re-grafted PR is usually silent: an import block that survives while its
CALL SITES were rewritten away (the feature vanishes and nothing conflicts), or a
local `def` that shadows an imported symbol so two divergent implementations
serve different callers.

Usage:
    scripts/graft-integrity-audit.py [BASE] [HEAD]
    # defaults: BASE=upstream/main HEAD=HEAD

Exit code 1 when anything is flagged — use it as a gate before committing a
re-graft, not as advisory output.
"""
import re
import subprocess
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "upstream/main"
HEADREF = sys.argv[2] if len(sys.argv) > 2 else "HEAD"


def git(args):
    return subprocess.run(["git"] + args, capture_output=True, text=True).stdout


def added_lines_by_file(diff_text):
    """Collect only '+' lines per file, in order (unified=0 keeps hunks minimal)."""
    out, cur = {}, None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
            out.setdefault(cur, [])
        elif line.startswith("+++ "):
            cur = None
        elif line.startswith("+") and not line.startswith("+++") and cur:
            out[cur].append(line[1:])
    return out


def imported_names(added_text):
    """(module, name) for every import statement in the ADDED lines.

    Handles `from x import (a, b)` blocks: the added lines of such a block are
    consecutive in the collected '+' stream, so re.S over the joined text works.
    """
    pairs = []
    for m in re.finditer(r"from\s+([\w\.]+)\s+import\s*\(([^)]*)\)", added_text, re.S):
        mod, body = m.group(1), m.group(2)
        for n in re.findall(r"\w+", body):
            pairs.append((mod, n))
    for m in re.finditer(r"from\s+([\w\.]+)\s+import\s+([^\n(#]+)", added_text):
        mod, body = m.group(1), m.group(2)
        if "(" in body:
            continue
        for n in body.split(","):
            n = n.strip()
            if re.fullmatch(r"\w+", n):
                pairs.append((mod, n))
    return pairs


def defined_names(text):
    return set(re.findall(r"^(?:async\s+)?def\s+(\w+)", text, re.M)) | set(
        re.findall(r"^class\s+(\w+)", text, re.M)
    )


def singular_attr_reads(pkg_dirs, plural, singular):
    """Files that READ the singular attribute but never mention the plural one.

    After a change generalises a scalar into a collection, every reader that
    still answers a set-valued question from the scalar is the same defect the
    reviewer already flagged — usually in a file the diff never touches.
    """
    hits = []
    out = git(["grep", "-l", f"['\"]{singular}['\"]", "--", *pkg_dirs])
    for path in out.split():
        text = git(["show", f"HEAD:{path}"]) or git(["grep", "-h", "HEAD", "--", path])
        if plural not in text:
            hits.append(path)
    return hits


diff = git(["diff", f"{BASE}..{HEADREF}", "--unified=0", "--", "."])
if not diff.strip():
    print(f"no diff between {BASE} and {HEADREF} — nothing to audit")
    sys.exit(0)

flags = 0
for path, lines in sorted(added_lines_by_file(diff).items()):
    if not path.endswith(".py") or not lines:
        continue
    full = git(["show", f"{HEADREF}:{path}"])
    if not full.strip():
        continue  # deleted at HEAD
    added_text = "\n".join(lines)
    defs = defined_names(full)
    seen = set()
    for mod, name in imported_names(added_text):
        if (mod, name) in seen:
            continue
        seen.add((mod, name))
        # SHADOW: the file both imports the name and defines it. The local
        # definition wins, so callers importing the symbol THROUGH this file get
        # a different implementation than the source module's own internal
        # callers — two divergent versions of one predicate.
        if name in defs:
            print(f"SHADOW  {path}: imports '{name}' from {mod} AND defines it locally")
            print("        keep the module's version as the single source, delete the")
            print("        local copy, and pin it with an identity-assertion test")
            flags += 1
            continue
        # DEAD IMPORT: an import line contributes exactly one occurrence, so a
        # total count of 1 means the name is never used in the file. After a
        # re-graft that usually means the CALL SITE was lost, not that the
        # import is surplus.
        occ = len(re.findall(rf"\b{re.escape(name)}\b", full))
        if occ <= 1:
            print(f"DEAD    {path}: imports '{name}' from {mod} but never uses it")
            print("        re-anchor the call site (an extracted helper is usually")
            print("        better than the inline duplicate upstream left behind), or")
            print("        state explicitly that this file is a re-export seam")
            flags += 1

print()
if flags:
    print(f"graft-integrity-audit: {flags} flag(s) — resolve before committing the re-graft")
else:
    print("graft-integrity-audit: clean (no dead imports, no shadowed defs)")

# --- STALE CONSUMER: attributes this change turned from scalar to collection ---
# `app.state.bound_hosts = frozenset(hosts)` next to `app.state.bound_host = host`
# means readers of the singular may now be answering set-valued questions.
attrs = set()
for path, lines in added_lines_by_file(diff).items():
    for line in lines:
        m = re.search(r"\.([A-Za-z_]\w{3,})s\s*=", line)
        if m and f".{m.group(1)s}" in "".join(
            git(["show", f"{BASE}:{path}"]) for _ in [0]
        ):
            attrs.add((m.group(1) + "s", m.group(1)))
top = sorted({p.split("/")[0] for p in added_lines_by_file(diff) if p.endswith(".py")})
for plural, singular in sorted(attrs):
    stale = singular_attr_reads(top or ["."], plural, singular)
    if stale:
        print(f"\nSTALE   '{singular}' generalised to '{plural}', but readers never "
              f"consult '{plural}':")
        for p in stale:
            print(f"        {p}")
        print("        audit each: a set-valued decision made from the scalar alone is "
              "the bug,\n        and a fallback chain must end in `or \"\"` (an existing "
              "attribute holding None\n        is not the getattr default). Fix + test "
              "per consumer.")
        flags += len(stale)

sys.exit(1 if flags else 0)
