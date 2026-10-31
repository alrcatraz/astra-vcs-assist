# Review Fix → Push → Reply Loop

Addressing GitHub review comments on an open PR: the mechanics from identifying
the PR's head branch through pushing and replying point-by-point.

## Core facts

- A PR tracks the **head branch** it was opened from (on the fork). Pushing new
  commits to THAT branch auto-updates the PR — your local branch name is
  irrelevant. Never assume the PR follows a new branch you create.
- Review comments live at TWO possible levels: inline code comments
  (`/pulls/N/comments`) AND issue-level comments (`/issues/N/comments`).
  **Check both** — a comment can sit under either while the other list is empty.
  Reviews themselves: `/pulls/N/reviews`.
- **Only one of those endpoints posts a conversation comment.**
  `POST /repos/<o>/<r>/issues/<n>/comments` writes to the PR/issue conversation
  box. `POST /repos/<o>/<r>/pulls/<n>/comments` creates an INLINE review comment
  and answers 422 (`No subschema in "oneOf" matched`) without
  `commit_id`+`path`+`line`. Retrying the wrong endpoint never succeeds — switch
  endpoints; a 422 on the second attempt means you are still asking for a
  different object, not that the network is flaky.

## Steps

1. Identify the PR's head branch and current sha:

   ```bash
   curl -s https://api.github.com/repos/UPSTREAM/OWNER/REPO/pulls/N | \
     python3 -c "import json,sys; d=json.load(sys.stdin); print(d['head']['ref'], d['head']['sha'])"
   ```

2. Base your fix branch on that exact sha (fetch the fork's branch first).
   Verify with `git log --oneline -1 <sha>` and `git rev-parse <sha>`.

3. Commit the fix (signed), then verify signature + build:

   ```bash
   git verify-commit HEAD                 # expect "Good signature"
   git log --format='%h %s %G?' -1        # G = good, B = bad, N = unsigned
   cargo check -p PKG --features FEAT     # feature build
   cargo check -p PKG                     # default build (optional dep isolation)
   ```

4. Push to the PR's head branch via refspec (fast-forward when based on PR head).
   Name the commit, not a local branch, unless you have asserted they agree:

   ```bash
   git rev-parse HEAD INTENDED-BRANCH   # the two shas MUST match before pushing
   git push github HEAD:refs/heads/PR-HEAD-BRANCH
   ```

   **Force is the exception, not the default.** GitHub auto-tracks the fork's
   head branch, so a plain push of *new commits* updates the PR — no force flag
   at all. `--force-with-lease` is justified ONLY when you rewrote history on
   that branch (amend, rebase, squash), where the remote and local tips have
   diverged and a plain push is rejected as non-fast-forward.

   **Prefer adding a commit over amending when the branch is already pushed.**
   A follow-up commit (`fix(scope): <what changed>`) updates the PR with a plain
   push and gives the reviewer a readable delta. Amend-and-force is the choice
   only when a single clean commit is genuinely wanted — and note it conflicts
   with the general 'amend to update this commit' preference: that preference
   implies a force push whenever the branch already exists upstream, so pick it
   deliberately rather than by habit.

5. Confirm the PR updated: re-query the API — `head.sha` must equal your new
   commit, `updated_at` fresh, `commits` count incremented.

6. Fetch comments for the reply, then reply on the PR page (Reply button on the
   comment, or page-bottom box). Markdown reply should state: the commit hash,
   what changed per comment point, and verification results.

## Pre-push verification ladder

Run these in order after the fix commit; each kills a specific false signal.
Use the repo's canonical test entry point (never a bare venv pytest — on a host
that also runs production, the suite's home-IO guard masks a real result as a
test failure).

```bash
# 1. signature — verify-commit, not %G? (confirms the key uid matches the author)
git verify-commit HEAD
# 2. lint with the version CI pins, on exactly the changed files
git diff --name-only <base> HEAD | grep '\.py$' | xargs uvx ruff@<pinned> check
# 3. purity: scan only the added lines
git diff <base> HEAD --unified=0 | grep '^+' | grep -v '^+++' | grep -iE '<own-brand/infra terms>'
# 4. commit-message hygiene: forbidden keywords + CHAR (not byte) line length
git log -1 --format=%B | grep -icE 'closes|fixes #|<deployment-env words>'
git log -1 --format=%B | python3 -c "import sys;ls=sys.stdin.read().splitlines();print(max(map(len,ls)))"
# 5. working tree: no UU, no leftover backups staged
git status --short
```

