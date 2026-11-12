# Grouping workspace changes into themed commits

Grouping workspace changes into themed commits.

## Workspace-only grouping (no history rewrite)

When only UNCOMMITTED changes need grouping (branch already has commits, keep them —
do NOT flatten), the task is "classify 100+ files → N themed commits". Verified on
a later phase (hundreds of files regrouped into a handful of commits):

1. **Classify BEFORE staging** — `git status --short` to enumerate, then per-file
   `git diff HEAD` keyword scan buckets files by feature theme. Untracked files are
   invisible to `git diff` — read them directly. Bucket by PLAN sub-item (user's rule:
   "分组参考整体规划，按修复的 bug/新功能组织"), e.g. quota feature keywords
   (`dmxapi|siliconflow|quota|usageconfig`), async markers (`await |async `), packaging
   markers (`basePath|createRequire|nativeRequire`). One script pass classifies all files;
   mixed-theme files go to the dominant theme.
2. **Stage by whitelist, never `git add -A`**: `git add <dir/> <file>...` per group, then
   **audit the index**: `git diff --cached --name-only | grep -vE "<group patterns>"` —
   strays slip in via directory adds (e.g. `src/lib/db/` sweep pulled in
   `driverFactory.ts`/`omp.ts` that belonged to the packaging commit).
3. **Pull strays out**: `git restore --staged <file>`. For an already-staged RENAME you
   must restore BOTH paths (`old` + `new`), else the index keeps a staged deletion while
   the new path shows untracked (`D old` + `?? new` split).
4. Commit each group with Conventional Commits; body names the plan sub-item. Pre-commit
   hooks (husky lint-staged + t11 any-budget) re-run the whole file list on EVERY commit —
   budget minutes per commit. Backup first: `git diff HEAD > /tmp/phase2-backup/precommit-$(date +%s).patch` + untracked list.

- **husky lint failure may point at a MISCLASSIFIED file** (2026-08-06): eslint's
  missing-dependency error in `ApiManagerPageClient.tsx` (a services-feature file staged
  into the cleanup group) blocked the whole group's commit. When the failing rule's
  identifier (e.g. a state variable name) matches a DIFFERENT theme's files, unstage the
  offender (`git restore --staged <file>`), move it to its correct group (rebase edit +
  amend — see amend trap), THEN commit. Don't fix unrelated code in place just to pass.

### Fixing a PUSHED wrong commit — never paper over (user rule, 2026-08-10)

User verbatim: 「你在哪个commit改出了错误的README，就要把那个commit修正，不能发新的commit来欲盖弥彰」.
If an ALREADY-COMMITTED change turns out wrong (wrong content, wrong section, wrong
language), the wrong commit must be REWRITTEN in place — a follow-up "fix" commit is
explicitly forbidden. Verified end-to-end on astra-agent-constellation (wrong README
section in feature commit, then a follow-up README commit made it worse):

1. The follow-up commit already exists → do NOT keep it. Fold its correct content into
   the original commit and delete it.
2. **Verified clean path (works even in a dumb terminal):**
   ```bash
   git checkout -b fix-<original> <original-sha>   # branch at the WRONG commit
   git reset --soft <base-before-original>          # all phase changes staged
   # worktree now holds the final correct state; fix files if needed, then:
   git commit -S -m "<same subject, corrected body>" # ONE fixed commit replaces the chain
   ```
   Then point the integration branches at it (they hold no independent commits):
   `git checkout development && git reset --hard <fixed-sha>`, same for `main`.
3. **`git rebase -i` squash into the original fails headless** with
   `error: Terminal is dumb, but EDITOR unset` — for the squash message. Either set
   `GIT_EDITOR=true` (accepts the combined message) or skip rebase entirely and use the
   reset --soft path above. Do NOT let the failed rebase leave a partial state — abort it.
4. **Do NOT merge the fix branch into development/main** when those still point at the
   OLD wrong commit — the merge conflicts (same file changed on both sides). Reset the
   integration branches (`git reset --hard`) instead; they are pure integration lines.
5. Force-push ALL remotes with lease, delete the orphaned old feature branch:
   ```bash
   git -c http.version=HTTP/1.1 push gitea main development --force-with-lease
   git push github public:main --force-with-lease   # GitHub main mirrors public
   git branch -D <old-feature-branch>               # still points at the wrong commit
   ```
