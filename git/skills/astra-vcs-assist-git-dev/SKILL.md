---
name: astra-vcs-assist-git-dev
description: "Daily Git workflow during active development — branch management, staging strategies, commit discipline, stash, rebase vs merge decisions, and pre-push verification."
version: 1.3.0+alrcatraz.1.0.0.angelia.0.0.0
author: alrcatraz
triggers:
  - "日常 git"
  - "分支管理"
  - "暂存区"
  - "commit message"
  - "写提交信息"
  - "整理改动"
  - "branch workflow"
platforms: [linux]
metadata:
  hermes:
    tags: [git, daily-workflow, branch, staging, commit-hygiene]

---

# astra-vcs-assist-git-dev — Daily Development Workflow

## Trigger Conditions

Load this sub-skill when:

- Starting work on a new feature, fix, or refactor
- Making commits during active development
- Deciding between merge and rebase
- Needing to save work-in-progress (stash) or restore it
- Reviewing your working tree before pushing
- Resolving merge conflicts

## Overview

Daily git work follows a rhythm: **start → work → commit → repeat**. This sub-skill covers the everyday decisions that keep your history clean without over-engineering.

```text
Start work       →  Branch      →  Make changes  →  Review  →  Commit  →  Repeat
    │                                                          │
    └── Stash (if interrupted)     Run tests ──────────────────┘
```

## 1. Branching Strategy

### Collaboration model (standard workflow, all projects)

```text
feature/* ──▶ development ──▶ main (via PR) ──▶ build server pulls main
     ▲             │              │
     └── work      └── PR         └── release (tagged)
```

- **`main`** — production. Only receives merges from `development` via PR.
  The build server (e.g. SUSETLearn00) pulls **main only** — never feature
  branches, never development.
- **`development`** — integration branch. Feature branches merge here via PR.
  This is where the whole team's work meets; keep it green.
- **`feature/*`** — your working branch (`feat/`, `fix/`, `refactor/`, `docs/`).
  Short-lived: cut from `development`, merged back via PR, then deleted.

Hard rules:

1. **Never push directly to `main` or `development`** — all integration goes
   through PRs (Gitea/GitHub).
2. **Never have the build server check out a feature branch** — it builds
   `main` only. If a fix isn't in `main`, the build doesn't see it.
3. **Double-push every remote project**: Gitea (private) + GitHub (public)
   both get the same branches and tags. Push order: Gitea first, then GitHub.
4. If the repo only has `main` (e.g. during a rebuild), recreate
   `development` before starting feature work:
   ```bash
   git checkout -b development main
   git push -u gitea development
   git push -u github development
   ```

### Start a feature branch

```bash
# Always branch from the tip of development
git checkout development
git pull --rebase            # sync integration branch (gitea + github)
git checkout -b feat/add-user-auth
```

If development does not exist locally yet:

```bash
git fetch gitea development
git checkout -b development gitea/development
```

### Create a feature branch

```bash
# Naming: <type>/<short-description>
git checkout -b feat/add-user-auth
git checkout -b fix/login-redirect
git checkout -b refactor/db-layer
git checkout -b docs/api-guide
```

Branch name conventions (mirrors Conventional Commits types):

| Prefix | When | Example |
|:-------|:-----|:--------|
| `feat/` | New feature | `feat/user-auth` |
| `fix/` | Bug fix | `fix/login-null-pointer` |
| `refactor/` | Code restructuring | `refactor/model-layer` |
| `docs/` | Documentation | `docs/api-guide-v2` |
| `chore/` | Maintenance | `chore/update-deps` |
| `ci/` | CI/CD | `ci/gh-actions-python` |

### Working on existing branches

```bash
# Switch to an existing branch
git checkout feat/user-auth

# Create from a non-main base (e.g. another feature branch)
git checkout -b feat/user-auth-permissions feat/user-auth
```

## 2. Daily Status Checks

Before committing, always check what's happened:

```bash
# Quick overview
git status

# See unstaged changes
git diff

# See staged changes
git diff --cached

# See untracked files (new files git doesn't know about)
git status --short

# See log in context of your branch (baseline: development)
git log --oneline development..HEAD
```

## 3. Staging Strategies

### The three staging patterns

| Pattern | Command | When |
|:--------|:--------|:-----|
| **Stage all** | `git add -A` | Small, focused changes where every file belongs together |
| **Stage by file** | `git add src/auth.py src/models/user.py` | Medium changes where some files are unrelated |
| **Stage by hunk** | `git add -p` | Large edits where you want to commit in logical pieces |

### `git add -p` — The most powerful staging tool

`-p` (or `--patch`) shows each change hunk and asks what to do:

```
y — stage this hunk
n — skip this hunk
s — split hunk into smaller pieces
e — manually edit the hunk (advanced, split first when possible)
q — quit (don't stage remaining hunks)
```

**Use case:** You fixed a bug and added a comment in the same file, but they're in different hunks. Stage only the bug fix hunk, leave the comment for a separate commit.

### Split unrelated changes before committing

```bash
# After making changes, check if your work tree has logically separate changes
git diff --stat

# If yes, stage them separately:
git add -p src/component.py    # stage only the feature hunks
git commit -m "feat: ..."

git add -p src/component.py    # stage remaining hunks
git commit -m "refactor: ..."
```

## 4. Commit Discipline During Development

### Rules of thumb

1. **One logical change per commit.** Don't mix a bug fix with a refactor in the same commit.
2. **Commit early, commit often.** Small commits are easier to review, squash later.
3. **Write descriptive messages.** Future you will thank present you.
4. **Different tasks, different commits.** Never merge two unrelated tasks into one commit — user will call you out on this.

### Conventional Commits (development messages)

```bash
# Feature
git commit -m "feat: add user login endpoint" \
           -m "POST /api/auth/login validates credentials and returns JWT."

# Bug fix
git commit -m "fix: handle null token in auth middleware" \
           -m "Middleware crashed on missing Authorization header. Added early return."

# Refactoring
git commit -m "refactor: extract database connection pool" \
           -m "Moved connection logic from auth_handler.py to db/pool.py."

# WIP marker (use sparingly)
git commit -m "wip: experimenting with rate limiting approach"
```

### The body explains "why"

| Good body | Bad body |
|:----------|:---------|
| "Middleware crashed on missing header. Added early return guard." | "Fix auth bug" |
| "Moved to separate file to share across auth and billing modules." | "Refactored" |
| "Temporary — squash before merging to main." | "WIP" |

### Sign commits

```bash
# If commit.gpgsign is configured per-repo, `-S` is automatic
git commit -m "feat: ..."

# Otherwise, use -S explicitly
git commit -S -m "feat: ..."

# Verify the signature
git log --show-signature -1
```

## 5. Stashing (Saving Work-in-Progress)

### When to stash

- You're mid-work on feature A and need to hot-fix something on main
- You want to test a clean state without losing your changes
- You need to pull rebase but have uncommitted changes

### Basic stash operations

```bash
# Save current work (tracked files only)
git stash

# Save with a descriptive message
git stash push -m "wip: rate limiter unfinished"

# Include untracked files
git stash push -u -m "wip: new config parser"

# List stashes
git stash list

# Apply the latest stash (keeps it in stash list)
git stash apply

# Apply and remove from stash list
git stash pop

# Apply a specific stash
git stash apply stash@{2}

# Drop a stash (after deciding you don't need it)
git stash drop stash@{0}

# Apply stash to a different branch
git checkout feature-branch
git stash pop
```

### Recovery: applying stash to the wrong branch

```bash
# If you popped a stash on the wrong branch, create a patch from it
git stash show -p > /tmp/stash.patch
git checkout correct-branch
git apply /tmp/stash.patch
```

## 6. Syncing During Development

### Pull with rebase (recommended)

```bash
git pull --rebase

# Or set as default:
git config pull.rebase true
```