Match the repo's own wrapping: sample recent commit bodies (`git log -N
--format=%B`) for max line length before re-wrapping yours — an em-dash is 3
bytes, so `awk length` over-reports and you will 'fix' lines that were fine.

## Pitfalls

- **Read the lint config the tool actually loads, and pin the CI's version.** A
  repo can carry a root `ruff.toml` that overrides `[tool.ruff.lint]` in
  `pyproject.toml` — reading `pyproject` alone tells you a rule is disabled while
  the effective select list has it enabled, or the reverse. Confirm with the
  version CI installs (`uvx ruff@<pin> check <files>`) and grep the effective
  config for the specific codes (`RUF100`, `F811`, …) INCLUDING commented-out
  lines: a commented code was deliberately turned off, which means CI will not
  catch it and you must. Workflow prose describing the blocking set goes stale —
  the config file is the authority.
- **A test file reported FAILED with 0 collected is usually the runner's
  per-file wall budget, not a regression.** Prove it two ways: run the same file
  in a clean baseline checkout (`git worktree add /tmp/<name> <upstream-base>`
  — avoids stashing entirely and cannot disturb your tree), and re-run yours with
  the budget raised (e.g. `HERMES_TEST_FILE_TIMEOUT=900 <canonical runner>
  <file>`). Only a same-file, same-selection green run at a raised budget
  licenses the claim 'environmental, not mine'.
- **Prefer per-file copies over `git stash` for red/green controls:** `cp f
  /tmp/f.fixed`, break `f`, run the one test, restore with `cp /tmp/f.fixed f`.
  A stash can carry files you never named and surface them as `UU` on pop; a copy
  restores exactly one file and is checkable by re-grep.
- **After generalising a state field, audit every consumer of the old one.** When
  a change adds a collection beside the scalar it supersedes, grep the whole
  source tree for reads of the scalar — request-time paths outside the file you
  edited are precisely where the stale single-value decision survives, and the
  existing tests may never exercise the new shape. Then check the fallback
  chain's None behaviour: `getattr(obj, "f", "")` returns `None`, not the
  default, when the attribute EXISTS and holds `None`, so any chain that ends by
  iterating the result needs a trailing `or ""`. A consumer reading only the
  scalar silently rejects legitimate input naming the second member.
- **A fix's regression test must be proven to FAIL without the fix.** After
  writing or strengthening an assertion, revert the production change (stash it,
  or inline-swap the fixed expression back to the broken one), re-run the ONE
  test, and confirm it goes red; then restore and confirm green. An assertion
  that passes in both states is false-green and protects nothing — the common
  shape is anchoring on the input just consumed (`assert not stripped.startswith(prefix_just_used)`) instead of the exact expected output, which a longer
  sibling value silently satisfies. Verify by running the single test file, not
  the whole suite, so the signal is unambiguous.
- **Do not `git stash` and forget it.** If you stash to run the negative
  control, `git stash pop` immediately after and re-run to confirm the working
  tree is back to the fixed state before committing; a lost stash silently ships
  the unfixed file.
- **A baseline-control `git stash` can drag in files you did NOT name, and its
  `pop` then collides.** `git stash push -- <file1> <file2>` looks scoped, but if
  the working tree already carried unrelated uncommitted edits (from an earlier
  turn or another task), the resulting stash entry may hold MORE than the two
  files you listed — and `git stash pop` surfaces them as merge conflicts on
  files that are otherwise clean at HEAD. Before using stash for a red/green
  baseline, run `git status --short` and confirm ONLY your intended files are
  dirty; if anything else is modified, commit it, or use `git stash push -k`
  (--keep-index) / a per-file copy-out instead. After any `pop`, `git status`
  must show NO `UU` paths before you proceed — an unmerged path means the tree is
  half-restored and the next commit would ship a conflict-marker file. Recovery
  when it happens: the named files are safe because they were already committed,
  so `git checkout HEAD -- <conflicted files>` discards the bad pop cleanly; rescue
  any UNCOMMITTED new work first (`cp` the live files to scratch, verify with
  `ls`) before that checkout wipes them.
- Don't `git push github NEW-BRANCH` and expect the PR to follow — push to the
  recorded head ref explicitly.
- **The mirror trap: pushing the CORRECT head-branch name while your work sits on
  a differently-named branch.** A PR head branch usually exists locally as a
  stale leftover (`feat/x` still pointing at last month's tip) while the real
  work was committed onto a fresh topic branch (`pr/N-regraft`). `git push
  --force-with-lease=... origin feat/x` then succeeds — the lease only checks the
  REMOTE value — and lands a months-old, possibly unsigned commit on a live PR.
  The remote accepts it silently; only reading `head.sha` back reveals it.
  Therefore: (a) before pushing, `git rev-parse <local-branch>` and require it to
  equal the sha you just built; (b) prefer `HEAD:refs/heads/<branch>` or
  `<sha>:refs/heads/<branch>` over a bare branch name; (c) after an amend, realign
  the head-branch name immediately (`git branch -f feat/x <new-sha>`) so the next
  push cannot regress; (d) re-query `head.sha` after every force-push and fix
  forward with a second lease anchored on the value you just wrote.
- **Before replying "fixed" to a review point, prove the fix is on the PR's
  head sha** — compare the API-reported `head.sha` against your local branch
  tip AND the fork remote (`git ls-remote <fork> refs/heads/<branch>`). A reply
  claiming points are addressed while head still sits at the pre-review commit
  is an overclaim that costs trust when the reviewer checks. Two look-alike
  traps: (a) a verification comment reporting suites green may have run against
  the OLD head — it confirms nothing about the review points; (b) a newer local
  mtime on the touched files is not evidence of a push — only sha equality is.
- `rm -rf` on untracked junk files triggers the security approval gate (can
  hang on no response). Use `mv junk /tmp/xxx-backup/` instead — non-destructive
  and reversible, no approval needed.
- GPG signing in headless (no-tty) shells: cache the passphrase first with
  `gpg-preset-passphrase` (see astra-vcs-assist-gpg-key skill for the binary
  path), otherwise `commit -S` fails.
