# Code review, push, opening the PR, its body

## Code review before push

Before pushing, verify the diff:

```bash
# Show what you're about to push (against what it will merge into)
git log --oneline origin/main..HEAD
git diff --stat origin/main..HEAD
```

Check for:
- Hardcoded secrets, tokens, credentials
- Debug print/breakpoint/pdb left in
- Commented-out code without a TODO
- Missing or wrong type annotations (project convention)
- Test coverage for the new behaviour
- **Wrong issue references (`Closes #N` / `Fixes #N`)**: verify every issue number in
  the PR body and commit messages actually belongs to this feature's bug/feature
  issue. If the number points to an unrelated PR/issue (wrong number from a
  template, copy-paste from another PR, an auto-increment guess), **delete the
  reference entirely — do NOT guess a replacement number.** A wrong `Closes #N`
  closes someone ELSE's issue on merge (or worse, their open PR). If you cannot
  identify the correct issue from the repo's own search, leaving no reference is
  safe; leaving a wrong one is not. Fix via `gh api -X PATCH` on the PR body and
  on each comment that carries the bad reference — do this BEFORE pushing if it's
  in a commit message (amend), or as comment/PATCH edits if already pushed.

## Step 6 — Push & Open PR

```bash
# Push to fork (origin usually points at UPSTREAM — a bare `git push`/`-u origin`
# 403s with "Permission ... denied": upstream is not writable. Push to the fork remote.
git push -u fork feat/my-feature
```

Identify the remotes before pushing (`git remote -v`): the remote your branch
TRACKS (from `git rev-parse --abbrev-ref @{u}`) is often upstream, not the fork.

```bash
Or if already tracking, force push after rebase
git push --force-with-lease fork feat/my-feature
```

Open the PR using the GitHub CLI or web:

```bash
gh pr create \
  --repo NousResearch/hermes-agent \
  --head alrcatraz:feat/my-feature \
  --base main \
  --title "feat: brief description" \
  --body "## Summary

## Changes

## Testing

## Notes"
```

## Post-PR monitoring

```bash
# Check PR status
gh pr view --repo NousResearch/hermes-agent/<number>

# Check mergeability
gh pr view <number> --json mergeable,mergeableState
```

Use `scripts/pr-monitor.py` for automated monitoring.
