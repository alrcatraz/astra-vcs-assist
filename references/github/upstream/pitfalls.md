# Failure modes of upstream contribution

## Pitfalls

- **A deployed instance can run a DIFFERENT tree than the one you edit.**
  Environment/plugin installers (`pm install`) copy a snapshot of the source into
  `…/installs/<id>/environments/<hash>/workspace/`, and that copy can sit earlier
  on `sys.path` than the repo you are patching. The traceback's `(path/file.py)`
  names the module the interpreter RESOLVED, not necessarily the file you wrote.
  Check with `grep -rln '<newsymbol>' <install-root> --include='*.py'`: both trees
  appearing, symbol in one and not the other, is the cross-tree signature. The
  workspace snapshot is not a symlink — syncing into it does not sync the repo,
  and clearing `__pycache__` in the repo does nothing for a stale `.pyc` there.
  Before concluding ANYTHING from a traceback on a deployed copy, confirm which
  tree the hosting process inserted into `sys.path` (`ps -eo cmd | grep -i hermes`).
- **Never restart the service that hosts your own session from a tool call.**
  On a host where the agent is served by the unit it is patching,
  `systemctl --user restart <serve unit>` kills the process backing the
  conversation (symptom: "session kernel died", or the reply becomes a bare
  interrupt placeholder). Identify your own unit first
  (`ps -eo pid,lstart,etimes,cmd | grep -i '[h]ermes'` + `systemctl --user status
  <unit>`), then hand the user the command. A rollback that "doesn't work" is
  almost always a correct rollback whose hosting process was never restarted —
  restart it before re-reverting the files.
- **Don't reach across trees to make a test run.** If the dev copy's interpreter
  is broken but the deployed one works, the temptation is to `cp` files into the
  deployed tree and run pytest there. That makes a half-written edit live for the
  next process that starts — the exact outage described in
  `references/upgrade-deployed-instance-with-patches.md` Run the suite in the
  dev copy, or with an explicit `PYTHONPATH` pointing at dev's files; never by
  mutating the deployed tree. Note also that a deployed-tree pytest run trips the
  suite's own home-IO guard (`tests/home_io_guard.py` → "TEST BUG: file I/O
  against the REAL hermes home"), which masks a real result as a test failure.
- **Contribution purity (user rule 2026-08-17): commit messages, PR body, and
  test comments for an UPSTREAM repo must never mention our own devices
  (our own devices), the multi-agent constellation, Hermes/orchestrator
  integration, or deployment environment.** Describe only the upstream bug and
  the fix — e.g. for dsh, "the ACP stdio server leaves a lingering child when
  its transport closes" — never "our executor" / "to fix Hermes' dropped ACP".
  A foreign upstream project (like deepseek-harness) must see a self-contained,
  `a/ b/`-style bare-bug report. This applies to ALL user-visible upstream text
  (commit subject, commit body, PR description, code comments added by the
  fix). Grep the final diff for own-brand/infra terms before pushing.
- **An open PR you created may be flagged as a DUPLICATE by the triage bot — verify
  before accepting or declining.** When a bot comment says "Duplicate of #N", do NOT
  take it at face value (it can be wrong or stale). Inspect #N's CURRENT code via
  `gh pr diff N`: confirm it actually covers your fix's semantics AND the security
  boundary your fix respects. In this session's dsh/Hermes case the duplicate PR was
  a genuine superset (`_MODEL_HIDDEN_TASK_FIELDS` included the field; local/remote
  cwd resolution + fs capability), so the right move was to close my PR with a
  polite comment listing the verified overlap — NOT to argue "mine is better" when
  it wasn't. A maintainer comment asking #N to fix a security gap may already be
  satisfied by #N's current code (the comment predates later commits) — check the
  code, not the comment thread, before deciding. To confirm a PR's CONFLICTING
  state concretely (and which files), fetch its head branch and run
  `git merge-tree $(git merge-base origin/main FETCH_HEAD) origin/main FETCH_HEAD`
  — it lists `changed in both` files and `<<<<<<< .our` conflict markers without
  touching your working tree. Verify by reading the other branch's ACTUAL code
  (`gh pr diff N`, `git show branch:path`), not the triage bot's prose.
- **Do not rename deployed/local code to match an UNMERGED PR's naming.** An open
  PR (even a well-formed one) is not authoritative until merged. If your deployed
  copy uses a different identifier than the still-open upstream PR, keep yours —
  decide on aligning only after the upstream PR actually merges ("没合并不是权威").
- **Fork-vs-PR divergence audit before any release decision.** When both a fork
  branch and submitted PRs exist for the same fixes, diff all three against each
  other AND against upstream main — they drift silently in both directions: the
  PR head may carry newer rework (e.g. netlink/D-Bus rewrite) that never got
  merged back into the fork branch, while the fork branch carries plumbing-only
  commits the PRs lack. Treat whichever side has the newest content per fix as
  the merge source; never assume "our branch = what we PR'd".
