# Rewrite recipe and traps

The recipe that was run end-to-end the first time this block's procedure was executed, plus the traps it
turned up. Commands are copy-paste ready for the next rewrite; the narrative is stripped to what a reader
about to run it needs.

## Recipe used (verified end-to-end)

```bash
git reset --soft <ROOT>            # HEAD→root, index/worktree untouched
git checkout -b phase1-reorg       # branch from root
git reset -q                       # CRITICAL: mixed unstage (index→root tree)
# ... per-theme groups: git add -A <paths> → git commit -q -S -m "..."
git checkout main && git merge --ff-only phase1-reorg
git branch -d phase1-reorg
git tag -s v0.1.0 -m "..."
```

Result: root + 4 theme commits, linear, GPG-signed, zero workspace residue.

## Pitfall transcripts

### 1. `git add -A` multi-path aborts entirely on one bad pathspec

```bash
git diff --name-only A B | grep -v '^PLAN.md$' | xargs git add -A --
# fatal: pathspec 'CLAUDE.md' did not match any files
# → NOTHING after the failing path got staged (and the && chain broke)
```
Cause: path exists in commit A but was deleted by commit B; it is absent
from both index and worktree, so plain `git add` cannot see it.
Fix: `git add -A` stages deletions only when the path is in the index;
a path in neither index nor worktree is un-addable → filter it out, or
verify every path with `git ls-files` first, or add in small batches.

### 2. `reset --soft` keeps the whole diff staged

`git reset --soft <root>` moves HEAD only — index still equals the old
tree. A direct `git commit` would commit ALL ~1300 file diffs (incl.
1200 deleted mirror files) into commit #1. Must `git reset` (mixed) to
unstage everything, then re-add per theme group.

### 3. lint-staged failure REVERTS the staged state

`git commit` → husky pre-commit → eslint --fix failed →
```
✖ Failed to run tasks for staged files!
⋯ Reverting to original state because of errors…
```
This **unstages everything you had staged** (62 files lost from the
index). After fixing the cause you MUST re-`git add` the whole group
before committing again. Do not assume the index survived.

### 4. eslint suppressions go stale when files/rules disappear

Deleting files (electron tests, orphan scripts) leaves stale entries in
`config/quality/eslint-suppressions.json`; pre-commit eslint --fix then
fails with "There are suppressions left that do not occur anymore".
Fix:
```bash
# 1. drop entries whose file is no longer tracked
python3 -c "import json,subprocess; d=json.load(open('config/quality/eslint-suppressions.json')); tracked=set(subprocess.run(['git','ls-files'],capture_output=True,text=True).stdout.split()); [d.pop(k) for k in list(d) if k not in tracked]; json.dump(d,open('config/quality/eslint-suppressions.json','w'),indent=2,ensure_ascii=False)"
# 2. prune rule-level staleness on the touched files
npx eslint --fix --prune-suppressions --suppressions-location config/quality/eslint-suppressions.json <files...>
# 3. git add the suppressions file itself, then re-add the group, then commit
```

### 5. `git add` uses WORKTREE content — file-level attribution

When a file was changed by both the target commit and later commits,
`git add` stages the **final** content (e.g. package.json script
pruning landed in the UI commit; tsconfig electron-exclude removal too).
To force the target-commit version for overlapping files:
```bash
cp <f1> <f2> <f3> /tmp/c1-keep/          # preserve final versions
git checkout <COMMIT> -- <f1> <f2> <f3>  # index+worktree → that version
git add ...                              # commit the theme
cp /tmp/c1-keep/<f1> <f2> <f3> <paths>   # restore worktree finals (staged later)
```
Side effect: keys that the target commit added and later commits removed
(e.g. electron `startOnLogin` i18n keys) net-disappear inside the first
commit — acceptable, arguably cleaner.

### 6. Remote name may be `gitea`, not `origin`

`git push origin ...` → "fatal: 'origin' does not appear to be a git
repository". Check `git remote -v` first. This project: `gitea`
(https://<private-forge-host>/...) + `github`. Push to the named
remote: `git push gitea :refs/tags/v3.8.50`, `git push --force-with-lease gitea main`.

### 7. GitHub template placeholder commit

A freshly created GitHub repo (README auto-init ticked) contains an
"Initial commit" of template scaffolding (README/SKILL.md/pyproject.toml/
.gitkeep) unrelated to the project. Recon before pushing:
```bash
git ls-remote https://github.com/<user>/<repo>   # non-empty?
curl -s https://api.github.com/repos/<user>/<repo>/commits/<sha>  # inspect files
git fetch github                                  # sets lease expectation
git push --force-with-lease github main           # overwrite placeholder
```
`gh auth status` confirms push credentials (needs `repo` scope).

### 8. Orphan tag cleanup (local + remote)

Old tags pointing at pre-rewrite commits linger (`git rev-parse <tag>`
to verify it is off-history). Delete both sides:
```bash
git tag -d v3.8.50
git push gitea :refs/tags/v3.8.50      # remote deletion via empty refspec
```

### 9. Signed-tag ls-remote shows two lines

`git ls-remote <remote> | grep refs/tags` prints the annotated tag
object AND its `^{}` peeled line pointing at the commit — two lines per
signed tag is normal, not a duplicate.

### 10. Transient TLS EOF on push

`fatal: unable to access ... TLS connect error: unexpected eof while
reading` — flaky once, succeeding commands in the same batch worked.
Retry the same command; do not re-diagnose.

## Force-push vs PR decision rule

- History rewritten / remote holds wrong (old, template, or messy)
  history → **direct `--force-with-lease` push of main** + tags.
  PR cannot express a full-history replacement (it only appends).
  Single-owner repos need no review gate.
- Incremental work on a clean base → **feature branch + PR, rebase
  merge** (keeps linear history and commit granularity); local sync
  afterwards must be `git pull --ff-only` so drift is silent.

## Repo-state changes via the gh CLI: verify the state actually flipped

Archiving/unarchiving a repo gates every subsequent git write, so a no-op'd
transition silently invalidates the rest of a script:

```bash
gh repo archive   alrcatraz/<repo> --yes     # confirm/archive are INTERACTIVE without
gh repo unarchive alrcatraz/<repo> --yes     # --yes: they print usage and exit 0-ish
# prove it, do not trust the command's own output line:
gh repo view alrcatraz/<repo> --json isArchived,defaultBranchRef \
  --jq '"archived=\(.isArchived) default=\(.defaultBranchRef.name)"'
```

- **An archived repo is read-only at the transport level**: pushes fail with
  `remote: This repository was archived so it is read-only` + HTTP 403. Unarchive,
  make the change, re-archive — never assume a mid-script failure was transient.
- **Default-branch changes are API-only**: `git push` cannot move them. Use
  `gh api -X PATCH repos/<owner>/<repo> -f default_branch=<name>` and echo the returned
  field; the CLI subcommand form takes different arguments across versions and fails
  quietly in non-interactive runs.
- **Ordering trap in retire scripts**: create audit tags pointing at pre-rewrite commits
  BEFORE force-pushing branches off those commits — once unreachable, the remote rejects a
  tag ref for an object it no longer holds, and the rollback marker is lost.
