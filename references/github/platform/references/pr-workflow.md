# Pull Request Workflow

Create, monitor, and merge pull requests on GitHub.

## Create a PR

```bash
# Push branch first
git push -u origin HEAD

# gh
gh pr create --title "feat: ..." --body "## Summary\n..." --label "enhancement"

# curl
BRANCH=$(git branch --show-current)
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{\"title\": \"feat: ...\", \"head\": \"$BRANCH\", \"base\": \"main\"}"
```

## Monitor CI

```bash
# gh
gh pr checks --watch

# curl
SHA=$(git rev-parse HEAD)
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status
```

## Merge

```bash
# gh (squash + delete branch)
gh pr merge --squash --delete-branch

# curl
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d '{"merge_method": "squash", "commit_title": "feat: ... (#N)"}'
```
