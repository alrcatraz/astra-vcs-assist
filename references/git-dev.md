# astra-vcs-assist-git-dev — Daily Development Workflow

*This reference was migrated from the `astra-vcs-assist-git-dev` sub-skill.*

## Trigger Conditions

Use this reference when:

- Starting work on a new feature, fix, or refactor
- Making commits during active development
- Deciding between merge and rebase
- Needing to save work-in-progress (stash) or restore it
- Reviewing your working tree before pushing
- Resolving merge conflicts

## Overview

Daily git work follows a rhythm: **start → work → commit → repeat**.

```
Start work       →  Branch      →  Make changes  →  Review  →  Commit  →  Repeat
    │                                                          │
    └── Stash (if interrupted)     Run tests ──────────────────┘
```

## 1. Branching Strategy

### Start from a clean main

```bash
git checkout main
git pull                    # or: git pull --rebase
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
git checkout feat/user-auth
git checkout -b feat/user-auth-permissions feat/user-auth
```

## 2. Daily Status Checks

```bash
git status
git diff
git diff --cached
git status --short
git log --oneline main..HEAD
```

## 3. Staging Strategies

| Pattern | Command | When |
|:--------|:--------|:-----|
| **Stage all** | `git add -A` | Small, focused changes |
| **Stage by file** | `git add src/auth.py` | Medium, some unrelated files |
| **Stage by hunk** | `git add -p` | Large edits, commit in pieces |

### `git add -p` options

```
y — stage this hunk
n — skip this hunk
s — split hunk into smaller pieces
e — manually edit the hunk (advanced)
q — quit
```

## 4. Commit Discipline

- **One logical change per commit.** Never mix unrelated changes.
- **Commit early, commit often.** Small commits are easier to squash later.
- **Different tasks, different commits.** No merging unrelated tasks.

### Conventional Commits

```bash
git commit -m "feat: add user login endpoint" \
           -m "POST /api/auth/login validates credentials and returns JWT."

git commit -m "fix: handle null token in auth middleware" \
           -m "Middleware crashed on missing Authorization header."

git commit -m "refactor: extract database connection pool" \
           -m "Moved connection logic from auth_handler.py to db/pool.py."
```

### Sign commits

```bash
# If commit.gpgsign is configured, -S is automatic
git commit -m "feat: ..."
# Otherwise:
git commit -S -m "feat: ..."
# Verify:
git log --show-signature -1
```

## 5. Stashing

```bash
git stash                                    # save tracked files
git stash push -u -m "wip: rate limiter"     # include untracked
git stash list
git stash pop                                # apply + drop
git stash apply                              # apply only (keep in list)
git stash apply stash@{2}                    # apply specific stash
git stash drop stash@{0}                     # drop specific
```

## 6. Syncing During Development

```bash
git pull --rebase                            # recommended
git config pull.rebase true                  # set as default
```

### Handling conflicts during rebase

```bash
git add <fixed-file>
git rebase --continue
git rebase --abort             # abort if wrong
```

| Use rebase | Use merge |
|:-----------|:----------|
| Updating feature branch from main | Merging finished feature into main |
| Cleaning up local history | Preserving explicit merge topology |

## 7. Pre-Push Verification

```bash
git log --oneline --graph origin/main..HEAD
git log --show-signature -3
git diff origin/main --name-only
make test || cargo test || pytest
git push
```

## 8. Multi-Task Switching

```bash
git add -A && git commit -m "wip: ..."
git push -u origin HEAD
git checkout other-feature
# Later:
git checkout wip-feature
```

## Pitfalls

1. **Never amend pushed commits.** Use `git commit --fixup` + `git rebase -i --autosquash`.
2. **`git pull` without rebase** creates merge commits. Use `git pull --rebase`.
3. **Stash on wrong branch.** Verify with `git stash list` before popping.
4. **WIP commits left behind.** Squash before merging.
5. **`git stash` loses untracked files.** Use `git stash push -u`.
