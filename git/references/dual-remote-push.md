# Dual-Remote Push Reference

> Companion reference for `astra-vcs-assist-git-sync` sub-skill.
> Covers multi-remote setup, push strategies, sync workflows, and Gitea-specific notes.

## Remote Naming Conventions

| Convention | When | Example |
|:-----------|:-----|:--------|
| `origin` / `mirror` | Primary + backup | `origin` = GitHub, `mirror` = Gitea |
| `github` / `gitlab` / `gitea` | Named by hosting | Explicit about destination |
| `origin` with push URLs | Single push to both | `git push` goes to all configured push URLs |

## Setup: Two Named Remotes

```bash
# GitHub as primary (read/write)
git remote add github https://github.com/owner/repo.git

# Gitea as secondary (read/write)
git remote add gitea https://git.example.com/owner/repo.git

# Push to both
git push github main
git push gitea main
```

## Setup: Single Remote with Multiple Push URLs

```bash
# Add the primary
git remote add origin https://github.com/owner/repo.git

# Add additional push URLs
git remote set-url --add --push origin https://github.com/owner/repo.git
git remote set-url --add --push origin https://git.example.com/owner/repo.git

# Verify
git remote get-url --all origin
# Output:
# https://github.com/owner/repo.git
# https://git.example.com/owner/repo.git

# Now `git push origin main` pushes to BOTH
```

### Important caveat

When using multiple push URLs, `git fetch origin` only fetches from the
**first** URL. The additional URLs are push-only. If you want to fetch
from the mirror too, keep separate remotes.

## Fork Workflow

When you've forked a repo from `upstream`:

```bash
# Named remotes
git remote add upstream https://github.com/original-owner/repo.git  # read-only
git remote add origin https://github.com/your-username/repo.git      # your fork (push)

# Sync from upstream
git fetch upstream
git checkout main
git merge upstream/main          # or: git rebase upstream/main

# Push to your fork
git push origin main

# Optional: also push to a self-hosted mirror
git remote add gitea https://git.example.com/your-username/repo.git
git push gitea main
```

## Daily Workflow

```bash
# After commits are ready:
git push origin main           # GitHub
git push mirror main           # Gitea
git push origin v1.2.0         # tag to GitHub
git push mirror v1.2.0         # tag to Gitea
```

Or as a one-liner:

```bash
for remote in origin mirror; do
  git push $remote main
  git push $remote --tags
done
```

## Gitea-Specific Notes

### Authentication

Gitea supports both HTTP and SSH:

```bash
# HTTP (with token or password)
git remote set-url gitea https://username@git.example.com/owner/repo.git

# SSH (with key)
git remote set-url gitea git@git.example.com:owner/repo.git
```

### Token-based auth for Gitea

```bash
# Generate a Gitea token in Settings → Applications
# Then use it as the password:
git remote set-url gitea https://username:${GITEA_TOKEN}@git.example.com/owner/repo.git

# Or store in credential helper (see git-sync sub-skill §5)
```

### Push mirroring from Gitea itself

Gitea has a built-in **push mirror** feature (Settings → Repository →
Mirror Settings → Push Mirror). This lets Gitea automatically push to
GitHub, keeping them in sync even if you only push to Gitea.

## Verification

After pushing, verify both remotes have the same state:

```bash
# Fetch from both
git fetch origin
git fetch mirror

# Compare
git rev-parse origin/main
git rev-parse mirror/main
# Both should return the same SHA

# Compare tags
git ls-remote --tags origin | sort
git ls-remote --tags mirror | sort
```

## Pitfalls

1. **Push URLs are order-dependent.** Git tries each URL in sequence. If the
   first succeeds, it doesn't try the rest. For mirroring, this is fine; for
   fan-out (push to A AND B), each push is attempted regardless.

2. **Fetch doesn't use push URLs.** `git fetch origin` only uses the first
   URL listed by `git remote get-url origin` (the fetch URL). Push URLs are
   strictly for pushing.

3. **Tags need explicit pushing.** `git push --tags` pushes to the specified
   remote. If you forget `--tags`, tags stay local. In dual-remote setups,
   you need to push tags to each remote separately.

4. **Force push on one remote doesn't affect the other.** If you force-push
   to GitHub, Gitea still has the old history. You must force-push to each
   remote individually.
