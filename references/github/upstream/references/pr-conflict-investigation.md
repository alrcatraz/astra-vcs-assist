# PR Conflict Investigation

Workflow for investigating why an open PR shows `mergeable: false` /
`mergeable_state: dirty` after upstream has moved forward.

### 0. Force-refresh the local upstream ref BEFORE trusting any local merge test

A stale `origin/main` silently flips a local conflict verdict: `git fetch origin main`
without `--force` can be a no-op on some remote configs, leaving your local ref N commits
behind while GitHub computes `dirty` against its own tip. Symptom of the divergence trap:
`git merge-tree --write-tree origin/main <pr-head>` returns rc=0 (no conflict) yet GitHub
reports `mergeable_state: dirty`. Cross-check with the compare API —
`gh api repos/<o>/<r>/compare/main...<owner>:<branch> --jq '{status,ahead_by,behind_by}'`:
`diverged` + nonzero `behind_by` means YOUR LOCAL REF IS STALE, not that GitHub is wrong.
Then force-fetch (`git fetch origin +refs/heads/main:refs/remotes/origin/main`) and re-run
merge-tree; only after the refs agree is a local verdict trustworthy. Never conclude
"GitHub is misreporting" from a clean local merge-tree without first proving
`rev-list --count <pr-head>..origin/main` matches GitHub's `behind_by`.

## Quick check

```bash
# PR mergeable status (single command)
curl -s -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/Org/Repo/pulls/12345 | \
  jq '{title, state, mergeable, mergeable_state, head: .head.ref, base: .base.ref}'
```

## Step-by-step

### 1. Identify the divergence

Find out how far upstream has moved since the PR's base commit:

```bash
# Fetch the upstream main branch
git fetch origin HEAD   # or: git fetch upstream main

# Count commits since the base tag
git log --oneline vX.Y.Z..FETCH_HEAD | wc -l

# List them
git log --oneline vX.Y.Z..FETCH_HEAD
```

### 2. Find commits touching PR files

```bash
git log --oneline vX.Y.Z..FETCH_HEAD -- path/to/modified/file.rs
```

Repeat for every file the PR modifies. This shows which upstream commits
overlap and are likely causing conflicts.

### 3. Assess conflict scope

Check whether the upstream changed files were:

- **Full rewrites** (`-300/+400` type changes): the PR commit probably
  cannot be applied cleanly. The feature may need to be re-implemented
  on top of the new code structure.
- **Additive changes alongside ours**: minor merge conflicts, resolvable
  with standard `git rebase` + conflict resolution.

Key indicators of deep conflicts:

| Signal | Meaning |
|:-------|:--------|
| Upstream deleted the file entirely | Feature must be re-integrated into the replacement |
| Proto file restructured (type generation) | The field definition + all usages need updating |
| Core module split into portable/native | The PR's logic needs to land in the correct new module |

### 4. Attempt rebase — but check for upstream-commit pollution first

A shallow clone corrupts every range-based answer here. Before trusting
`merge-base`, `merge-tree`, or any `<base>..HEAD` listing, run
`git rev-parse --is-shallow-repository`; if `true`, all three lie:

- `merge-tree` exits 128 with `fatal: refusing to merge unrelated histories` —
  NOT a real conflict; a depth-limited clone simply has no common ancestor.
- `git diff --name-only <base>..HEAD` returns a nonsense file set (tens of
  thousands of files — effectively the whole repo) because with no merge-base
  git falls back to a whole-tree comparison.
- `git merge-base` prints NOTHING. An empty merge-base plus a whole-tree diff is
  the signature; treat BOTH as "clone is shallow", never as "the PR is huge".

Fix the clone FIRST, in the background — unshallowing a large repo takes minutes
and must not run inside a bounded foreground cell (it will time out and kill your
kernel):

```bash
git fetch upstream main --unshallow    # background / long timeout
# verify: git rev-parse --is-shallow-repository → false
# verify: git merge-base HEAD upstream/main → a real sha
```

Before rebasing, check whether the fork PR branch has commits that are
already on upstream (common when the fork was created from a stale base):

```bash
git log --oneline fork/pr-branch --not FETCH_HEAD
```

