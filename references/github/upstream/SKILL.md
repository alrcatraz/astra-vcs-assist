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
retirement, local patch disposition, successor-PR tracking). Use its §4
`reviewDecision`/`reviewThreads` GraphQL query to tell "no approving review has
ever existed" from "an open review queue" before calling a `blocked` state
actionable, and its §3 rule not to re-rebase a clean PR just to chase the base.
§5's **load-bearing check** covers the case a monitor can never see: a live unit
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
`references/upgrade-deployed-instance-with-patches.md` §7 — read §7 in full BEFORE
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
Its §7 covers landing a **NEW** patch on a live host: test in the dev copy only
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
not touching already-merged/absorbed branches. **§9 is the re-graft integrity
audit** — read it after any cherry-pick onto a refactored main: imports that
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
`references/tailscale-linux-dns-design.md` is the condensed Tailscale net/dns
architecture (mode detection, resolved probing, direct-mode backup/ownership/
atomic-write) that informed that fallback — read it before designing a D-Bus +
resolv.conf fallback for TUN/VPN DNS config.

## Pre-requisites

- `gh` CLI installed and authenticated to at least one account
- GPG key configured for commit signing
- Local clone of the upstream repo

## Creating the fork itself (GitHub)

`gh repo create --fork` / `gh repo fork` flag combinations often just print help.
Use the REST API instead — it is one call and preserves the native fork link
(which keeps GitHub's "Sync fork" button working for future upstream pulls):

```bash
curl -s -X POST -H "Authorization: Bearer $(gh auth token)" \
  https://api.github.com/repos/<owner>/<repo>/forks -d '{}'   # → full_name appears once forked
```

Two mechanics that bite:

- **Forking is asynchronous.** The first GET/PATCH right after the POST can 404
  or return partial state. Poll `GET /repos/<user>/<repo>` until `full_name`
  resolves, then continue.
- **Renaming a repo makes its API resource redirect (301 `Moved Permanently`).**
  Subsequent `/repos/<old-name>` calls fail; re-target by numeric id, which never
  changes: `PATCH https://api.github.com/repositories/<repo-id>` (the id comes
  from the original create/fork response or a fresh GET). Set `private:true` in
  the same PATCH as the rename when both are wanted.

## Step -1 — Get the fix approved as a DISCRETE list before editing (gate)

**Approval to "go ahead" approves the plan you showed, not the plan you later
invent.** Diagnosing and fixing inside one turn is the failure this gate stops:
you investigate, notice a second thing that must change, change it, then notice
the first change was wrong — and the user has been charged a rollback window for
every step because none of them was approved.

Hard rules:

1. **Enumerate the exact files you will touch and what changes in each, and show
   that list before the first `patch`/`write_file`.** The user's rule is verbatim:
   *"改法我列出来，你点头我再动手"* — the 改法 IS a file-by-file list, not a
   direction. A plan that names "fix the interrupt reporting" authorises nothing
   until it names `agent/<file>.py: <what changes>`.
2. **A file not on the approved list is not approved.** Discovering during
   implementation that a third file also needs edits means STOP and re-present —
   not "this one is obviously part of the same fix". Scope creep inside a task is
   still scope creep.
3. **Never mix diagnosis and mutation in one stretch.** Complete the read-only
   phase and report it; the write phase starts after approval. If mid-write you
   find the diagnosis was wrong, stop and report the correction — do not silently
   reverse the previous edit and keep going.
4. **Keep an undo point before the first edit** (`git diff > backup.patch` into a
   scratch dir alongside `HEAD.txt`), so a rejected plan costs one `git checkout`
   rather than an archaeology session.

**Honesty when you have already broken this.** If you edited beyond the approved
list, say so in the same turn, name the extra file, and offer the rollback. Do not
fold the extra edit into the narrative as though it had been planned.

### The task list is the USER'S SYMPTOM LIST, not your latest diagnostic thread

A long diagnosis drifts: you start on symptom 1, rabbit-hole into a mechanism,
and several compactions later you are optimising a sub-question nobody reported.
The user then has to re-supply the task ("主要任务应该还是两个 bug 的修复" / "刚才你不是
还修了 X？"). Two habits prevent it:

1. **Anchor the task list on the user's own words.** When a user reports problems,
   write them down as a numbered list of *their* symptoms ("A: the message appears
   and the agent stops", "B: "progress is behind" and my send fails") and treat THAT
   as the definition of done. Sub-questions you discover are work items under an
   entry — never a replacement for it.
2. **After every compaction resume, and after every multi-turn diagnostic detour,
   restate the list and where each item stands** (not started / root cause known /
   fix applied / verified). Do this unprompted; the user should never have to
   reconstruct what you are supposed to be doing.
3. **"Did I already fix that?" is answered from the repo, not from memory.** When
   the user asks whether a fix went in, run the two-command check before answering:
   `git log --since=<window> --oneline --all` plus
   `git status --short`. If the answer is in the conversation rather than in git,
   the honest reply is "no — it was only diagnosed; no code changed." A diagnosis
   plus a written plan is NOT a fix, and reporting it as one is the
   overclaiming failure this skill already warns about.
4. **Prefer finishing one item end-to-end over advancing several.** When several
   symptoms are open, closing one (fix → test → review → push) reduces the
   mental load more than partial progress on each — and the user may say so
   outright ("你先修一个好了也省去一些上下文记忆负担").

## Step 0 — Prove the bug EXISTS before writing any fix (gate)

Everything in §3 assumes there is a real defect. **Establishing that is a
separate, prior step, and skipping it is the most expensive failure mode in this
skill** — you can spend a whole session on a rigorous diagnosis of a
non-existent bug and only discover it when the "fix" has nothing to change.

A defect is **proven** only when you have a **failing observation from the live
system**: a reproduced error, a log line whose owner-accounting shows the
user-visible actor was actually harmed, or a test that goes RED against unmodified
code. Anything short of that is a **hypothesis**, and a hypothesis must never
grow a patch, a branch, or a PR.

### Before the diagnosis: is the fix ALREADY upstream? (cheapest check, do it first)

When the bug is a fresh report on a DEPLOYED instance — especially one whose host
carries a local patch stack — check upstream BEFORE reading any implementation
code. A deployed copy can sit thousands of commits behind upstream while its local
patches are still-unmerged PRs, so the "bug" is frequently already fixed and the
task collapses from *author a patch* into *upgrade and re-apply the local set*.

```bash
cd <deployed-copy> && git fetch origin main
git rev-list --count HEAD..origin/main            # distance to upstream
git log --oneline origin/main --since=<when> -- <file area in question>
```

Search upstream history by FILE PATH and match the user's symptom words against
the commit subjects before reading implementation code — a commit subject like
"graft this window's own turn residue instead of refusing the send" identifies the
bug faster than any amount of local reading.

**Two traps that make an already-merged fix look absent:**

- **The symbol was renamed by a refactor.** Grepping for the function you expected
  (`refreshIfTranscriptStale`) returns nothing after upstream renames it
  (`transcriptRefreshIfBehind`). Confirm by LINEAGE, not by name:
  `git merge-base --is-ancestor <fix-sha> HEAD && echo "fix IS in HEAD"` plus
  `grep -n 'export function' <file>` for the current surface.
- **A green self-authored probe is not evidence the bug is unreproducible.** Probes
  model the mechanism you guessed; once several constructed shapes plus a real-data
  replay all converge, the ceiling of that probe is reached. That is the signal to
  change evidence surface or check upstream — not to build shape N+1.

Two failure shapes this gate exists to stop:

- **Symptom-class confusion.** A report like "the agent stops mid-task" is a
  behaviour claim. A grep hit for a plausible-looking placeholder string is a
  display-layer finding. They can share wording and still be different defects —
  writing the display-layer fix answers a question nobody asked, and every probe
you built for it is void. Write the symptom class down first
  (display / behaviour / admission) and make it match the user's words.
- **Shared-identifier misattribution.** One process often has several actors
  running under the SAME session/task id (a fork reusing the parent's session id
  for cache parity, a child inheriting a task id). Its log lines then look
  exactly like the parent's being killed. Filter the events by their **owner
  field** (`origin=`, thread name, distinct budget counters) and count them
  separately before concluding anything: **all events belonging to the internal
  actor means this is designed behaviour, not a defect.**

When the gate fails, the correct output of the session is an honest **"not
reproduced"** report (what was tested, what converged, what was ruled out) — NOT
a speculative PR. Then ask for the one fact that would separate the remaining
branches (wall-clock time of the occurrence, the presentation shape, the exact
session) instead of constructing another shape.

Corollary for probe-based diagnosis: **self-authored probes going green tells you
the function is correct on healthy input, not that the bug is absent.** Once
several constructed shapes AND a real-data replay all converge, you have hit the
ceiling of what that probe can prove — the defect (if any) lives in a caller, a
timing window, or a state source you never modelled. Change the evidence surface
(live log, persisted rows, event ordering) or go back to the user; do not add
shape N+1.

### Do not carry a fix you have not proven into a patch

A diagnosis plus a written plan is NOT a fix. When the user asks "did you already
fix that?", answer from the REPO, never from the conversation: `git log --since=<window>
--oneline --all` and `git status --short`. If nothing landed, say so plainly —
reporting a diagnosis as a completed fix is the overclaiming failure this skill
exists to stop. Same rule for the reverse: never let a hypothesis that keeps getting
falsified (each probe converging, each layer ruled out) grow a branch or a PR —
stop and report the dead end.

## Workflow

### 1. Account Selection & GPG Setup

> **Per-project active account — switch, don't assume one default.** This host
> carries multiple `gh` accounts (e.g. `alrcatraz` and `Zhen-LinHuo`) and the
> user's rule is that **each project picks its own default** — there is no single
> global Active account. For NousResearch/hermes-agent upstream PRs the default
> is `alrcatraz` (fork `alrcatraz/hermes-agent`; commits, pushes, and replies all
> go through it). Pick by project, then confirm before acting:
> `gh auth status` → `gh auth switch --user <account>` if the wrong one is Active.
> **The Active flag reverts without warning between tool calls** — a `gh auth
> switch` done earlier in a session is not durable; some gh invocations or OS
> keychain refreshes reset it. **Re-check `gh api user --jq .login` before EVERY write
> operation** (PATCH, POST comment, push, `gh pr create`), not just at session start —
> including *comments*: posting an issue/PR reply under the wrong account splits one
> person's thread into two identities, and repairing it needs the WRONG account again
> (a non-admin can only delete their own comment), so the fix costs two extra
> switches and leaves a deletion hole if anyone read it in between. Prefer
> `gh api user --jq .login` as the authority — `gh auth status` can show a stale
> Active flag (it showed `Zhen-LinHuo / Active account: true` minutes after a
> successful alrcatraz push). The cost is asymmetric: a read succeeds on EITHER
> account, so "the GET worked" never proves your identity — only an
> author-attributed write (comment, push, edit) exposes it.
> A wrong Active account on a write surfaces as **404 on PATCH that succeeds on GET**
> (GitHub returns 404 rather than 403 for insufficient write permission on the
> pulls/issues endpoints), so a PATCH-404 after a working GET means the account
> switched, not that the URL is wrong. Fix: `gh auth switch -u <owner>` →
> verify `gh api user --jq .login` → retry. Pushes additionally need the
> credential-helper override if GCM is the configured helper (see the Push 403
> pitfall below).
> The Active account is the push credential AND (via `gh auth git-credential`)
> the author-attribution source, so setting it once per project avoids both the
> 403 and the unattributed-commit failures below.

> **Sign by default — this project's own commits are always signed.** Our
> contribution commits on NousResearch/hermes-agent carry GPG signatures
> (verify: `git log --format='%h %G?' <our-branch>` → `E`/`G`, never `N`), so
> the standing rule is the normal `commit.gpgsign true` + `user.signingkey`
> path — see skill `astra-vcs-assist` → `references/gpg/key-lifecycle/` (preset the passphrase first with
> `~/.hermes/scripts/preset_gpg_signing.sh`; it ends in a real sign test, so
> `SIGN_OK` means signing works and there is nothing to debug).
>
> `%G?` showing `E` means the signature exists but the key is not in the LOCAL
> keyring — that is expected on a machine that verifies-but-does-not-own the
> key, and it is NOT "unsigned". Do not misread `E` as `N`.
>
> Measure the upstream repo's own convention separately if you ever need to
> (e.g. `git log <base> --format='%h %G? %s'`); whatever the maintainers do,
> our contributions stay signed for attribution.

```bash
# List available gh accounts
gh auth status

# Switch to the account you'll open the PR from
gh auth switch --user alrcatraz

# If the clone is fresh, configure per-repo identity
# ⚠️ CRITICAL: git user.email MUST match the GitHub account's primary email.
# GitHub uses the commit email to associate commits with an account, NOT the
# author name. Using zhenlinhuo503@outlook.com makes GitHub show Zhen-LinHuo
# instead of alrcatraz on the PR page.
git config user.name "alrcatraz"
git config user.email "alrcatraz@gmx.com"
git config user.signingkey B01ECDF27D2D156D
git config commit.gpgsign true
```

If GPG signing fails with a timeout on gpg 2.5.20+ (openSUSE), the passphrase
may not be cached. Retrieve it from `~/.hermes/.env` (`GPG_Key_Alrcatraz`) and
use the wrapper approach:

```bash
PASSPHRASE=$(grep GPG_Key_Alrcatraz ~/.hermes/.env | cut -d= -f2)
cat > /tmp/gpg-sign.sh << EOGPG
#!/bin/bash
exec gpg --batch --pinentry-mode loopback --passphrase "$PASSPHRASE" "$@"
EOGPG
chmod +x /tmp/gpg-sign.sh
GIT_SSH_COMMAND= git config gpg.program /tmp/gpg-sign.sh
```

**Faster alternative — preset the passphrase into gpg-agent** (works for plain
`git commit -S` without wrapper scripts; verified in the field):

```bash
# 1. Get the keygrip of the signing key
gpg --with-keygrip --list-secret-keys B01ECDF27D2D156D | grep 'Keygrip = ' | awk '{print $3}'
# 2. Preset the passphrase (binary NOT in PATH on openSUSE — use full path)
echo "$PASSPHRASE" | /usr/libexec/gpg-preset-passphrase --preset <KEYGRIP_HEX>
# 3. Now `git commit -S` succeeds in the same gpg-agent session (no tty needed)
```

`gpg-preset-passphrase` lives at `/usr/libexec/gpg-preset-passphrase` on
openSUSE (find it: `find /usr -name 'gpg-preset-passphrase'`; could also be
`/usr/lib64/gnupg/`). The preset persists for the gpg-agent cache lifetime
(default ttl), so subsequent commits in the same session don't re-prompt.

> **Hermes terminal-guard crash on passphrase strings.** Inside Hermes, running a
> bash command or script that *contains the passphrase/$gpg-preset-passphrase
> invocation inline* can trip the terminal lifecycle guard, which crashes with
> `embedded null byte` (a guard bug when it tries to re-parse the command it
> thinks is dangerous). Workaround: put the preset in a standalone script
> (`~/.hermes/scripts/preset_gpg_signing.sh`) and run that, or run the preset
> via a small Python `subprocess` through `execute_code`. The preset itself is
> safe — only the inline bash form trips the guard. Also: **never run
> `gpgconf --kill gpg-agent` to debug signing** — it clears the cached
> passphrase and forces a re-preset (skill `astra-vcs-assist` → `references/gpg/key-lifecycle/` Pitfall 0).

### GPG Pitfall: git rebase
`git rebase` replays commits, each of which is re-signed. If the GPG passphrase isn't
cached in the agent (gpg-agent.conf), rebase will hang waiting for the passphrase and
time out after ~30 s per commit. Workarounds (in order of reliability):

1. **Preferred: disable signing for the rebase.** Use `-c commit.gpgsign=false`:
   ```bash
   git -c commit.gpgsign=false rebase origin/main
   ```
2. **Cache the passphrase.** If you installed a local gpg-agent.conf that auto-presets
   the passphrase (common on new machines), run `gpg-connect-agent reloadagent /bye`
   before the rebase.
3. **Wrap gpg with passphrase injection** (see GPG setup section above) — fragile if
   the user's machine doesn't have the same env variable.

### 2. Branch Setup

```bash
# Set up dual remotes (fork + upstream)
git remote add fork git@github.com:alrcatraz/hermes-agent.git
git remote add upstream git@github.com:NousResearch/hermes-agent.git

# Create feature branch from upstream main
git fetch upstream main
git checkout -b feat/my-feature upstream/main

# Push to fork
git push -u fork feat/my-feature
```

### 3. Before Making Changes

- **Read upstream docs before writing fixes — but when the project lives on
  GitLab, use its REST API, not just the web UI.** The user's stated rule
  (2026-08-17): **"看上游有没有修复或 Issue，没有就 PR + 补丁"** — before writing
  any fix, check upstream for BOTH an existing fix (open/merged PR) AND an open
  Issue describing the bug:
- Check if a PR already exists for this (`gh pr list`)
- **GitLab-hosted upstreams (freedesktop etc.): the web UI blocks anonymous
  browsing ("influx of spam" gate), and general web search may be down. Use the
  unauthenticated issues API instead** (verified 2026-09-04 for NetworkManager
  triage): `curl -sk "https://gitlab.freedesktop.org/api/v4/projects/<group>%2F<project>/issues?search=<kw>&state=all&per_page=20"`
  — run several narrow keyword queries (symptom words, component names,
  version numbers), filter titles, then fetch one issue's full description via
  `/issues/<iid>` before judging relevance. This found #1984/#1711/#1004 in
  minutes when SearXNG was 401. GitHub equivalent: `gh search issues` /
  `gh api`.
- **Query open Issues that may describe the exact bug** — a faithful bug report
  often lives as an open Issue WHILE a fix PR is already open against it
  (e.g. `gh search issues --repo <repo> "keyword" --state open`; then inspect
  cross-referenced PRs on the Issue via `gh api repos/<r>/issues/<n>/timeline
  --jq '[.[] | select(.event=="cross-referenced") | .source.issue.number]'`).
- Read the upstream code to understand conventions
- Base all work on `origin/main` (fork's main) which is synced from upstream

**Branch on what you find upstream — this decides PR+patch vs just-patch:**

| Upstream state | Action |
|:--|:--|
| **No Issue, no PR** for the bug | You own it: write the fix → **PR + local patch** (patch so already-deployed instances get it before merge). |
| **Open Issue, no PR** | Reproduce/confirm the bug, then **PR (Fixes #N) + patch** — the PR closes the issue. |
| **Open PR already fixing it** | **Do NOT repeat the PR.** Review that PR's diff; take/adapt ITS patch for deployed instances to get the fix live before merge. Track it in PR monitoring to follow the merge. Only re-PR if the existing PR is stale/mergeable:false AND covers a different layer than your fix. |
| **Fix merged upstream** | Nothing to PR; sync upstream and drop your local patch. |

- When an existing PR is `mergeable:false` (conflicts with main) or touches many
  unrelated files, prefer extracting ONLY the minimal diff you need (e.g.
  `gh api .../pulls/N/files --jq '.[].filename'` to see scope; apply just the
  hunk you need) rather than bringing the whole PR into your deployment.
- Deepen: a reported bug often has TWO layers — the forwarding gap (param never
  passed down) and the actual missing feature (e.g. a param exists but is not
  independently usable). Upstream may fix only layer 1; if you need layer 2,
  that's a SEPARATE PR even when an open PR covers layer 1.

### 4. Daily Development

Make changes on the feature branch.

```bash
git checkout feat/my-feature
# Make changes, test them
```

#### 4.0. Test-Safety Gate on a SHARED / PRODUCTION machine (⚠️ CRITICAL)

"Development copy ≠ safe to run the suite" is WRONG when the dev clone lives on
the **same host that runs production services**. The isolation that matters is
not just *which repo you edit* but *what your tests touch at runtime*. A test
suite that spawns real server processes (`start_server`, uvicorn, a subprocess
`hermes serve`) can disrupt live production even with an ephemeral port + temp
`HERMES_HOME`: it raises host load, opens listeners, and — worst — may invoke
orphan-reaping logic (e.g. `start_server` calling
`_reap_orphaned_desktop_local_serves()`) that scans/kills host-level processes.

This session: running `scripts/run_tests.sh tests/hermes_cli/` (FULL suite) on
a host that runs production `hermes-serve.service` (:9901) +
`hermes-gateway.service` as **user systemd units** — caused the user's desktop
client to report a backend restart. The production PIDs were NOT actually
restarted (verified three ways), but the WebSocket connection blipped. Lesson:
the incident was real even though my "processes are fine" evidence was also
true; do not argue with the user's observed symptom.

Gate before running ANY suite that spawns servers, on a box that hosts prod:
1. **Prefer targeted runs over full suites.** Run only the specific test files
   your change affects (`run_tests.sh path/to/test_x.py`), never `tests/<big-dir>/`
   wholesale, unless you've confirmed no test in scope spawns/talks to prod.
2. **Know how prod runs here.** Check `systemctl --user list-units | grep -iE
   'serve|gateway'` AND `ps aux | grep -iE 'serve|gateway'`. Production hermes
   may be a *user* systemd unit or a bare process under a DIFFERENT install dir
   (`~/.hermes/hermes-agent/`), not the dev clone you're editing.
3. **If a disruption is suspected, investigate to a mechanism — don't lead with
   "my commands were read-only".** Gather: `systemctl --user show <unit>
   -p NRestarts -p ActiveEnterTimestamp`, `ps -o pid,lstart,etimes` (kernel-level
   age is unfakeable — a restart resets etimes), `/proc/<pid>/stat` field 22
   (starttime jiffies). Cross-check all three. Then explain the *actual* channel
   (WS reconnect under load, orphan-reaper, shared port probe) rather than
   dismissing the user's observation.
4. When in doubt about blast radius, ASK before running the full suite on a
   prod-hosting machine, or run e2e-spawning tests only in a container / other
   host and let upstream CI cover the rest.

#### 4.1. Commit Organisation (⚠️ CRITICAL PREFERENCE)

**NEVER** group commits by external category such as "review feedback", "review fixes",
"address review comments", or "PR review" — even when the changes were triggered by
a code review. The user explicitly rejects this pattern. Every commit must carry a
concise, self-contained description of the *logical change*, not its *origin*.

✔ Good — grouped by function:
```
feat(serve): support multiple --host arguments for dual-stack binding
fix(serve): store all bound hosts as frozenset for middleware validation
fix(serve): compute auth_required from all bound hosts
fix(serve): reuse OS-assigned ephemeral port across all listeners
fix(serve): validate all bound hosts in WebSocket client/auth guards
test(serve): update tests for multi-host signature and fix test pollution
```

✗ Bad — grouped by trigger:
```
feat(serve): support multiple --host arguments for dual-stack binding
fix: address review feedback — auth over all hosts, bound_hosts as frozenset, port-0 reuse
```

When changes span the same file across multiple logical fixes, split them into
separate commits using this workflow:

1. Save the full working-state diff: `git diff > /tmp/full.patch`
2. `git checkout -- <file>` to restore HEAD
3. For each logical change, apply only that change using targeted edits,
   then `git add` + `git commit` with a function-level message
4. Commit test file changes last

Alternatively, use `git add -p` (interactive hunk staging) or `git commit --fixup
<target-sha>` followed by `git rebase -i --autosquash`.

**Splitting one file's hunks across commits from a saved patch (non-interactive).**
When the logical fixes interleave in the same file, `git add -p` is awkward from a
tool call. The reliable recipe is: save the full diff, capture just the hunk you
want as its own patch file, and stage it with `--cached`:

```bash
git diff > /tmp/all.patch                 # 1. the whole working-state diff
git checkout -- .                          # 2. clean tree
# 3. hand-write /tmp/hunk1.patch — a minimal diff with the REAL hunk header
#    (@@ -974,7 +974,12 @@) and exact context lines, for ONE logical change
git apply --cached /tmp/hunk1.patch        # 4. stage only that hunk
git commit -S -F /tmp/cmsg1.txt            # 5. commit just that change
git diff                                   # 6. the remainder is still unstaged
```

Two traps in this recipe, both of which silently lose work:

- **`git apply --include=<file>` on a patch whose file is ALREADY applied fails
  with `patch does not apply` — and the failure is easy to miss inside a loop.**
  Scope each re-apply to the files you actually cleared. Verify by re-reading
  `git status --short` after every apply, not by trusting the exit code of a
  chained command.
- **A whole-patch `git apply` after a partial commit fails**, because the
  committed hunks no longer match. Re-apply the remaining files individually
  (`git apply --include=<path> /tmp/all.patch` per surviving file) rather than
  re-running the whole patch.

Run tests after each commit to catch breakage early. Run the full test suite
on the final commit before pushing.

#### 4.1a. Test runner: use `scripts/run_tests.sh`, never `.venv/bin/pytest` directly

On the hermes-agent repo, the canonical test entry point is
`scripts/run_tests.sh <path/to/test_file.py>` — NOT `.venv/bin/python -m pytest`.
The `.venv` may have a stale or missing compiled extension (e.g.
`pydantic_core._pydantic_core` absent after a Python version bump) that makes
every test fail at **import time** with `ModuleNotFoundError` or a module-level
`SystemExit("Web UI requires fastapi and uvicorn")` from the target module —
none of which are assertion failures. Direct `.venv/bin/pytest` runs show
`17 failed / 11 passed` when the real state is `0 tested, environment broken`.

`scripts/run_tests.sh` detects the broken env, reinstalls dependencies
(hash-verified via `pm` + `uv.lock`), spawns per-file isolated subprocesses
(fresh interpreter per test file, `TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0`), and
returns a trustworthy green/red. One invocation covers a single file or a whole
directory:

```bash
cd <repo> && scripts/run_tests.sh tests/hermes_cli/test_web_serve_bind.py -q
# → run_tests_parallel.py: per-file subprocess, summarized pass/fail
```

If a direct pytest run reports failures, check whether ANY are import/`
SystemExit` errors before attributing them to your change — those are env
artefacts, not regressions. Re-run through `run_tests.sh` before concluding
either green or red.

**Negative controls go through the same runner.** Proving a new assertion is RED
without the fix requires re-running that one test id, and the reflex is to call
the test-env venv's `python -m pytest <id>` because it is faster. Don't: that
path lacks the runner's clean env, so `tests/home_io_guard.py` fires
(`TEST BUG: file I/O against the REAL hermes home`) and the test "fails" for the
wrong reason — a FALSE red that looks like a successful negative control. Always
`scripts/run_tests.sh '<file>::<class>::<test>'`.

**A per-file timeout is a budget artifact, not a regression.** The parallel
runner caps each test FILE (`_DEFAULT_FILE_TIMEOUT_SECONDS`, overridable with
`HERMES_TEST_FILE_TIMEOUT=900`) and reports `no tests ran … FAILED: 1 of N files`
with 0 collected for a large file. Before attributing that to your change,
baseline the same file on a clean `upstream/main` worktree (it often exceeds the
cap there too, especially on a weak-CPU host); if it does, re-run your tree with
a raised `HERMES_TEST_FILE_TIMEOUT` to get a real verdict, and report the file as
"budget, not failure" with the numbers from the raised-budget run.

#### 4.2. Keeping Branch in Sync

```bash
# Before pushing, rebase onto latest upstream main
git fetch origin main
git rebase origin/main     # add -c commit.gpgsign=false unless the passphrase is preset
```

**Rebase to fix a conflict, never to chase the base.** While a PR sits clean and
blocked on review, an old base is not a defect: every force-push resets the
reviewer's accumulated diff context and marks existing inline threads
`isOutdated`, so rebasing to look current actively reduces the chance of getting
the review you are waiting for. A flip to `dirty` is the trigger; before that,
leave the head alone. Corollary for a PR pushed many times with zero human
review — the next briefing item is an escalation question to a human maintainer,
not another rebase. (Same rule, plus the reads that prove the feature is still
unique, in `references/pr-briefing-workflow.md` §3.)

### 5. Code Review Before Push

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

### 7. Post-PR Monitoring

```bash
# Check PR status
gh pr view --repo NousResearch/hermes-agent/<number>

# Check mergeability
gh pr view <number> --json mergeable,mergeableState
```

Use `scripts/pr-monitor.py` for automated monitoring.

## Handling a PR parked by upstream god-file decomposition

When an open PR goes quiet with no conflicts initially, then later flips to
`mergeable: false`, the usual cause is upstream decomposing the giant file you
touched ("god-file shard" campaigns). Investigate via
`references/pr-conflict-investigation.md`; the decision steps specific to this
situation are below (mirrored in full detail in
`references/pr-conflict-investigation.md` §5–§7).

### A. Is your feature SUPERSEDED or still unique? (do this before re-implementing)

A conflict against a heavily-refactored file can *look* like "upstream already
did my work." Verify empirically before either closing the PR or rewriting it:

```bash
# Does upstream's current code actually contain your feature's semantics?
git show origin/main:path/to/file.py | grep -n "your_key_function_or_kwarg"
# e.g. for multi-host bind: is `--host` still single-value? does start_server
# take host:str or hosts:list? are your helpers (_create_server_sockets) absent?
git log --oneline origin/main --grep="dual.stack\|multi.host\|<your feature>" -i
```

Two distinct outcomes with opposite actions:
- **Superseded** (upstream implemented the same capability, often more fully):
  close the PR with a note, OR salvage only the delta you still add. Don't
  re-implement what landed.
- **Neighbor-renovation conflict** (upstream rewrote ADJACENT code — e.g. the
  auth/host-header framework around your change — but your core feature is
  absent): the PR is still valuable. This is a design-level rebase, not a
  mechanical one — you must RE-GRAFT your logic onto upstream's new structure
  rather than keep-your-version-in-the-conflict-hunk. Check whether upstream's
  rewrite already subsumed part of your diff (e.g. a stricter Host parser that
  replaces your hand-rolled IPv6 split) and DROP the now-redundant lines.

### B. The "refactor epic declared COMPLETE ≠ merged" trap

When a PR is parked because upstream is decomposing a god-file (a huge module
being split into slices), do NOT assume "wait until the shard finishes" has a
bounded timeline. Contributors often open an EPIC issue ("Shard all N god
files") and mark it `[COMPLETE]` once they have *proposed* every slice PR — but
maintainer merge state is tracked separately and lags weeks/months, or stalls
indefinitely (`needs-decision` label). Evidence to gather:

- Epic issue title/labels: `[COMPLETE]` / `needs-decision` tells you the
  campaign status, not the merge status.
- Individual slice PR states: if even the AUTHOR's own slices sit `open` with
  last-activity weeks ago and some gone `dirty`, the whole effort is stalled —
  waiting on it is open-ended.
- The god-file's line count over time: still GROWING (`git show origin/main:f |
  wc -l` vs your base) means the decomposition hasn't landed; shrinking means it
  has. A growing target = moving靶, conflicts worsen daily.

Decision: when the park reason evaporates (epic "done", no merge window in
sight), stop passively waiting — either re-graft now onto current main, or post
one precise question to a HUMAN maintainer (not the auto-reviewer bot) asking
whether to (a) adapt to the new framework now, (b) wait for a real merge
window, or (c) let them cherry-pick/salvage with authorship preserved.

### C. Contributing INTO a mid-decomposition god-file: extract-a-slice + seam

If upstream policy is "god-files must be sharded, partial edits discouraged,"
don't jam logic back into the giant file. Mirror their own pattern:

- Put genuinely NEW, pure, app-free logic in a fresh module
  (`hermes_cli/web_serve_bind.py`) so it never line-conflicts with others'
  edits to the big file. New files are off the moving target.
- In the big file, add a thin **seam re-export**:
  `from hermes_cli.web_serve_bind import create_server_sockets, ...`. Assert
  identity holds: `web_server.create_server_sockets is
  web_serve_bind.create_server_sockets` so monkeypatch targets and existing
  callers keep working.
- **Do not add `# noqa:` to a seam import unless the rule actually fires.**
  An unused `# noqa` is itself a blocking error (RUF100 is enabled in this
  repo's ruleset) — verify by running the pinned linter on the file, and
  mirror upstream's own style at that position (upstream's sibling seam import
  carries a plain explanatory comment, no noqa).
- **Never keep a local `def` of a symbol you also import** — the local copy
  shadows the import, so callers that import it *through this module* get the
  copy while the module's own internal callers get the original: two divergent
  implementations of one security predicate (F811, and lint may not even be
  watching for it). Delete the local copy, keep the module version as the
  single source, and pin it with an identity assertion test.
- Keep tightly-coupled request-time logic (depends on module-local state like a
  trusted-hosts snapshot or a shared parser) IN PLACE as a minimal extension to
  upstream's function — don't force-extract it just to look "sharded."
- Make extended functions BACKWARD-COMPATIBLE so upstream's existing tests need
  zero edits: accept both the old scalar arg and the new collection
  (`if isinstance(x, str): x={x}`), and keep an old kwarg as an alias
  (`start_server(hosts=..., *, host=None)` where `host=` still works). Verified
  this session: this let a multi-host rewrite pass upstream's unchanged
  `test_serve_port_in_use.py` (which calls `start_server(host='127.0.0.1')`)
  green without touching it.

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
  `references/upgrade-deployed-instance-with-patches.md` §7a. Run the suite in the
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
  reading. See `references/pr-conflict-investigation.md` §5 for why a monitor must
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
