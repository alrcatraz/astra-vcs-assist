# Submitting Upstream PRs from Self-Hosted Git (Gitea → GitHub)

When patches live on a self-hosted Git server (Gitea, GitLab, etc.) and need to be submitted as PRs to an upstream GitHub repo.

## Prerequisites

- `gh` installed and authenticated (`gh auth login --web` for device code flow; one-time auth persists via `~/.config/gh/hosts.yml`)
- GitHub fork of the upstream repo exists under your account
- Local clone of your self-hosted Git repo

## Workflow

### 1. Check Existing State First

Before cloning or creating branches, check what already exists on the remote:

```bash
# List remote branches via API
curl -s 'https://gitea.example.com/api/v1/repos/user/repo/branches' \
  -H 'Authorization: token <TOKEN>' | python3 -c \
  "import sys,json; [print(b['name']) for b in json.load(sys.stdin)]"

# Or via git (if already cloned)
git branch -a
```

Do NOT create new branches if they already exist — just fetch and track them.

### 2. Fetch and Verify Branch Content

```bash
# Fetch the PR branch from your self-hosted Git
git fetch origin pr/my-feature-branch
git checkout -b pr-clean origin/pr/my-feature-branch

# Verify the diff against upstream base
git diff main..HEAD

# Check for local-only artifacts that should NOT go upstream:
# - CI trigger markers (# trigger <timestamp> in README)
# - Temp files, local config overrides
# - Personal IPs, hostnames, credentials
# - Commented-out debug code
```

### 3. Clean Up Local Artifacts

If local-only artifacts are mixed into the patch, revert them with a separate commit:

```bash
# Revert a dirty file to upstream version
git checkout main -- README.md
git add README.md
git commit -m "chore: remove local CI artifacts from README"
```

Each PR branch should contain only functional changes. The cleanup commit is fine preceding the PR.

### 4. Push Clean Branches to GitHub Fork

```bash
# Add your GitHub fork as a remote
git remote add github-fork https://github.com/YOUR_USER/REPO.git

# Push the clean branch
git push github-fork pr-clean-branch-name

# Use --force-with-lease if branch already exists remotely
git push --force-with-lease github-fork pr-clean-branch-name
```

### 5. Create PR Against Upstream

```bash
# --repo targets the UPSTREAM, --head points to your fork's branch
gh pr create \
  --repo upstream-owner/repo-name \
  --head YOUR_USER:branch-name \
  --base main \
  --title "type: short description" \
  --body "## Summary\n..."
```

## Pitfalls

- **`gh` not authenticated** — run `gh auth login --web`, get device code, open `https://github.com/login/device` in any browser, enter code. One-time setup.
- **PR branch exists on Gitea but not on GitHub fork** — this is the normal case. The push creates it on GitHub; `gh pr create` then references it from your fork.
- **`gh pr create` fails with "no commits"** — the branch on your GitHub fork may differ from the local one. Verify with `git push` first.
- **Local-only artifacts in diff** — always `git diff main..HEAD` and visually scan before pushing. CI trigger markers (`# trigger <timestamp>`) are a common Gitea CI artifact.
