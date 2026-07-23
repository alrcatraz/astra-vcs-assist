---
name: astra-vcs-assist-git-release
description: "End-of-phase commit preparation — interactive rebase for squash, split, reword, and reorder; semantic version tagging; changelog generation; and pre-release verification."
version: 1.0.0
author: alrcatraz
platforms: [linux]
---

# astra-vcs-assist-git-release — Commit Cleanup & Release Management

## Trigger Conditions

Load this sub-skill when:

- Preparing to merge a feature branch into main (commit cleanup)
- Squashing WIP or fixup commits into clean history
- Splitting a large commit into smaller logical pieces
- Rewording commit messages for clarity
- Tagging a new release version
- Writing or generating a changelog
- Planning the commit structure before a release
- Reviewing the history before force-pushing a cleaned-up branch

## Overview

Development produces raw history. Release turns that into a story. This sub-skill covers the transformation:

```text
Raw commits  →  Interactive rebase  →  Clean commits  →  Tag  →  Ship
                     │                       │
                squash / split /         SemVer tag +
                reword / reorder         changelog
```

## 1. Review the State of Play

Before any cleanup, understand what you're working with:

```bash
# View commits on your branch relative to main
git log --oneline --graph main..HEAD

# View commits with full messages
git log --format="%h %s%n%b---" main..HEAD

# View commits with their diffstat
git diff --stat main..HEAD

# Count commits
git rev-list --count main..HEAD

# Check for WIP or fixup commits
git log --oneline main..HEAD | grep -E "^(wip|fixup|squash|WIP)"
```

## 2. Interactive Rebase (the Core Tool)

Interactive rebase is the Swiss Army knife of commit cleanup.

```bash
# Rebase the last N commits
git rebase -i HEAD~N

# Rebase from the branch point off main
git rebase -i main
```

This opens an editor with a list of commits:

```
pick a1b2c3d feat: add user login endpoint
pick e4f5g6h wip: rate limiter unfinished
pick i7j8k9l fix: handle null token
pick m0n1o2p docs: add api examples

# Commands:
# p, pick  = use commit
# r, reword = use commit but edit the message
# s, squash = use commit but meld into previous
# f, fixup  = like squash, but discard this commit's message
# d, drop   = remove commit
# e, edit   = stop at this commit for amending / splitting
# x, exec   = run a shell command
# b, break  = stop here (for pre-testing before continuing)
```

### Key operations in interactive rebase

### A. Squashing WIP commits

WIP and fixup commits should never appear in the final merge. Squash them into their parent:

```text
Before:
pick a1b2c3d feat: add user login endpoint
pick e4f5g6h wip: rate limiter unfinished       ← squash into above
pick m0n1o2p docs: api examples

Change to:
pick a1b2c3d feat: add user login endpoint
fixup e4f5g6h wip: rate limiter unfinished      ← f = discard message, merge into above
pick m0n1o2p docs: api examples
```

### B. Rewording a commit message

```text
pick a1b2c3d feat: add user login endpoint
reword e4f5g6h fix: handle null token           ← r = stop and let you edit message
```

### C. Dropping a mistaken commit

```text
pick a1b2c3d feat: add user login endpoint
drop m0n1o2p feat: accidentally committed debug code  ← d = remove entirely
```

### D. Reordering commits

Simply reorder the lines in the editor:

```text
Before:
pick e4f5g6h fix: handle null token
pick a1b2c3d feat: add user login endpoint

Change to:
pick a1b2c3d feat: add user login endpoint    ← moved up
pick e4f5g6h fix: handle null token           ← moved down
```

## 3. Splitting a Commit

When a single commit contains two unrelated changes, split it.

### Method A: During interactive rebase

```bash
# In rebase -i, mark the commit as "edit":
edit a1b2c3d feat: add user auth + refactor config loading

# Git stops at this commit. Now:
git reset HEAD~                   # unstage everything, keep files as-is
git add -p src/auth.py            # stage only auth changes
git commit -m "feat: add user authentication"
git add -p src/config.py          # stage config changes
git commit -m "refactor: extract config loading"
git rebase --continue
```

### Method B: Without rebase (for the most recent commit)

```bash
# Soft reset the last commit
git reset HEAD~

# Now re-stage in logical groups
git add -p src/feature-one/
git commit -m "feat: feature one"
git add src/feature-two/
git commit -m "feat: feature two"
```

## 4. Commit Message Writing (Final Form)

After cleanup, ensure every commit message follows Conventional Commits:

```bash
type(scope): short description (50 chars max, lowercase, imperative)

Longer explanation if needed. Wrap at 72 characters.
Explain WHY, not just WHAT.
```

