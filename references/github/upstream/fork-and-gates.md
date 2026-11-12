# Fork creation and the two approval gates that precede any edit

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

Everything in `pr-workflow.md` assumes there is a real defect. **Establishing that is a
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