Rebase replays your local commits **on top** of remote changes, keeping a linear history:

```text
Before:    A---B---C (main)
                \
                 D---E (feature)

git pull --rebase on feature:

After:     A---B---C---D'---E' (feature)
```

### Handling conflicts during rebase

```bash
# Git tells you which files conflict. Fix them manually, then:
git add <fixed-file>
git rebase --continue

# If you realise the rebase was a mistake:
git rebase --abort

# Or skip a conflicting commit you don't need:
git rebase --skip
```

### When to merge instead of rebase

| Use rebase | Use merge |
|:-----------|:----------|
| Updating your feature branch from development | Merging a finished feature into development |
| Cleaning up your local history | Preserving explicit merge topology |
| Before pushing to a shared branch | When the merge commit itself is meaningful |

## 7. Pre-Push Verification & PR Merge

Before pushing, do a quick sanity check (baseline is **development**, not main):

```bash
# 1. Review what you're about to push
git log --oneline --graph origin/development..HEAD

# 2. Check commit signature
git log --show-signature -3

# 3. Verify no debug/test noise
git diff origin/development --name-only

# 4. Check the diff
git diff origin/development --stat     # files changed
git diff origin/development            # full diff (if small)

# 5. Run tests (if applicable)
make test || cargo test || pytest

# 6. Rebase onto latest development before pushing
git fetch origin
git rebase origin/development

# 7. Push the feature branch (never main/development directly)
git push -u origin feat/my-feature     # gitea first, then github
```

### Merge feature into development via PR

```bash
# Gitea (private, primary)
gh pr create --base development --head feat/my-feature   # or via Gitea web UI
# GitHub (public mirror) — same branch, same PR
git push github feat/my-feature
# open PR at github.com/alrcatraz/<repo>/compare/development...feat/my-feature

# After the PR is merged, clean up:
git checkout development
git pull --rebase
git branch -d feat/my-feature
git push origin --delete feat/my-feature     # both remotes
git push github --delete feat/my-feature
```

### Promote development → main

```bash
# Only after development is green and phase work is complete:
# open a PR development → main (Gitea + GitHub). Never push main directly.
```

The build server pulls **main only**, so nothing ships until development
has been promoted via PR.

## 8. Multi-Task Switching

When switching between tasks during development:

```bash
# 1. Commit current work (even if incomplete — use wip: prefix)
git add -A && git commit -m "wip: ..."

# 2. Push current branch (if you might want it on another machine)
git push -u origin HEAD

# 3. Switch to the other branch
git checkout other-feature

# 4. When coming back, continue where you left off
git checkout wip-feature
# Review your WIP commit, then either amend or reset
git log -1 --format="%B"
```

**Important:** Different tasks must be in separate commits. Never stash or commit two unrelated pieces of work together. If you catch yourself doing that, split with `git reset HEAD~` and re-stage with `git add -p`.

## Pitfalls

1. **Amending pushed commits.** Never `git commit --amend` a commit that has already been pushed. Use `git commit --fixup` + `git rebase -i` instead, or push a new fix commit.

2. **`git pull` without rebase.** Default `git pull` creates a merge commit. Unless you explicitly want one, use `git pull --rebase`.

3. **`git add -A` when you meant `git add -p`.** If you realise you staged unrelated changes, unstage them: `git reset HEAD <file>`.

4. **Stash on the wrong branch.** If you stash on main and pop on a feature branch, the changes apply to the feature branch. This is usually fine, but can cause unexpected conflicts. Verify with `git stash list` before popping.

5. **Commit without `-S`.** If `commit.gpgsign` isn't set, commits won't be signed. Check `git config commit.gpgsign` or use `-S` explicitly when needed.

6. **WIP commits left behind.** A `wip:` commit intended as temporary should be squashed before merging. Track with `git notes` or keep a `WIP` topic in your commit list.

7. **`git stash` loses untracked files by default.** Use `git stash push -u` to include untracked files, or add them first with `git add -N`.