### Commit types

| Type | When | Example |
|:-----|:------|:--------|
| `feat` | New feature | `feat: add user login endpoint` |
| `fix` | Bug fix | `fix: handle null token in auth middleware` |
| `refactor` | Code restructuring | `refactor: extract db pool from auth module` |
| `docs` | Documentation | `docs: add api endpoint reference` |
| `test` | Tests | `test: add unit tests for auth middleware` |
| `chore` | Maintenance | `chore: update dependency versions` |
| `ci` | CI/CD | `ci: add python lint workflow` |
| `perf` | Performance | `perf: cache database connection pool` |

### Body — always explain WHY

```bash
# Good — explains the motivation
feat: cache database connection pool

Creating a new connection per request was causing 400ms latency
on high-traffic endpoints. Pool reuses up to 10 connections.

# Bad — restates what the code already says
feat: cache database connection pool

Added connection pool to database module.
```

### Writing workflow

1. **Draft the type+desc first** — give to user for approval
2. **Write the body** — explain the "why"
3. **User confirms** before `git commit` executes

## 5. Semantic Versioning (SemVer)

### Version format

```
vMAJOR.MINOR.PATCH
  ↑       ↑      ↑
  │       │      └── Bug fixes (backward-compatible)
  │       └───────── New features (backward-compatible)
  └───────────────── Breaking changes
```

### When to bump

| Change type | Bump | Example |
|:------------|:-----|:--------|
| Bug fix, no API change | PATCH | `v1.0.0` → `v1.0.1` |
| New feature, backward-compatible | MINOR | `v1.0.0` → `v1.1.0` |
| Breaking API change | MAJOR | `v1.0.0` → `v2.0.0` |
| Documentation only | PATCH (or none) | `v1.0.0` → `v1.0.1` |
| Initial release | v0.1.0 or v1.0.0 | `v0.1.0` (pre-stable) |
| Pre-release | Append `-alpha.1`, `-beta.2` | `v2.0.0-beta.1` |

### Tagging

```bash
# Tag the current commit
git tag v1.2.0

# Tag with a message
git tag -a v1.2.0 -m "Release v1.2.0 — add rate limiting"

# Tag a specific commit
git tag v1.1.0 a1b2c3d

# List tags
git tag -l 'v*'

# Push tags to remote
git push origin v1.2.0          # single tag
git push origin --tags           # all tags (be careful — pushes everything)

# Delete a tag locally
git tag -d v1.2.0

# Delete a tag on remote
git push origin :refs/tags/v1.2.0

# Move a tag to a new commit
git tag -d v1.0.0
git tag v1.0.0 <new-sha>
git push --force origin v1.0.0
```

## 6. Changelog

### Manual changelog (recommended for small projects)

```markdown
## [v1.2.0] — 2026-07-01

### Added
- Rate limiting on API endpoints (#42)
- User profile caching (#38)

### Fixed
- Null pointer in auth middleware when token missing (#40)
- Race condition in session handler (#36)

### Changed
- Upgraded dependencies to latest versions
```

### Auto-generated (from Conventional Commits)

```bash
# Simple changelog from commit messages
git log --oneline --format="%s" v1.1.0..HEAD | \
  grep -E '^(feat|fix|refactor|docs):' | \
  sed -E 's/^(feat):/\n### Added\n-/' | \
  sed -E 's/^(fix):/\n### Fixed\n-/' | \
  sed -E 's/^(refactor):/\n### Changed\n-/'
```

### Keep a Changelog Format

