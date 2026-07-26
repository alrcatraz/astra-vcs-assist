# astra-vcs-assist-git-release — Commit Cleanup & Release Management

*This reference was migrated from the `astra-vcs-assist-git-release` sub-skill.*

## Trigger Conditions

- Preparing to merge a feature branch into main
- Squashing WIP or fixup commits into clean history
- Splitting a large commit into smaller logical pieces
- Rewording commit messages for clarity
- Tagging a new release version
- Writing or generating a changelog

## Overview

```
Raw commits  →  Interactive rebase  →  Clean commits  →  Tag  →  Ship
```

## 1. Review the State of Play

```bash
git log --oneline --graph main..HEAD
git log --format="%h %s%n%b---" main..HEAD
git diff --stat main..HEAD
git rev-list --count main..HEAD | grep -E "^(wip|fixup|squash)"
```

## 2. Interactive Rebase

```bash
git rebase -i HEAD~N      # last N commits
git rebase -i main        # from branch point off main
```

### Commands

| Key | Command | Action |
|:----|:--------|:-------|
| `p` | pick | Use commit as-is |
| `r` | reword | Edit message |
| `s` | squash | Meld into previous commit |
| `f` | fixup | Squash, discard message |
| `d` | drop | Remove commit |
| `e` | edit | Stop for amending/splitting |

### Key operations

**Squash WIP into parent:**
```
pick a1b2c3d feat: add user login endpoint
fixup e4f5g6h wip: rate limiter unfinished
```

**Reword message:**
```
reword e4f5g6h fix: handle null token
```

**Split commit (mark as `edit`, then):**
```bash
git reset HEAD~
git add -p src/auth.py && git commit -m "feat: user auth"
git add -p src/config.py && git commit -m "refactor: config"
git rebase --continue
```

## 3. Commit Message Final Form

```
type(scope): short description (50 chars max, lowercase, imperative)

Longer explanation. Explain WHY, not just WHAT.
```

| Type | When |
|:-----|:-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring |
| `docs` | Documentation |
| `test` | Tests |
| `chore` | Maintenance |
| `ci` | CI/CD |
| `perf` | Performance |

## 4. Semantic Versioning

| Change | Bump | Example |
|:-------|:-----|:--------|
| Bug fix | PATCH | v1.0.0 → v1.0.1 |
| New feature | MINOR | v1.0.0 → v1.1.0 |
| Breaking change | MAJOR | v1.0.0 → v2.0.0 |

```bash
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

## 5. Changelog

```markdown
## [v1.2.0] — 2026-07-01

### Added
- Rate limiting on API endpoints (#42)

### Fixed
- Null pointer in auth middleware (#40)

### Changed
- Upgraded dependencies
```

## 6. Merge to Main

```bash
git checkout main
git merge feature-branch        # or: git merge --squash feature-branch
git tag v1.2.0
git push origin main --tags
git branch -d feature-branch
```

## 7. Open a Pull Request (fork)

```bash
git push -u origin feature-branch
# Use gh CLI or GitHub API to create PR
```

## Pitfalls

1. **Never rebase pushed commits** shared with others.
2. **`git push --tags` pushes ALL tags** — push individual tags instead.
3. **Moving tags confuses consumers** — treat pushed tags as immutable.
4. **`git commit --amend` on a pushed commit** creates divergent history.