- **Wire-format identifiers (protobuf field numbers, enum values, ports) must be
  allocated from CURRENT upstream main, not your base tag.** A number free at
  branch-base can be taken by the time the PR rebases (this exact class of bug:
  a new field at 67 colliding with socket_mark=67 added upstream later). Check
  `git show origin/main:<proto>` max allocated field before choosing, and prefer
  the number the PR head already settled on over a stale local one.
- **Check upstream's CONTRIBUTING.md for "we cannot accept external PRs" before
  building a PR workflow.** deepseek-harness (2026-08) explicitly states it
  cannot accept external PRs at the moment; for such repos keep the fix on your
  fork + generate a standalone `.patch` for deployment, and confirm disposal
  with the user instead of assuming a PR will be accepted.
- **Stale open PRs are worth mining BEFORE writing any code.** Search the target
  repo for existing PRs/issues matching the feature (`gh api search/issues -f
  q="repo:<o>/<r>+shortcut"`, plus symptom keywords): an abandoned-but-correct PR
  turns "implement feature X" into "cherry-pick + rebase + adapt", and its diff
  validates your architecture guess. Check `mergeable_state` — `dirty` means it
  lags the base branch and needs conflict work, not invention. Also grep the
  CURRENT codebase for the feature before claiming it absent: a half-wired
  implementation (e.g. `reportShortcutUsed()` called for a shortcut id that is
  only registered dynamically elsewhere) reads as "missing" to a manifest-only
  scan. Read call sites, not just declarations.
- GPG signing: `git rebase` re-signs every commit, which blocks on passphrase
  prompt. Use `-c commit.gpgsign=false` on the rebase command.
- `gh` account: must match the commit email, or GitHub shows the commits
  as unattributed. Check `gh auth status` before pushing.
- **Before creating branches or committing in ANY GitHub repo, resolve the
  identity triple in this order:** (1) `gh auth status` — which account is
  **Active** (this is the push credential), (2) `git config user.email` and
  `user.signingkey` — is the author identity the repo's own convention, (3)
  the key's uid vs the author email. A repo may be owned by an account that
  is *not* Active, and its per-repo identity may be a public identity with a
  dedicated signing key — neither is visible from `git config --global`.
  Committing before resolving this means re-signing later.
- **Sign with the key whose uid matches the commit's author email, and verify
  after committing** — `git log --format="%h %G? %GK %s" main..HEAD`:
  `G` = good signature. A commit signed with a key whose uid carries a
  different email than the commit author will fail downstream verification
  even when both belong to the same human. When history already carries
  mismatched signatures on unpushed commits, rewrite before pushing
  (`git reset --soft <base>` + re-commit with the right key); pushed commits
  are not rewritten (Pitfall 1: amend trap).

- **Re-signing an ENTIRE pushed history to a different key requires a full
  replay — signatures cannot be rewritten in place.** Chain the commits with
  `git rev-list --reverse <branch>` (one branch, NEVER `--all`: `--all` walks
  every ref and replays branches twice), build the new chain on an orphan root,
  and for each commit clear then re-checkout: `git rm -rq --cached . && git
  clean -fdxq && git checkout <c> -- . && git add -A && GIT_AUTHOR_DATE="$(git
  log -1 --format=%aD <c>)" git commit -S -m …`. The clear-then-checkout cycle
  is mandatory — `git checkout <c> -- .` is *additive* and will not delete files
  an earlier commit renamed, so the rebuilt tree silently loses them; verify
  every intermediate tree with `git rev-parse <old>^{tree}` vs
  `<new>^{tree}` (a `paste`/`while read` loop) before force-pushing. After the
  push, **GitHub's own API is the authority on signature validity**, not local
  `git log`: `gh api repos/<o>/<r>/commits --jq '.[] | [.sha[0:7],
  .commit.verification.verified, .commit.verification.reason] | @tsv'` must
  return `true`/`valid` for every commit — `false`/`unknown_key` means the key's
  public half is not on the signing account. Push the rewritten history with
  `--force-with-lease` after confirming there are no tags/releases pointing at
  the old SHAs (`git tag -l`, `gh api …/releases`).
- **Reading `pulls/<n>/merge` as a status endpoint is the PUT merge endpoint and
  404s on GET.** To read mergeability with a forced recompute (fresh, not cached),
  use `GET /repos/<o>/<r>/pulls/<n>?test=true`; the same `?test=true` read merges
  cleanly into the normal pull payload (`gh api 'repos/<o>/<r>/pulls/<n>?test=true'`),
  so one call yields `mergeable` + `mergeable_state` + `rebaseable` in one fresh
  reading. See `references/pr-conflict-investigation.md` for why a monitor must
  compare only bool-to-bool mergeable transitions.