6. **Verify no residue**: `git log --all --oneline | grep -c <wrong-sha>` = 0, and the
   fixed commit contains the final content (`git show <fixed> --stat`).

Note the correction chain that made the follow-up commit necessary in the first place:
the agent added a changelog-style "部署现状" section to a reader-facing README (violates
repo-language-convention Rule 5 release tone) — wrong-content fixes belong to the
language-convention skill; the git-side lesson here is purely the in-place-rewrite rule.

### The amend trap (missed file → wrong commit)

After a multi-commit sequence, HEAD is the LAST commit. `git commit --amend` on a missed
file silently merges it into the WRONG commit (Phase 2: `check-permissions.sh` landed in
the docs commit, not the build commit). Check `git log --oneline -1` BEFORE amending.

Two ways the wrong amend happens:
- HEAD is a LATER commit than the intended target (check `git log --oneline -1` first).
- **Pipe masks the rebase failure** (2026-08-06): `git rebase -i <base> | tail -2` exits 0
  because the pipeline's exit code is TAIL's — a following `&& git add ... && git commit
  --amend --no-edit` then amends HEAD (the LAST commit) as if the rebase had stopped at the
  target. Run rebase WITHOUT a pipe (or verify `git status` / `git rebase --continue` state)
  before amending; after a botched amend `git log --oneline` shows the target SHA changed.
Recovery:

```bash
git reset --soft HEAD~1          # undo the bad amend; changes stay staged
git restore --staged <file>      # drop the file from the index
git commit -m "..."              # re-create the last commit WITHOUT the file
# now insert into the earlier commit:
git stash push -m "pending" <file>
GIT_SEQUENCE_EDITOR="sed -i 's/^pick <hash>/edit <hash>/'" git rebase -i <hash>^
git stash pop && git add <file> && git commit --amend --no-edit
git rebase --continue
```

Verify: file shows in the right commit (`git show <hash> --stat | grep <file>`),
`git status --short` empty, replayed commits kept content.

### Companion-commit squash (18→14, Phase 2, 2026-08-04)

Third shape: branch has MANY committed sub-tasks; user wants **strict
one-commit-per-subtask** ("要严格一一对应"). Do NOT flatten the whole branch
— keep primaries, `fixup` companions (follow-up fixes, docs, UI preludes)
into them via interactive rebase. Verified on a later rewrite phase
(18 → 14 commits: 2.5 absorbed login-loop patch + conventions docs; 2.6
absorbed GLM quota fix; 2.7 absorbed media sidebar + 43 locale).

1. **Back up FIRST with a backup BRANCH** (patch backup alone can't restore
   commits): `git diff HEAD > /tmp/phase-backup.patch` +
   `git branch phase-pre-rebase-backup`. Delete it only after verification.
2. **Show the user the mapping table** (primary ← companions) BEFORE
   rebasing — they approve the plan, not just the result.
3. **Check file overlap** per pair before writing the todo:
   `git show <c> --name-only --format=""` — same-file edits are fine in
   historical order; moving a companion EARLIER than its original position
   is the risky case. (Phase 2: ee78b36/65ca444 both touched
   require-login/route.ts + login/page.tsx — 3-way merge resolved cleanly
   because order was preserved.)
4. **Write the todo to a file** (`pick` primaries, `fixup` companions right
   after their primary — `fixup` keeps the primary's message; `squash`
   would open an editor) and drive rebase non-interactively:
   ```bash
   GIT_SEQUENCE_EDITOR="cp /tmp/rebase-todo.txt" git rebase -i <base>
   ```
5. **Verify equivalence, not just success**:
   ```bash
   git diff <base>..HEAD --stat | tail -1                 # must equal:
   git diff <base>..phase-pre-rebase-backup --stat | tail -1
   git show <squashed> --stat | grep <key-file>           # merged content present
   git show <squashed> --stat | grep -c "i18n/messages"   # e.g. 43 locale files
   git status --short | wc -l                             # 0
   ```
6. **Re-sync PLAN.md completion markers AFTER the rebase** — every commit whose
   history was rewritten gets a NEW SHA, and PLAN.md sub-item headers that cite
   commit hashes become stale. Phase 2 (2026-08-04): 2.5 `ee78b36→d16320a`,
   2.6 `→d3988f7`, 2.7 `→e96a70f`, 2.8 `→f4ff6ff`, 2.3 `→2f030b6`. Grep for
   the OLD hashes (`grep -nE "commit [a-f0-9]{7}" PLAN.md`) and update each;
   also flip "working tree — 待提交" markers to `✅ COMPLETE (date, commit <new-sha>)`.