If this shows only your feature commit(s) — proceed with normal rebase.
If it shows upstream commits too — use the cherry-pick strategy instead.
If it shows OTHER of YOUR OWN feature commits that are NOT part of this PR
(the branch has drifted onto unrelated work) — do NOT rebase the whole branch:
a plain rebase drags those commits into the PR. Cherry-pick ONLY the PR's own
commit range onto a fresh branch:

```bash
# Identify the PR's true commit list FIRST — from GitHub, not the local branch:
gh api repos/<o>/<r>/pulls/<n>/commits --jq '.[].sha'
# Then replay exactly that range onto a fresh branch:
git checkout -b pr/<n>-rebased upstream/main
git cherry-pick <oldest-sha>^..<pr-head-sha>
# If conflicts, resolve them:
git add <resolved-files>
git cherry-pick --continue --no-edit
```

`--no-edit` matters inside a tool call: `cherry-pick --continue` with no flag
tries to open an editor and hangs. Verify the replayed branch carries EXACTLY
the PR's commit count and nothing else (`git rev-list --count
upstream/main..HEAD` must equal the API's list length) before pushing.

### 5. Decide next steps

| Conflict type | Action |
|:--------------|:-------|
| Simple line conflicts | `git rebase`, resolve, `--continue`, force push |
| File fully rewritten | Re-implement the PR's logic on new structure |
| PR changes now in upstream | Close the PR (upstream already fixed it) |
| Multiple PRs overlapping same files | Rebase one first, then the other onto the result |

## Pitfalls

1. **`FETCH_HEAD` is ephemeral.** If you run multiple git commands between
   fetches, `FETCH_HEAD` still points to the last fetch. Be explicit about
   which remote/branch you fetched.
2. **⚠️ `FETCH_HEAD` is a shared variable — any subsequent fetch overwrites it.**
   If you fetch the fork's PR branch (`git fetch fork pr/foo`), that overwrites
   the upstream FETCH_HEAD set by `git fetch origin HEAD`. After that, `git
   rebase FETCH_HEAD` silently rebases onto the **fork branch tip**, not the
   upstream main. You won't notice until GitHub shows `mergeable: false` and
   the PR commit parent is wrong. **Mitigations:**
   - Use `git fetch origin main` (named ref) when the remote spec permits it
   - Or re-fetch the upstream after any intermediate fork fetch
   - Or capture the upstream hash early: `UPSTREAM=$(git rev-parse FETCH_HEAD)`
3. **`origin/main` doesn't exist if the remote fetch spec is tag-only.**
   Some repos configure remote fetch to only pull specific tags (e.g.
   `+refs/tags/v2.6.4:refs/tags/v2.6.4`). In that case `origin/main` is
   never created. Use `git fetch origin HEAD` + `FETCH_HEAD` instead.
4. **`mergeable_state: dirty` ≠ `mergeable: false`.** `dirty` means
   GitHub hasn't recalculated the merge status yet (CI still running,
   recently pushed). `dirty` can resolve to `clean` or `blocked` or
   `behind` after recalculation. Only `mergeable: false` + `dirty` is
   a confirmed conflict.
5. **The GitHub API returns `mergeable` as `null`** while GitHub computes
   it. Poll after a few seconds if you see `null`.
   A monitor that reads it must treat `null` as *unknown*, never as a value:
   compare only bool-to-bool transitions (`prev is not None and now is not
   None and prev != now`), otherwise every recompute window fires a false
   `True -> None` alert and a second false `None -> True` alert when the value
   returns — two spurious alerts per recompute, on every PR, forever. To get a
   fresh reading instead of GitHub's cache, hit
   `GET /repos/<o>/<r>/pulls/<n>?test=true`, which forces a recompute. NEVER
   read mergeability from `GET .../pulls/<n>/merge` — that is the PUT
   merge-creation endpoint and returns 404 on GET.
6. **`git log --oneline pr-branch --not FETCH_HEAD` can list upstream
   commits if FETCH_HEAD points to the fork instead of upstream.**
   Always check what FETCH_HEAD resolves to: `git rev-parse --short FETCH_HEAD`.
   If it's the fork's hash (not upstream's), you have FETCH_HEAD pollution.
