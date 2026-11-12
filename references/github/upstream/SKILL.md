---
name: upstream-contribution-github
description: Fork upstream repos, create feature branches, push, and open PRs on GitHub — full upstream contribution workflow including account switching, GPG signing, and PR monitoring.
version: 1.4.0
author: alrcatraz
tags:
  - github
  - pull-request
  - fork
  - contribution
triggers:
  - "给上游提 PR"
  - "contribute upstream"
  - "fork feature branch PR"
  - "上游贡献工作流"
  - upstream
---

# Upstream Contribution — GitHub Workflow

Contribute code to an upstream (not-your-fork) repository on GitHub.

**Making an app automatable from phone routines (Samsung Modes & Routines,
etc.):** `references/android-app-shortcuts-for-routines.md` — App Shortcuts are
the only action surface a native routine sees; covers static vs dynamic
registration, the long-press-icon verification step, the half-wired
`reportShortcutUsed` trap, and the intent→MethodChannel→Dart bridge pattern for
Flutter apps whose state lives outside the Kotlin layer.

**PR monitoring:** `references/pr-monitor.md` documents the cron monitor design
that reports *content* (author/time/body) of new comments, inline review
comments, and reviews — not just counts. Counts-only monitors silently miss
inline review comments.

**Drafting a briefing when the monitor wakes you on new PR activity:**
`references/pr-briefing-workflow.md` — enumerate ALL current comments rather
than only the pushed delta (the action-worthy item is regularly one the
baseline already absorbed, so the delta alone is a partial briefing presented as
a complete one), classify each author (a bot review with
`author_association: NONE` is advisory, not a merge gate; a self-described
automated review is not a maintainer block), read `unstable` + zero check-runs
as *no CI signal* rather than red, sort findings into
owns-it / same-family-uncovered-path / scope-too-wide / note-only, and emit the
three-part output the user expects (substance with quotes → per-item judgement
and rationale → an explicit decision list, plus a statement of whether any write
happened). It also carries the **gate-blocked fallback** (`web_extract` on the PR
page instead of `gh api`, labelled as such in the briefing), the rules for a
`State: open → merged` delta (merge SHA and our PR's own state must be verified
separately), and the post-merge follow-up list (authorship check, monitor
retirement, local patch disposition, successor-PR tracking). Use the `reviewDecision`/`reviewThreads` GraphQL query documented there to tell "no approving review has
never existed" from "an open review queue" before calling a `blocked` state
actionable, and its rule not to re-rebase a clean PR just to chase the base.
The **load-bearing check** described there covers the case a monitor can never see: a live unit
already passing a flag the unmerged PR defines — which degrades *silently*
(argparse keeps only the last value of a repeated single-valued option) rather
than failing.

**Extracting a PR branch from a diverged fork:**
`references/pr-extract-from-fork-branch.md` — fresh branch off upstream main +
per-file cherry-pick, stripping fork-only infra, neutralising build-flag defaults,
standalone-build verification (incl. the `git add -N flake.nix` trick for running a
repo devShell whose flake stays out of the commit), and re-running device acceptance
against the PR-shaped APK before pushing. Also covers the SERIES case — replaying
already-reviewed commits with `git cherry-pick` (expect conflicts; merge-both
resolution policy, re-run each commit's tests before `--continue`, prerequisite
commits surfacing as test failures), the `--amend -S --no-edit` message-reversion
desensitisation trap, keeping local A/B/C fix labels OUT of the PR body, and
delta re-review fail-closed (a fix round's own incompleteness must be re-fixed and
re-reviewed, never self-certified).

**Landing a local patch on a LIVE host (the dangerous variant):**
`references/upgrade-deployed-instance-with-patches.md` — read it in full BEFORE
editing any deployed tree. It is the difference between a working patch and an
outage; every rule there (7a never test in the deployed tree, 7b verify the
`from X import Y` form across the whole symbol set, 7c restarting the unit you are
running inside kills your own session, 7d two trees can share `sys.path`,
7e a rollback is not complete until the hosting process restarts, 7f prove the LIVE
   process reloaded, 7g multiple serving units may read different trees — land the
   patch in each) was paid for with a production outage. The short form:

1. Dev copy: apply, run the suite, verify imports. Never `cp` between trees to
get a test to run.
2. Deployed copy: stop the services, apply, clear `__pycache__`, assert the
   cross-module symbol identity, start.
3. Hand the user the restart command — never run it from a tool call when that
   unit hosts your session.

**Fixing Hermes's own interrupt / synthetic-transcript behaviour** (the agent
answers with a canned phrase, or a placeholder leaks to the user or the model):
`references/interrupt-transcript-rows.md` — `display_kind="hidden"` hides a row from
the UI but NOT from the provider (its `api_content` is substituted back into
`content` every call), which is how a short neutral-sounding phrase becomes an echo
loop; density inside the send window decides whether a given session imitates it;
and you cannot freely DROP such rows because removal can recreate the `tool → user`
alternation violation the row existed to prevent — keep-and-rewrite instead.

**Reading your OWN private repos non-destructively:**
`references/read-own-private-repos-via-api.md` — per-account token via
`gh auth token --user <Owner>` (no `gh auth switch`), recursive tree API instead
of cloning engine-bloat repos, noise-path filtering, and the space-in-filename
URL-encoding gotcha.

**Review fix → push → reply loop:** `references/review-fix-push-reply.md` covers
addressing review comments on an open PR: identifying the PR's actual head
branch, pushing via refspec so the PR auto-updates, verifying via the GitHub
API, and replying. Key lessons: PRs track the fork's head branch, NOT your local
branch name — push `local-branch:pr-head-branch` explicitly. **Load this file
BEFORE pushing review fixes:** force is the exception (only for rewritten
history — amend/rebase/squash), a plain append commit needs no force, and every
strengthened assertion must be proven RED without the fix (see its Pitfalls,
which also covers the stash-and-forget trap and the false-green assertion shape).
Force is only needed when history was rewritten (amend/rebase), so prefer a
follow-up commit; and every fix's regression test must be proven to FAIL without
the fix (revert → run the one test → expect red), since an assertion anchored on
the input just consumed can be false-green.