### Debug-arc flatten: one commit for 30–60 iteration commits (CI/workflow arcs)

A CI or workflow debugging arc produces a长 string of `diag probe`, `wip`, `try again`,
`fix quoting`, `debug checkout env` commits — the "测试用提交" the user expects to be
cleaned before the history is treated as durable. Do NOT reach for `git rebase -i`: it
needs an editor and hand-writing 40 `squash` lines invites mistakes. Collapse the arc in
three commands:

```bash
# 0. ALWAYS snapshot first — a force-push follows; a tag is the only way back
git tag -a backup/pre-tidy-$(date +%Y%m%d) HEAD -m "pre-tidy snapshot" --no-sign

# 1. locate the true start of the arc — the commit BEFORE the first series commit
git log --oneline -50          # e.g. the commit that first added the workflow file

# 2. soft-reset to it: worktree untouched, all file changes staged, history collapses
git reset --soft <arc-start>~1

# 3. drop artifacts that existed only to debug the arc
git rm --cached <probe>.py && rm -f <probe>.py

# 4. ONE commit whose message carries the DESIGN, not the saga
git commit -F -               # body: each decision baked in + the pitfall it answers
```

**Verify the squash removed nothing but what you meant to remove** — the check is a diff
against the snapshot and its expected output is a DELETION LIST ONLY:

```bash
git diff backup/pre-tidy-$(date +%Y%m%d) HEAD --name-status
# expect: D <probe>.py        ← nothing else.
# an M or A line means the squash dropped or altered real work — stop and inspect.
```

Then re-point every tag that named the old head and push branch+tag together — a
force-push rewrites the SHA the tag names, so leaving the tag unmoved points the release
at orphaned history:

```bash
git update-ref refs/tags/vX.Y.Z HEAD
git push <remote> <branch> --force-with-lease && git push <remote> vX.Y.Z --force
```

- **A leftover diagnostic script is a finding, not furniture.** Files added purely to probe
  runner/platform behaviour (`*_probe.py`, `diag-*.sh`) are dead the moment the workflow
  works — grep the final workflow for each before keeping it. On a repo that also has a
  public mirror they are a disclosure liability, since the probe often encodes runner
  topology or the debug technique used.
- **The rewrite invalidates the SHA of the green CI run, so re-trigger and re-verify.** The
  cleaned history is a NEW commit: the earlier passing run proves the old tree, not this one.
  Push the tag again and confirm the new run reaches the same conclusion before calling the
  tidy done — "it passed before I tidied" is not evidence about what you just pushed.
- **Report the tidy as a content-equivalence claim, not a completion claim.** The diff
  against the snapshot is what makes the claim checkable; quote its result (e.g. "only
  `D _cache_probe.py`") rather than asserting the history is clean.

### Push target: `development`, NOT the feature branch (Phase 2 verified, 2026-08-04)

User correction (verbatim): 「你推的分支是错的。我们之前说过，合并到develop分支，然后PR merge到main分支」.
After squashing a phase into clean theme commits on a feature branch, the deliverable
is the **`development` integration branch**, not the feature branch standing on the
remote. Verified sequence:

```bash
git branch phase-<name>-premerge-backup            # optional safety
git checkout -b development main                   # create if remote lacks it
git merge <feature-branch> --ff-only               # linear, no merge commit
git push -u gitea development                      # gitea FIRST, then github
git push -u github development
git push gitea --delete <feature-branch>           # remove wrongly-pushed branch BOTH remotes
git push github --delete <feature-branch>
# then open PR development -> main on BOTH platforms
```

- **Pre-push recon**: `git ls-remote --heads <remote>` — check whether the target
  integration branch (`development`) exists before pushing; a completed phase's work
  goes there, not on a standing feature branch.
- **Dependabot branches** (github `dependabot/npm_and_yarn/*`) are automatic and
  unrelated to your push — audit before assuming you pushed them.
- The Phase 1 "force-push main directly, no PR" guidance above applies to history
  REPLACEMENT on main; the Phase 2 norm for feature delivery is development + PR.
