---
name: astra-vcs-assist-github
description: "GitHub platform operations — authentication, issues, pull requests, releases, CI/CD, secrets, and repository management via the GitHub API."
version: 1.2.0
author: alrcatraz
platforms: [linux]
---

# astra-vcs-assist-github — GitHub Platform Operations

Consolidated GitHub operations covering authentication, issues, pull requests, releases, CI/CD, secrets, gists, and branch protection. All operations provide both `gh` CLI and `git` + `curl` API approaches.

## When to Load

- Setting up GitHub authentication (GCM, PAT, SSH, gh CLI)
- Creating, viewing, or managing issues
- Creating or reviewing pull requests
- Monitoring CI / re-running workflows
- Creating releases, managing secrets, or configuring branch protection
- Forking repositories or creating gists

## Prerequisites

### Auth Detection

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\\n\\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\\([^@]*\\)@.*|\\1|')
    fi
  fi
fi
```

### Extract Owner/Repo

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\\.com[:/]||; s|\\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)

if [ "$AUTH" = "gh" ]; then
  GH_USER=$(gh api user --jq '.login')
else
  GH_USER=$(curl -s -H "Authorization: token ***" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin)['login'])")
fi
```

## Reference Files

Load specific topics via `skill_view`:

| Topic | Load with |
|:------|:----------|
| Authentication (GCM, PAT, pass, gh, SSH) | `skill_view(name='astra-vcs-assist-github', file_path='references/auth-setup.md')` |
| Issue management (view, create, manage) | `skill_view(name='astra-vcs-assist-github', file_path='references/issues.md')` |
| Pull request workflow (create, CI, merge) | `skill_view(name='astra-vcs-assist-github', file_path='references/pr-workflow.md')` |
| Repo ops (fork, releases, CI, secrets, gists) | `skill_view(name='astra-vcs-assist-github', file_path='references/repo-operations.md')` |

## Quick Reference

| Operation | gh | curl endpoint |
|-----------|-----|---------------|
| Issues | `gh issue list/create/view/close` | `/repos/o/r/issues` |
| PRs | `gh pr create/merge/checks` | `/repos/o/r/pulls` |
| Releases | `gh release create/list` | `/repos/o/r/releases` |
| Workflows | `gh workflow/run/list` | `/repos/o/r/actions/workflows` |
| Secrets | `gh secret set/list/delete` | `/repos/o/r/actions/secrets` |
| Gists | `gh gist create/list` | `/gists` |
| Branch protection | `gh api repos/o/r/branches/main/protection` | `/repos/o/r/branches/main/protection` |