- **Push 403 is a credential-helper issue, not a commit-identity issue.**
  Diagnose BOTH halves of the identity/credential split:

  1. **Which helper is answering?** `git config --get credential.helper`.
     If it is `gh auth git-credential`, git gets the token of whichever account
     is **Active** in `gh` — a `remote: Permission to Owner/repo.git denied to
     <active-account>` means that account lacks push (fix: `gh auth switch --user
     Owner` → push → switch back, verify with `gh auth status`).
  2. **But if the helper is something else — Git Credential Manager (`~/.dotnet/
     tools/git-credential-manager`), an osxkeychain, a stored PAT — `gh auth
     switch` changes NOTHING**, because git never asks `gh` for credentials. GCM
     caches its OWN account independently of `gh`'s Active flag, so the `denied to
     <account>` name will be the GCM-cached one, not the gh-Active one. The bypass
     is to override the helper chain for that one push, forcing gh's per-account
     token:

     ```bash
     git -c credential.helper= \
         -c 'credential.helper=!gh auth git-credential' \
         push --force-with-lease fork <local>:<remote-head>
     ```

     The empty `credential.helper=` clears the configured helper; the `!…` line
     supplies gh's. `gh auth token --user <Owner>` is the read-only equivalent when
     you just need to confirm the owner's token has push.

  `user.name`/`user.email` are the AUTHOR identity and are irrelevant to either
  failure — fixing them never changes the push credential. Resolve the identity
  triple (`gh auth status` Active account, repo-local `user.email`/`signingkey`,
  key uid vs author email) before committing, then confirm the PUSHER separately.
- **`git commit -c` and `-F` cannot combine.** To sign (`-S`) a commit whose message
  comes from a file (`-F <msgfile>`) under a specific identity, set the identity as
  repo-local config first (`git config user.email …`, verify it back) then
  `git commit -S -F <msgfile>` — passing `-c user.email=…` alongside `-F` aborts with
  "options '-c' and '-F' cannot be used together". Preset the GPG passphrase via the
  standalone script before committing, not inline.
- **A plain append commit needs no force push; the PR head auto-tracks the fork branch.**
  After `git push fork <branch>` (no `--force`), confirm the PR moved by reading
  `.head.sha` from the pulls API rather than trusting the push output. Force is only
  for rewritten history (amend/rebase/squash).
- **Two-sided baseline before blaming your change for red tests.** When running the suite
  against the DEPLOYED tree yields failures absent in the dev tree, check whether they are
  the home-IO guard (`TEST BUG: file I/O against the REAL hermes home`) or a missing-module
  env gap — both are environment artifacts of WHERE you ran, not regressions. Prove it by
  stashing your change and re-running the same selection on the clean deployed tree; an
  identical failure set means your patch is not implicated. Do not restart services to chase
  a test-runner error that never touches the live path.
- **Grep the final diff AND the PR body for own-brand/infra terms before pushing**
  (contribution purity): run the term list case-insensitively but read each hit — a
  substring like "Star" inside "start"/"started" is a false positive; confirm against
  the actual matching line before concluding the diff leaks. The body is the part that
  never gets re-audited: it was written once at PR creation, so it keeps a stale file
  list, superseded helper names and an older verification checklist long after the diff
  moved on — and it is where an own-tooling name (our linters, our scripts) tends to
  survive. Re-read it against `pulls/<n>/files` on every touch.
- **Two different POST endpoints for "commenting on a PR", and only one is the
  conversation box.** `POST /repos/<o>/<r>/issues/<n>/comments` posts a PR-level
  conversation comment (what you almost always want). `POST /repos/<o>/<r>/pulls/<n>/comments`
  creates an INLINE code review comment and 422s without
  `commit_id`+`path`+`line` (`No subschema in "oneOf" matched`). Retrying the wrong
  endpoint never succeeds — switch endpoints, don't retry. Replying to an existing
  inline thread is the `in_reply_to` subschema of the pulls endpoint.
- Review comments: you'll receive notifications via GitHub. Address each point
  in a separate commit or amend — see Commit Organisation above.
- Merge conflicts during upstream sync: resolve with `git mergetool` or manual
  edits. Do not force-push a broken merge.
- Test pollution: when tests pass individually but fail in batch, look for
  module-level state leaking between tests (e.g. `app.state.*` set without
  `monkeypatch`). Fix by explicitly setting the state to a known value with
  `monkeypatch.setattr(obj.state, "field", value)`.
- **A red suite is not yours until you have seen it red WITHOUT your change.**
  Before reporting a test run as broken by your fix — and before claiming green
  by quietly narrowing the file selection — stash your change and re-run the SAME
  selection on the same code. A two-sided baseline is the only honest signal:
  `git stash push -- <your files>` → re-run → compare the failure list verbatim
  → `git stash pop`. An identical failure set (often an environment gap, such as
  a missing module) means the failures are pre-existing and your change is not
  implicated; say that instead of "my change caused N failures".
- **`git stash pop` restores only what you named — check the file set before
  committing.** After the baseline pop, `git status --short` must show exactly
  the files you expect and nothing else, or you will commit a partial fix while
  believing the whole change is in the tree.
- **A stash made on a dirty tree can carry MORE than the files you named, and
  popping it onto moved code produces `UU` conflicts in files unrelated to your
  current edit.** Before any stash for a baseline comparison: confirm the tree was
  clean except your intended files (`git status --short`), stash by explicit path,
  and if pop conflicts, resolve by `git checkout HEAD -- <the already-committed
  files>` (their content lives safely in commits) rather than hand-editing markers.
  Rescue genuinely uncommitted new work to a scratch dir FIRST (`cp` the files out)
  before touching conflicted paths — a reset would otherwise discard the only copy.
- **An "existing test failure" verdict needs a same-selection baseline, not a
  remembered one.** When a test related to your change goes red, do not conclude
  "pre-existing" from a prior run's count: stash YOUR files specifically and re-run
  the identical selection now. This session mislabelled three self-inflicted
  failures as pre-existing until the fresh baseline separated them (one real
  environment gap vs three literal-string assertions broken by a wording change).
- **An attribute-fallback chain must terminate in a literal, because an
  attribute that EXISTS holding `None` is not a missing one.**
  `getattr(state, "a", None) or getattr(state, "b", "")` yields `None` — not
  `""` — when `b` is present and set to `None`, so a downstream
  `x if isinstance(x, str) else x` iterates `None` and raises `TypeError`.
  End the chain with `or ""` (or `or []`) explicitly. Two discovery channels
  worth knowing: upstream test fixtures that CLEAR a state attribute by
  assigning `None` (they never omit it), and the negative-control run of your
  own new assertion.
- **A new parallel state attribute leaks into upstream's tests.** When your PR
  adds a second attribute beside an existing one (e.g. `bound_hosts` next to
  `bound_host`) and consumers read `new or old`, upstream fixtures that
  save/restore/clear only the OLD name leave a stale value in the NEW one,
  silently enabling validation paths a test meant to disable. Audit every
  upstream fixture touching the old attribute (`git grep -n '<old_attr>' -- tests`)
  and either clear both in your production code's lifecycle or read them as one
  unit — and expect the leak to surface as a crash in an unrelated file.
- **Before declaring an interrupt/placeholder fix complete, ask which audiences it
  covers.** A change that stops the USER seeing synthetic text while the MODEL still
  reads it is half a fix and reproduces the bug through a different door (see
  `references/interrupt-transcript-rows.md`).
- **Hermes command-classifier false-positives on commit heredocs.** A
  `git commit -F - <<'MSG' ... MSG` whose message text contains words like
  `--host`, `bind`, `startup`, `serve`, `0.0.0.0` gets auto-flagged as "starts a
  long-lived server/watch process" and REFUSED (exit -1), even though it's just a
  commit. Fix: write the message to a file (`write_file /tmp/cmsg.txt`) then
  `git commit -F /tmp/cmsg.txt`. Same trap applies to any multi-line inline
  command whose payload reads like a server invocation.
- **Don't run `ruff format` over large upstream files you only lightly edited.**
  The lint CI blocks on `ruff check` only (pinned version, e.g. `ruff==0.15.10`);
  `ruff format --check` is advisory/non-blocking. **Read the ruleset from the
  tool's own config, not from `pyproject.toml`:** a repo-root `ruff.toml`
  OVERRIDES `[tool.ruff.lint]` in pyproject, so extracting `select` from pyproject
  understates what CI enforces (it can also drift: a workflow's comment may claim
  "currently PLW1514" while ruff.toml enables hundreds of codes). To decide
  whether a finding blocks the merge, run the PINNED linter with the project
  config (`uvx ruff@<pin> check <files>`) and check whether the code is
  active-or-commented in `ruff.toml` — a commented-out code (F811, F401 there)
  is not blocking but is still a real defect worth fixing.
  Running format with a DIFFERENT (latest) ruff version reflows unrelated
  upstream lines, inflating your PR diff and adding phantom conflicts. Verify the
  CI-blocking rule with the PINNED version (`uvx ruff@0.15.10 check <files>`), and
  format only your OWN brand-new whole files — never a big existing module.