Follow [keepachangelog.com](https://keepachangelog.com) conventions:

```markdown
# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com).

## [v1.2.0] — 2026-07-23

### Added
- New feature description (#42)

### Changed
- Behaviour change in existing feature (#38)

### Deprecated
- Feature that will be removed in next major version

### Removed
- Feature removed in this release

### Fixed
- Bug fix description (#40)

### Security
- Vulnerability fix

[Unreleased]: https://github.com/owner/repo/compare/v1.2.0...HEAD
[v1.2.0]: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
```

Keep the `[Unreleased]` link at the bottom so the section is always
ready for the next release's additions.

---

## PR Preparation Checklist

Before opening or merging a pull request, verify these items:

1. **Stop after coding** — once development work is functionally complete,
   STOP. Do NOT commit or PR without user confirmation.
2. **User confirmation** — present the work to the user. Let them confirm
   everything is correct.
3. **User identity** — confirm whose name/email should be on the commits.
   Set per-repo git identity.
4. **Commit only after approval** — organise commits only after explicit
   user go-ahead.
5. **Submit PR only after second approval** — wait for a second explicit
   approval before opening a PR. No self-authorised submissions.
6. **Review commit history** — squash intermediate corrections, split
   logical concerns.
7. **Update README** — must reflect the PR's changes before opening.
8. **Reset local main if needed:** `git checkout main && git reset --hard <remote>/main`
9. **No "Phase X" labels** in commit messages.
10. **Private data audit** — check for device names, IPs, passwords in
    committed files.
11. **Run graphlint** — `graphlint query --warn-types unused_import,dead_code`
    to catch dead code and unused imports before declaring done.

---

## 7. Pre-Release Verification Checklist

Before tagging and pushing a release:

```bash
# 1. Confirm commit history is clean
git log --oneline main..HEAD
#   → No WIP, no fixup, no "temp" commits

# 2. Verify all commit messages follow Conventional Commits
git log --format="%s" main..HEAD | grep -vE '^(feat|fix|refactor|docs|test|chore|ci|perf)\('
#   → Should return nothing

# 3. Check GPG signatures
git log --show-signature main..HEAD | grep -c "Good signature"

# 4. Confirm the diff looks right
git diff main..HEAD --stat

# 5. Check the next version bump
#    (see SemVer table above — is it PATCH, MINOR, or MAJOR?)

# 6. Write or update the changelog
#
# 7. Tag (only for own repos — forks skip this)
#    Confirm with user: "Ready to tag vX.Y.Z?"
#    git tag v1.2.0
```

### If something is wrong, don't push yet

```bash
# Go back to interactive rebase to fix
git rebase -i main
# Or reset and restructure
git reset --soft main
git add -p
git commit -m "feat: single clean commit"
```

## 8. Merge to Main vs Open a Pull Request

After commits are cleaned up, the final step depends on
whether you own the target repository:

### Own repo → merge to main

After cleanup, **ask the user** whether to tag before pushing:

```bash
# Ensure you're on the feature branch with clean commits
git checkout feature-branch

# Switch to main and merge
git checkout main
git merge feature-branch

# Or squash-merge (single commit on main)
git merge --squash feature-branch
git commit -m "feat: add user authentication (#42)"

# Tag — only if user confirms ("Ready to tag vX.Y.Z?")
git tag v1.2.0

# Push
git push origin main --tags

# Delete the feature branch (local and remote)
git branch -d feature-branch
git push origin :feature-branch
```

### Fork → pull request to upstream

No tagging — forks can't push tags to the upstream repo. Submit PR instead:

```bash
# Push the cleaned-up feature branch to your fork
git push -u origin feature-branch

# Create a pull request via GitHub API (no gh CLI)
BRANCH=$(git branch --show-current)
OWNER_REPO=$(git remote get-url origin | \
  sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: short description\",
    \"body\": \"## Summary\\n\\nWhat this PR does and why.\\n\\nCloses #issue\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"

# Or if the PR targets an upstream repo (not your fork):
#   head = \"$OWNER:$BRANCH\"
#   base = \"main\"
#   (the PR is opened against the upstream repo)
```

### Decision guide

| Scenario | Action | Tag? |
|:---------|:-------|:----:|
| Your own project, single maintainer | Merge to main, delete feature branch | ✅ Ask user |
| Your own project, multiple contributors | Merge via PR for audit trail | ✅ Ask user |
| Fork of someone else's project | Push feature branch → open PR to upstream | ❌ Skip |
| Experimental / throwaway branch | Delete without merging | ❌ Skip |

After merging or submitting the PR, proceed to `astra-vcs-assist-git-sync`
if you need to push to multiple remotes or transfer commits.

## Pitfalls

1. **Never rebase pushed commits** unless you're prepared to force-push. Rebasing changes commit SHAs. If others have the old history, they'll need to rebase too.

2. **Squashing loses authorship info.** If multiple people worked on the squashed commits, consider whether you want to preserve individual authorship (use separate commits) or collapse it (squash).

3. **`git push --tags` pushes ALL tags.** If you have local tags you don't want on the remote (e.g. test tags), push individual tags instead: `git push origin v1.2.0`.

4. **Moving tags confuses consumers.** Once a tag is pushed, treat it as immutable. If you must move it, notify everyone who might have pulled the old tag.

5. **Interactive rebase on the wrong branch.** Always verify: `git branch` (should show your feature/topic branch, not main). Rebasing main is almost never what you want.

6. **`git commit --amend` on a pushed commit** creates a divergent history. Use `git commit --fixup` + `git rebase -i --autosquash` instead, then force-push with `--force-with-lease`.

7. **Commit message in wrong case.** Conventional Commits requires lowercase: `feat:` not `Feat:` and `Fix:` — this applies to the type prefix only, not the rest of the message.
