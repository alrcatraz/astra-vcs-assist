# Upstream Contribution (Fork → PR)

Contribute code to an upstream (not-your-fork) repository on GitHub.

## Pre-requisites

- `gh` CLI authenticated to at least one account
- GPG key configured for commit signing
- Local clone of the upstream repo

## Workflow

### 1. Account & GPG Setup

```bash
# List/switch gh accounts
gh auth status
gh auth switch --user <your-account>

# Per-repo identity
git config user.name "Your Name"
git config user.email "your-github-email@example.com"  # MUST match GitHub primary email
git config user.signingkey <key-id>
git config commit.gpgsign true
```

> **Critical:** GitHub associates commits with an account by the commit **email**
> address, not the author name. The email in `git config user.email` must match
> the GitHub account's primary email.

### 2. Feature Branch

```bash
git checkout -b feat/my-feature origin/main
```

### 3. Fork & Push

```bash
# Fork the upstream repo
gh repo fork Owner/Repo --fork-name Repo --clone=false

# Add fork remote
git remote add fork https://github.com/<your-account>/Repo.git

# Push branch
git push -u fork feat/my-feature
```

> **Note:** `gh repo fork --remote` is unsupported when a repo argument is
> provided. Use `--clone=false` and add the remote manually.

### 4. Open PR

```bash
gh pr create \
  --repo Owner/Repo \
  --head <your-account>:feat/my-feature \
  --base main \
  --title 'feat(scope): description' \
  --body '## Summary

Summary of changes.

## Changes

- **file1**: change description
- **file2**: change description

## Verification

- [x] Syntax check
- [x] GPG-signed commit'
```

> PR head format is `owner:branch`, not just branch name — required when the
> head is on a fork.

### 5. PR Monitoring (Optional)

Set up a `no_agent` cron job to watch for new activity:

```bash
# Create monitor script
cat > ~/.hermes/scripts/pr-monitor.py << 'EOF'
# Monitors comment count, review count, PR state, mergeable status.
# State persisted to pr-monitor-state.json.
# Silent on no change — only prints when something meaningful happens.
PRS = [
    {"repo": "Owner/Repo", "num": "12345"},
]
EOF

# Register cron
cronjob action=create \
  schedule="every 30m" \
  name="PR monitor" \
  script=pr-monitor.py \
  no_agent=true \
  repeat=-1 \
  deliver=origin
```

⚠️ Do NOT check `updated_at` / CI timestamps — GitHub's `updated_at` changes
on every CI re-run, label edit, or branch push, causing false-positive reports.

## Conflict Resolution

### Investigation

When `mergeable: state == 'dirty'`:

1. **Identify divergence** — `git fetch origin HEAD`, count commits since base tag
2. **Find overlapping commits** — `git log base..FETCH_HEAD -- path/to/file`
3. **Check for polluted branch** — commits already upstream:

```bash
git log --oneline fork/pr-branch --not FETCH_HEAD
```

### Strategy A: Rebase (clean branch)

```bash
git fetch origin HEAD
git checkout git-pr-branch
git rebase FETCH_HEAD
# resolve conflicts, then:
git add <resolved-files>
git rebase --continue
git push fork git-pr-branch --force-with-lease
```

### Strategy B: Cherry-pick (polluted branch)

When the PR branch has upstream commits already present in FETCH_HEAD,
rebase would replay all of them. Create a clean branch instead:

```bash
# Identify the PR's actual feature commit(s)
git log --oneline fork/pr-branch --not FETCH_HEAD

# Create clean branch, cherry-pick only the feature commit
git checkout -b pr-rebased FETCH_HEAD
git cherry-pick <feature-commit-sha>
# resolve conflicts: git add, git cherry-pick --continue

# Push to the PR branch
git push fork pr-rebased:pr-branch-name --force-with-lease
```

### Modify/delete conflict

When upstream deleted a file that the PR modified:
1. Accept the deletion — `git rm <file>`
2. Find where logic now lives — `git log --oneline FETCH_HEAD --diff-filter=AM -- path/to/`
3. Search for equivalent APIs — `git grep -n "related_api" FETCH_HEAD -- '*.rs'`
4. Port the PR's changes to the new location
5. Stage deletion + new code, continue

### Strategy C: Full structural rewrite

If upstream refactored so thoroughly that the diff cannot be mechanically applied:
1. Create fresh branch from upstream HEAD
2. Re-apply the PR's logical change (not the diff) to the new structure
3. Commit, push, open replacement PR, close the original

## Pitfalls

1. **`gh auth switch` is per-command, not per-session.** The switch changes the
   default account — switch back when done.
2. **Fork name must be unique** under your account. Use `--fork-name` to avoid
   collisions.
3. **`FETCH_HEAD` is a shared variable.** Any `git fetch` overwrites it. If you
   fetch from fork and upstream in sequence, the second fetch replaces the first.
   Use named ref expressions or re-fetch upstream after fork operations.
4. **Commit email mismatch.** Set `user.email` to match the GitHub account's
   primary email. If discovered after committing:
   ```bash
   git config user.email "correct@example.com"
   git commit --amend --reset-author --no-edit -S
   git push --force-with-lease fork <branch>
   ```