**Upgrading a deployed instance that carries a local patch stack:**
`references/upgrade-deployed-instance-with-patches.md` — the execution recipe for
landing upstream fixes on a host whose local patches are partly UNMERGED PRs:
patch inventory + A/B/C/D classification, `sqlite3 .backup()` (never `cp`) DB
snapshot, `git merge --ff-only` in preference to the bundled updater, re-applying
from the stash with the expected "most clean, one hot file `UU`" split, the
graft recipe for the neighbour-renovation conflict, and effect-based verification
after restart — including the **post-restart completion-loop trap**: a manual
git upgrade still runs the product's own update-completion pass on first service
start (sentinel file `~/.hermes/.hermes-update-in-progress`), and asserting
`is-active` during that pass is premature — wait for the LISTENER (`ss -ltn`)
plus the `HERMES_BACKEND_READY` journal line instead of restarting in a loop.
That file covers landing a **NEW** patch on a live host: test in the dev copy only
(never edit the deployed tree to test), verify with a `from X import Y` statement
rather than `py_compile`/grep, never restart the unit that serves your own
session, expect a workspace snapshot second tree on `sys.path`, and remember a
rollback is not complete until the hosting process restarts. When the install has
BOTH a serve unit (repo tree) and a gateway unit running an `installs/<id>/
environments/<hash>/workspace/` snapshot, the patch must be copied into the
snapshot too (it is NOT a symlink to the repo) — prove which tree each PID uses
via `/proc/<pid>/cmdline`'s `sys.path.insert` before concluding coverage.

**Multi-PR review + upstream-main-moved repair:**
`references/multi-pr-review-and-rebase-repair.md` covers when a PR is LEFT
CONFLICTING by upstream advancing: read owner review THEN read upstream's current
code, orchestrator-vs-executor split (never patch implementation code yourself —
delegate to opencode; POINT the executor at the brief file, don't inline a 10KB
brief into the prompt — that triggers an opencode `UnknownError`), rebase keeping
both .gitignore sides, the 2-arg
`_try_register` + `_OPTIONAL_LANG_SUPPORT` registration fix in shared files,
scoping entry-rule `file_pattern` to a language's extensions (e.g. TS
`**/*.*[tjs][sx]`), proving pre-existing test failures on a clean main worktree,
running the FULL suite after a keep-both merge (a stray orphan rule dict can
break sibling-language tests while your PR's own go green),
`--force-with-lease` push, batching the shared repair across sibling PRs, and
not touching already-merged/absorbed branches. **Run the re-graft integrity audit
after any cherry-pick** onto a refactored main: imports that
survived while their call sites vanished, functions upstream MOVED to a file
absent from your diff (silent feature loss, zero conflicts), conflict sides that
are each a `NameError` once the enclosing signature changed, two independent
guards merged by picking one, pre-resolving a value the library already reads
back, new state attributes colliding with upstream fixture hygiene, and
negative controls that must run through the sanctioned runner. Also covers PR
monitor script updates (add new PR entries to `pr-monitor.py`, remove merged
ones), GPG passphrase cache expiry mid-session (use preset script, never
`gpgconf --kill`), and stale AGENTS.md misleading executors.

**Graphlint C++ backend patterns:**
`references/graphlint-cpp-backend-patterns.md` covers IncludeInfo dataclass pattern
(shared across backends, framework expects `include_path` attribute not dict),
test-file detection tiers (exact basename → suffix endswith with extension → prefix
→ dir pattern, no config dependency for core behavior), destructor special-name
handling (pattern-aware startswith "~" not exact membership match), out-of-class
member definition resolution (parse `::` scope, attach method to class qname not
module scope), Approach A receiver-type resolution wiring in `_visit_call`,
`.h` extension-split routing between separate C/C++ adapters (content-sniff in
`Indexer._parse_batch` — Approach B; ensure BOTH backends keep working), the
unified C-family routing/identity fix for cross-file headers (round-3), cross-file
constructor recognition via a graph-level qname predicate (not adapter
`is_special_name`), the verify-a-write-landed-in-the-real-fork-before-dispatch
pitfall, and — from round 3 — the orchestrator-finishes-the-tail guidance: strip
executor `print("DEBUG ...")` residue from implementation files, strengthen
owner-regex tests yourself when test-only, and stop re-dispatching an executor
that keeps mis-typing the HOME path (even with an absolute `--dir` the executor's
in-reasoning reads can drop an 'r' → external_directory rejects).

**No-shell-IO reviews (round 2 — non-systemd Linux):**
`references/rust-no-shell-io-patterns.md` covers replacing shell-out with
netlink/D-Bus; its "Round 2" section covers the follow-up pushback
"不是所有 linux 都有 systemd" and the resolv.conf fallback chain.

## Where each subject lives

| Subject | File |
|:--|:--|
| Fork creation and the two approval gates that precede any edit | `fork-and-gates.md` |
| Account and GPG setup, branch setup, preparing the change | `pr-workflow.md` |
| Working the fork day to day | `daily-development.md` |
| Code review, push, opening the PR, its body | `pr-publication.md` |
| A PR parked by upstream god-file decomposition | `parked-pr-handling.md` |
| Failure modes of upstream contribution | `pitfalls.md` |

`references/INDEX.md` registers the case files under `references/`;
`scripts/` holds the helper scripts these procedures call.
