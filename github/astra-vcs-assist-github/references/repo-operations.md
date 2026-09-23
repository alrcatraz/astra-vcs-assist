# Repository Operations (API)

GitHub API operations beyond basic git: fork, releases, CI, secrets, branch protection, gists.

## Fork

```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo-name/forks
sleep 3
git clone https://github.com/$GH_USER/repo-name.git
cd repo-name
git remote add upstream https://github.com/owner/repo-name.git
```

## Releases

```bash
# gh
gh release create v1.0.0 --title "v1.0.0" --generate-notes

# curl
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/releases \
  -d '{"tag_name": "v1.0.0", "name": "v1.0.0", "generate_release_notes": true}'
```

## GitHub Actions / Workflows

```bash
# gh
gh workflow list
gh run list --limit 10
gh workflow run ci.yml --ref main

# curl — list workflows
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/workflows

# curl — trigger workflow_dispatch
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/workflows/ci.yml/dispatches \
  -d '{"ref": "main"}'
```

## Secrets

```bash
# gh (much simpler)
gh secret set API_KEY --body "your-secret-value"
gh secret list

# curl — requires libsodium encryption, use gh instead
```

## Branch Protection

```bash
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{
    "required_status_checks": {"strict": true, "contexts": ["ci/test"]},
    "enforce_admins": false,
    "required_pull_request_reviews": {"required_approving_review_count": 1}
  }'
```

## Delete Repository

```bash
# gh (requires the delete_repo scope!)
gh repo delete OWNER/REPO --yes

# curl
curl -s -X DELETE -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO
```

### Pitfalls

- **Deleting a repository requires the `delete_repo` scope** — a plain gh token (`gist, read:org, repo, workflow`) gets 403: `Must have admin rights to Repository.` / `This API operation needs the "delete_repo" scope`
- Add the scope: `gh auth refresh -h github.com -s delete_repo` → the device-code flow **requires the user to enter the code in a browser** (no agent substitute; codes expire in ~5 minutes, so repeated timeouts occur when the user is away from the machine)
- Even with delete_repo, another account cannot delete a repo it does not administer (`permissions.admin=false`)
- Web fallback: repo page → Settings → Danger Zone → Delete this repository → type the repo name to confirm
- Before deleting, verify the target really is a stray/empty shell: `gh api repos/O/R/git/trees/HEAD --jq '.tree[] | .path'` should list only licence-class single files, with the real content elsewhere (another owner/backup)

## Gists

```bash
# gh
gh gist create script.py --public --desc "Useful script"

# curl
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/gists \
  -d '{"description": "Useful script", "public": true, "files": {"script.py": {"content": "print(\"hello\")"}}}'
```
