# Issue Management

View, create, and manage GitHub issues using `gh` or `curl`.

## Viewing Issues

```bash
# gh
gh issue list
gh issue list --state open --label "bug"
gh issue view 42

# curl
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:
        labels = ', '.join(l['name'] for l in i['labels'])
        print(f'#{i[\"number\"]:5}  {i[\"state\"]:6}  {labels:30}  {i[\"title\"]}')
"
```

## Creating Issues

```bash
# gh
gh issue create --title "Bug: login redirect" --body "Description..." --label "bug"

# curl
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues \
  -d '{"title": "Bug: login redirect", "body": "Description...", "labels": ["bug"]}'
```

## Managing Issues

| Action | gh | curl |
|--------|-----|------|
| Add label | `gh issue edit N --add-label "bug"` | `POST /repos/o/r/issues/N/labels` |
| Assign | `gh issue edit N --add-assignee user` | `POST /repos/o/r/issues/N/assignees` |
| Comment | `gh issue comment N --body "..."` | `POST /repos/o/r/issues/N/comments` |
| Close | `gh issue close N` | `PATCH /repos/o/r/issues/N -d '{"state":"closed"}'` |
| Reopen | `gh issue reopen N` | `PATCH /repos/o/r/issues/N -d '{"state":"open"}'` |
