---
name: astra-vcs-assist-git-review
description: "Pre-commit code review pipeline — diff collection, static security scan, baseline comparison, self-review checklist, independent agent review, and auto-fix loop."
version: 1.4.0
author: alrcatraz
triggers:
  - "提交前审查"
  - "code review"
  - "diff 检查"
  - "敏感信息扫描"
  - "pre-commit review"
  - "审一下改动"
platforms: [linux]
metadata:
  hermes:
    tags: [git, code-review, pre-commit, security-scan, diff]

---

# astra-vcs-assist-git-review — Code Review Pipeline

## Trigger Conditions

Load this sub-skill when:

- About to commit or push — need pre-submit verification
- User says "review", "verify", "check before commit", "is it ready"
- After completing a task with 2+ file edits in a git repo
- Setting up quality gates for a new project

**This skill vs astra-vcs-assist-github:** This skill verifies YOUR changes before committing. `astra-vcs-assist-github` covers GitHub-level code review (reviewing OTHER people's PRs) plus auth, issues, releases, and CI on GitHub.

**This skill vs coding-workflow:** `coding-workflow` covers the general methodology (TDD, simplify, conventions). This skill is the executable pipeline: get the diff, scan for security issues, run baseline tests, dispatch an independent reviewer, evaluate, fix, commit.

## Overview

```
Get diff  →  Static scan  →  Baseline tests  →  Self-review  →
    │                                                  │
    └── Run independent reviewer ───────────────────────┘
                     │
              Evaluate (pass/fail)
                     │
            ┌────────┴────────┐
            ▼                 ▼
          Commit          Auto-fix loop
                            (max 2 cycles)
```

**Core principle:** No agent should verify its own work. Fresh context finds what you miss.

## Step 1 — Get the Diff

Collect the changes to review. Source depends on context:

```bash
# Default: staged changes (about to commit)
git diff --cached

# If empty, working tree
git diff

# Last commit (after a single focused commit)
git diff HEAD~1 HEAD

# Specific branch vs main
git diff main...HEAD
```

If all diffs are empty, tell the user — nothing to verify.

If the diff exceeds 15,000 characters, split by file to avoid token limits.

## Step 2 — Static Security Scan

Scan added lines for common security issues. Any match is a concern.

| Pattern | What to check | Example |
|:--------|:--------------|:--------|
| Hardcoded secrets | `api_key`, `secret`, `password`, `token` = `'...'` | `grep -E "(api_key\|secret\|password)\s*=\s*['\"][^'\"]{6,}['\"]"` |
| Shell injection | `os.system()`, `subprocess.*shell=True` | `grep -E "os\.system\(|subprocess.*shell=True"` |
| Dangerous eval | `eval()`, `exec()` | `grep -E "\beval\(|\bexec\("` |
| Unsafe deserialisation | `pickle.loads()` | `grep -E "pickle\.loads?\("` |
| SQL injection | String formatting in queries | `grep -E "execute\(f\"\|\.format\(.*SELECT"` |

## Step 3 — Baseline Tests and Linting

Run tests and linters BEFORE your changes (stash, run, pop) to establish a baseline. Only NEW failures block the commit.

### Test Frameworks (auto-detect by project files)

```bash
# Python
python -m pytest --tb=no -q

# Node
npm test -- --passWithNoTests

# Rust
cargo test

# Go
go test ./...
```

### Linting and Type Checking

```bash
# Python
which ruff && ruff check .
which mypy && mypy .

# Node
which npx && npx eslint .
which npx && npx tsc --noEmit

# Rust
cargo clippy -- -D warnings

# Go
go vet ./...
```

## Step 4 — Self-Review Checklist

Quick scan before dispatching the reviewer:

- [ ] No hardcoded secrets, API keys, or credentials
- [ ] Input validation on user-provided data
- [ ] SQL queries use parameterised statements
- [ ] File operations validate paths (no traversal)
- [ ] External calls have error handling (try/catch)
- [ ] No debug print/console.log left behind
- [ ] No commented-out code
- [ ] New code has tests (if test suite exists)

## Step 5 — Independent Reviewer

Spawn a subagent whose sole purpose is to review the changes. The reviewer:

- Gets ONLY the diff and static scan results
- Has NO context of how the changes were made
- Returns a verdict (pass/fail) with structured evidence

**Reviewer instructions:**

```
You are an independent code reviewer. You have no context about how these
changes were made. Review the git diff and return:

1. SECURITY concerns: hardcoded secrets, backdoors, shell injection, SQL
   injection, path traversal, unsafe deserialisation, eval() with user input.

2. LOGIC errors: wrong conditional logic, missing error handling for I/O/
   network/DB, off-by-one, race conditions, code contradicts intent.

3. SUGGESTIONS (non-blocking): missing tests, style, performance, naming.

FAIL-CLOSED: if security_concerns or logic_errors is non-empty, pass=false.
Only pass=true when both lists are empty.

Give file:line evidence for each finding.
```

**Tooling:** Give the reviewer access to `terminal` and `file` tools so they can inspect the codebase around the changed lines.

## Step 6 — Evaluate Results

| All passed → | Any failures → |
|:-------------|:---------------|
| Proceed to commit | Report what failed, then auto-fix |

Combine results from Steps 2, 3, and 5.

## Step 7 — Auto-Fix Loop (Max 2 Cycles)

When the reviewer finds issues, spawn a fix agent:

```
You are a code fix agent. Fix ONLY the specific issues listed below.
Do NOT refactor, rename, or change anything else. Do NOT add features.

Issues to fix:
[security concerns + logic errors from reviewer]

Fix each issue precisely. Describe what you changed and why.
```

**Tooling:** Give the fix agent `terminal` and `file` tools.

After fixing, re-run Steps 1-6 (full verification cycle).

- Passed: proceed to commit
- Failed and attempts < 2: repeat Step 7
- Failed after 2 attempts: escalate to user with remaining issues

## Step 8 — Commit

If verification passed:

```bash
git add -A && git commit -m "[verified] <description>"
```

The `[verified]` prefix marks commits that passed the full review pipeline.

## Integration with Other Skills

- **coding-workflow** — TDD methodology and simplify code principles
- **astra-vcs-assist-git-dev** — pre-push verification; this skill runs before that
- **astra-vcs-assist-git-release** — PR preparation; this skill runs per-commit
- **astra-vcs-assist-github** — GitHub PR review (reviewing others' PRs); this skill reviews your own changes
