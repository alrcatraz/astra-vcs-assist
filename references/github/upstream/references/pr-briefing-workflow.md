# PR Activity Briefing — reading new activity and recommending a follow-up

The monitor's webhook route wakes an agent with the pushed delta ("PR X has a
new comment"). That delta is the START of the briefing, not the briefing. The
job is: enumerate the activity, judge each item against the disposition rules,
and hand the user a decision list. No writes — this route drafts; the user
decides.

## 1. Enumerate ALL current comment IDs, not just the pushed delta

**The highest-value item is regularly one the baseline already absorbed.** The
comment that actually demands action can predate the monitor's baseline (it was
seeded into state during initialisation, or an earlier tick already reported it),
so the pushed delta is a *neutral* "verified green" note while the substantive
review sits one comment earlier — never delivered, never read.

So never brief from the pushed text alone. Fetch the full set every time:

```
GET /repos/{repo}/issues/{num}/comments     # PR-level discussion (bots post here)
GET /repos/{repo}/pulls/{num}/comments      # inline review comments on code lines
GET /repos/{repo}/pulls/{num}/reviews       # formal reviews
GET /repos/{repo}/pulls/{num}               # state, mergeable, head.sha, counts
```

Then order the items yourself and say which were already seen. A briefing that
lists only the new delta is a partial briefing presented as a complete one.

### When `gh api` is blocked, the fallback is `web_extract` on the PR page — and label it as such

A webhook-drafted briefing session may be locked behind the work-principles
research gate (see skill `work-principles-cron-gate-deadlock`): `gh api`,
`curl`, `git fetch`, `tool_call`, and MCP fetches are all blocked mid-run, the
`[HARNESS: plan]` marker only lands at end-of-turn, and the state-file escape
hatch is itself a blocked write — so the API path is unreachable inside the run.
Do not stall and do not fabricate freshness. In order:

1. **`web_extract` on `https://github.com/<owner>/<repo>/pull/<n>`** (and
   `/pull/<n>/checks` for CI, `/pull/<n>/files` for scope) — an *unblocked* tool
   on this route, and it returns the full conversation, commit list, labels, and
   state header in one call. Extract both the pushed PR **and any PR it cross-
   references** (the successor PR that absorbed our commits is regularly where
   the real status lives). The page is large — `web_extract` spills over to a
   cache file; page it with `read_file`, do not re-request the URL.
2. `web_search` for the PR number + author/login to catch state changes the
   cached page missed (a merge that landed after the pull).
3. **Local sources**, if web is also unavailable:
   `~/.hermes/cron/output/<job-id>/*.md` (what the monitor pushed + tick history),
   `~/.hermes/scripts/pr-monitor-state.json` (comment/review ID baselines), the
   dev clone (`git -C ~/Projects/hermes-agent log --all --grep=<PR#>`,
   `branch -vv`), and `session_search` over prior pr-activity sessions (our side
   of past threads).

State explicitly in the briefing that the data is web-extracted or
locally-sourced rather than `gh api`-fetched, and name what a live API read
would add (exact `head.sha`, check-run conclusions, a comment posted after the
last pull). One cheap unlock if you must get live data: end a turn with
`[HARNESS: plan]` as pure text and ask the user to approve — the gate clears
next turn — but a blip-only briefing (§1a) is not worth spending that turn on.

**Read-only classifier traps observed while gathering fallback evidence:** the
classifier checks only the first token and does not parse URLs, so `cat <url>`
passes the gate yet fails as a missing-file path — a whitelisted word prefix is NOT
a network fetch; don't loop on that shape. Compound commands (`cd x && grep …`)
classify as mutating; use `git -C <dir>` and single-purpose commands. A
`python3 -c "…"` one-liner that only reads a file passes only when its first token
is a whitelisted read-only word; verify the read path with `cat`/`grep` instead
of retrying the same blocked shape.

**Stop the read-only shapes after TWO identical refusals — they do not vary.**
`gh …`, `curl …`, `python3 -c …` were each refused in fresh forms by the same
gate in one session; a third shape of the same intent is the loop this rule
exists to stop. What actually worked, in order: batch `web_extract` against the
**raw API JSON** (`https://api.github.com/repos/{o}/{r}/pulls/{n}`, `/issues/{n}/comments`,
`/pulls/{n}/comments`, `/pulls/{n}/reviews`, `/commits/{sha}/check-runs`,
`/compare/{base}...{head}`) — these carry everything the briefing needs
(`mergeable`, `mergeable_state`, `head.sha`, `author_association`, review states,
CI counts), so the PR *page* is not the only fallback; `web_extract` on the
`.patch` URL for the full diff (spills to cache file — page it with `read_file`,
never re-request the URL); and the local sources above (state file, tick
archive). Label every fact's provenance as before, and keep the extraction list
per fact short — a verbose triple-quoted fallback block inside the briefing
report buries the three-part output contract; the user asked for substance →
judgement → decision list, not a log of which tool refused what.

**Read the whole thread before judging.** Cross-check the linked issue and the
PR's own body: review points often reference an issue's "Suggested fix" section,
so the reviewer's ask and the reporter's ask become one checklist instead of two
unrelated lists.

### A `Mergeable:` delta with no comment/review item attached needs a causal story, not just a clean ID set

`⚡ Mergeable: True` (or `False`) alone — no 💬/📝/🔍 line — means the mergeability
READING moved, so the first question is *what moved it*: a head push, a base
advance, or a periodic recompute. Ask it in this order:

- **Scan the run archive for the transition pair.** The state file carries only
  the latest value; `~/.hermes/cron/output/<job-id>/*.md` for the day is what
  distinguishes `True → None → True` (recompute blip) from a real bool→bool
  change. `None` in between = the double-sided guard did its job and you have a
  blip.
- **No `null` in the archive does NOT make it a blip — check for an aborted run.**
  A run that died before `save_state()` (a `subprocess.TimeoutExpired` on one PR
  aborts the whole script) still PRINTED whatever it had and left the pre-event
  baseline on disk. So the true sequence can be `false` (stored by an aborted
  run, never re-saved) → `true`, with no `null` tick anywhere in the archive.
  A bool→bool jump with no visible cause is therefore most often a *stale
  baseline* recovering, not news — say which of the two it is, with the archive
  runs named.
- **Then look for the real event the boolean is reporting.** A head move is on
  the PR's own timeline (`head_ref_force_pushed`), not in the comment ID sets —
  the monitor tracks comments/reviews only, so a force-push produces a
  mergeability change and ZERO comment items by construction. Reading that as
  "upstream is interested" (or as "nothing happened") both miss the event.
- **Multiple PRs flipping in the same tick** is still the signature of a
  recompute pass rather than interest in any one of them.
- **A flipped VALUE that is not a legal state at all is a local artefact, not
  upstream news.** `mergeable_state`'s legal set is
  `{dirty, blocked, clean, unstable, has_hooks, unknown}`; `unknown` means the
  mergeability check itself could not be read. When a transition's target is
  `unknown`, trace where the string came from before reading it as a state: the
  monitor forces a recompute (`pulls/{n}?test=1`) which returns `mergeable: null`
  mid-window, and its code falls back to the *previous* reading or a local
  sentinel (`keys or ["unknown"]` in the webhook payload) — so `X -> unknown` is
  normally "the read failed / baseline was stale", printed identically to a real
  transition. Corroborate by checking the prior tick (silent run + `unknown`
  flip = pure artefact) and by verifying the state file's mtime against the
  aborted runs. If the push carries only such boolean/string flips and the ID
  sets are unchanged, the whole push is monitor noise — say "no upstream
  activity / no action" with that causal story, and put the monitor's own
  guard/robustness fix on the decision list as an optional write item (it touches
  the monitor config, so it needs the user's go-ahead like any other write).
- **Cross-check the ID sets in `pr-monitor-state.json`**: unchanged
  comment/review IDs plus a recovered boolean = nothing new *to read*, which is
  the claim that matters for follow-up.

The correct output is a plain "no upstream activity / no action" WITH the causal
story (aborted-run baseline vs recompute vs our own push) — not a briefing that
dresses a boolean up as upstream interest, and not one that hides a real push of
ours behind "nothing happened".

**A comment-free PR may still owe the user an action that lives OUTSIDE the
monitor's ID sets.** Enumerating all comments correctly proves *upstream said
nothing*; it does not prove *nothing needs deciding*. Cross-referenced material
the monitor cannot see — a note an adjacent PR posted about our shared mechanism,
the approval-gated CI state, the branch's divergence from local — belongs in the
briefing as its own decision item, clearly labelled as found-by-full-read rather
than pushed-by-monitor. Do not let "no comments" collapse the decision list to
empty.

### A `State: open → merged` delta is status, not new activity — verify three things it does not carry

GitHub's `pull_request` event also fires on **state transitions** — open→merged,
open→closed — and the monitor's report format includes `State: open → merged`.
Treat it as a status update, not new dialogue: brief it, then say plainly whether
it creates work. Verify separately:

- **The actual merge SHA and merge time.** The pushed line carries the transition;
  the SHA only exists on the merged PR's own page / `pulls/{num}` →
  `merge_commit_sha`. Read it before quoting "merged" with a SHA.
- **Our PR's own state.** When our PR is absorbed by an upstream-authored
  successor PR, OUR PR's state does not change until the author closes it — the
  two are independent rows. Read both. The stale `mergeable` reading on our PR
  (the successor advanced past our head) is *not* a new conflict to fix; it is a
  recompute artefact of the absorption.
- **Whether the monitor even recorded the transition.** If the monitor's own run
  aborted (a `subprocess.TimeoutExpired` on one PR skips the whole run's
  `save_state()`), the alert may have fired while the state was never updated — so
  the same transition can be re-reported later as if fresh, or never recorded at
  all. Check the cron job's run history (`~/.hermes/cron/jobs.json` /
  `deliveries.db`) for `Script exited with code 1` alongside the brief, and say so
  when it happened.

After a merge lands, the two questions the user will actually ask are "is our
authorship preserved?" and "what is still open?" — answer them from the merged
PR's Credit/authorship section (cherry-pick `-x` plus an email-mapping file is the
standing convention for salvage) and from a search for open PRs citing our
original PR number (a split-out half of our work typically lives there), not from
the merge event alone.

## 2. Classify every author — the bot's opinion is not the merge gate

Check `author_association` and self-description on each item:

| Signal | Meaning | Weight |
|:--|:--|:--|
| `author_association: NONE` + body opens "AI code review — automated review for reference; please use your judgment" | triage/review bot | advisory |
| `author_association: NONE`, no bot disclaimer, reasoned prose | outside human | weigh seriously |
| `OWNER` / `MEMBER` / `COLLABORATOR` | maintainer | **gating** |

A bot's review item is still worth acting on when it identifies a defect *you
introduced* or a case your fix does not cover — the advice is cheap and the
finding is real. It is not worth treating as an approval requirement, and it is
not by itself a reason to hold the PR.

A third-party "verified at `<sha>`: suites pass N/N" comment is **evidence, not
actions** — but check the sha it names against `head.sha`. A verification
comment can report green against a sha the PR has since moved past, in which
case it confirms nothing about the current head.

## 3. Classify each item's follow-up cost

| Shape of the finding | Response |
|:--|:--|
| Defect **our change introduced** (regression surface we created) | fix now — we own it |
| **Same bug family, uncovered path** the fix did not reach | fix now, or split as a follow-up PR if genuinely separate |
| **Scope too wide** — our change silently removes behaviour other callers relied on | fix now (usually a narrow the-condition change) |
| Upstream-side context, other contributors' code, stylistic preference | note only; do not absorb into our diff |

For the second row: a fix that repairs one path while an identical hardcoded
cause survives in a sibling path is an **incomplete** fix. Say so plainly rather
than claiming the family is closed.

### A PR that is merely *waiting* should not be re-rebased to chase the base

`mergeable: true` on a base hundreds of commits behind is **not** a reason to
push again. Every force-push resets the reviewer's accumulated diff context and
marks existing inline threads `isOutdated`, so rebasing to stay current makes the
re-review you are waiting for *less* likely, not more. Offer "rebase now" only
when the PR has actually flipped to `dirty`; while it sits clean and blocked on
review, the recommendation is to leave the head alone and put the escalation
question on the decision list instead. Say this out loud when the branch has moved
several times with zero human review — repeated rebasing is our own noise, not
progress.

The companion judgement: before reporting a stalled PR as still valuable, prove the
feature is still **unique** with three cheap reads on the current base, not from
memory —

```bash
git show origin/main:<file defining the CLI flag> | grep -n '"--<flag>"'   # still single-valued?
git show origin/main:<entry module> | grep -n "def <function>" -A6          # still the old signature?
git ls-tree origin/main --name-only <dir>                                    # did our new module appear?
```

And when a keyword search turns up an open PR with a similar title, compare its
**file list** (`pulls/<n>/files`) before calling it a duplicate: a multi-bind fix on
a different serving stack (an aiohttp gateway surface vs the dashboard/uvicorn
surface) is an adjacent concern on another layer, not a competing PR — and give such
a stale neighbour one line in the briefing so the user does not later read it as
upstream having beaten us to it.

4. **Read the repo's CI surface correctly — pending is not failing**

`mergeable: true` with `mergeable_state: "unstable"` and
`check-runs total_count: 0` plus commit status `pending` means **nothing has run
or reported**, not that something failed. Distinguish:

- `unstable` + zero check-runs → no CI signal yet; not a blocker
- `unstable` + check-runs present, some `conclusion: failure` → real red, blockers

**`mergeable_state` values other than `unstable` are read the same way — the
state string alone is never a judgement.** `blocked` on a freshly-pushed head
with zero check-runs means *required checks/reviews are pending*, i.e. the same
"no signal" as `unstable`; on a repo that gates contributor branches, the three
PR workflows sit in `Action required — awaiting approval from a maintainer` and
NEVER attach a check-run to the head SHA, so `check-runs total_count: 0` is the
expected resting state, not an anomaly. Only a check-run whose `conclusion` is
`failure` is red. Read the PAIR (bool `mergeable` + `mergeable_state`) with the
check-run count, and report the state string as fact ("awaiting maintainer CI
approval") rather than as a verdict ("blocked"/"red" sounds like a fault the
reader must fix).

Also distinguish *the signal exists and is absent* from *the signal could never
arrive*: an approval-gated workflow is an upstream process, not a failing check,
and there is no contributor-side action that advances it. Do not offer
"re-run CI" or "fix checks" as options for a gate only a maintainer can open.

Never report "CI failing" from `unstable` alone, and never equate the monitor's
`mergeable` boolean with merge-readiness (`rebaseable`, review state, and labels
all bear on that).

### The other half of `blocked`: read the review state, not the string

`blocked` with `mergeable: true`, `rebaseable: true` and zero check-runs has two
candidate causes — required checks pending, or no approving review has ever
existed. The REST `reviews` list cannot tell you which, because it omits thread
resolve state and the aggregate decision. One GraphQL read settles it:

```bash
gh api graphql -f owner=<Owner> -f repo=<repo> -F pr=<number> -F query='
query($owner:String!,$repo:String!,$pr:Int!){repository(owner:$owner,name:$repo){
 pullRequest(number:$pr){ reviewDecision
   reviewThreads(first:50){ nodes{ isResolved isOutdated path
     comments(first:10){ nodes{ author{ login } } } } } } } }' \
  --jq '{decision:.data.repository.pullRequest.reviewDecision,
         threads:[.data.repository.pullRequest.reviewThreads.nodes]}'
```

Read it as: every thread `isResolved: true` + `isOutdated: true` means the review
conversation is **closed** — the review-comment count the monitor reports is then
history, not a queue, and a briefing that lists those points as open follow-ups is
wrong. A `reviewDecision` of `null` alongside only `COMMENTED` reviews means nobody
has ever formally reviewed the head; that is the true cause of `blocked`, it is an
upstream-bandwidth fact, and the only contributor-side lever is one precise question
to a *human* maintainer — never another mention of the automated reviewer.

Four `gh api graphql` / `--jq` mechanics that each cost a failed call:

- `-f` sends a **string**, `-F` sends a **typed** value. An `Int!` variable passed
  with `-f` fails with `Could not coerce value "12345" to Int`. Use `-F` for numbers.
- Pass owner and repo as **two separate variables**. Putting `Owner/repo` in the
  `owner` variable resolves to `Could not resolve to a Repository with the name
  'Owner/repo/repo'`.
- **Every** nested connection needs its own `first:`/`last:` — a `comments`
  connection without one raises `MISSING_PAGINATION_BOUNDARIES` and the nodes come
  back `null`, which reads like an empty result rather than a query fault.
- Inside `--jq`, every field of a returned object needs its leading dot
  (`.user.login`, not `user.login`; the latter fails as `function not defined: user/0`).

Also: `pulls/<n>/requested-reviewers` answers `404` on some repos — treat that as
"unreadable", never as "nobody was asked"; the `review_requested` line on the issue
**timeline** is the readable evidence. And when a command is blocked *after* a
redirect was written, the file may not exist at all — verify the artefact before
trying to parse it, and read JSON with `jq` over the file rather than a `python3 -c`
inline (an inline `-c` is a blocked command class on unattended routes).

## 5. Output contract: per item — substance, judgement+rationale, action list

The user's asked-for shape, in this order:

1. **Substance per item**, quoted from the source (author, UTC time, the actual
   claims), not a paraphrase of the number of items.
2. **Judgement per item**: follow up or not, the recommendation, and the reason.
3. **A "待用户拍板" decision list** — the open choices, each with the options
   spelled out, and an explicit statement of whether any write happened (on this
   route: none).

Where the repo has a robot reviewer, label it as such in the briefing so the
user can weight it correctly instead of treating a bot comment as a maintainer's
blocking review.

**The decision list must separate read-only items from write items.** Every
action that would touch a PR, a monitor config, or a deployed tree is a write and
needs the user's explicit go-ahead on this route — state "本次已发生的写操作：无"
(and list which proposed actions are writes) so the user never has to guess which
suggestions already executed. Offer a recommended option first, with concrete
alternatives spelled out ((a)/(b)/(c)), so a one-word reply settles it.

**A merge that absorbed our work produces follow-ups the user will ask about —
name them proactively, each as its own decision item:**

- **Closing our PR.** Do not race the author: if they said they will close it
  with the merge SHA, waiting 12–24 h is the recommendation; closing it ourselves
  is the fallback only when the user wants the monitor entry cleared early.
- **Monitor retirement.** When the PR closes, its entry and state key must go from
  BOTH `pr-monitor.py` copies or it is polled forever — surface this as a
  decision item, not a silent plan.
- **Local patch / fork branch disposition.** "Fix merged upstream" means sync and
  drop the local patch (skill branch table) — but on a deployed instance this is
  an upgrade-schedule question, so offer "next upgrade" vs "now" as options
  instead of acting.
- **Successor PRs that still cite our PR.** If upstream split our work across an
  absorbed half and an open successor, adding the successor to the monitor keeps
  our authorship thread visible — make it an explicit option alongside the
  retirement.

### A stalled PR may already be load-bearing on a live host — check, do not assume

The monitor says nothing about whether production is *waiting on the merge*. When
the PR'd feature is a new CLI flag, look for a running unit that already passes it.
The user cannot derive this from the briefing text, and it must not be discovered
later by an outage:

```bash
systemctl --user show <unit> -p ExecStart -p ActiveState   # what flags does prod pass?
grep -c '<new-symbol-the-PR-introduces>' <deployed-tree>/<file>.py   # is the patch present?
git -C <deployed-tree> log -1 --format='%h %s'                          # which commit runs?
ss -ltnp | grep <port>                                                  # what actually bound?
```

The trap that makes this worth checking: **a flag the deployed tree does not support
usually does not fail — it degrades silently.** An argparse option declared without
`action="append"` accepts a repeated `--flag` and keeps only the LAST value, so a unit
line written for the PR's behaviour boots fine while doing something else (a
dual-address bind collapses to one listener, which may then be reachable only
incidentally via a wildcard socket). Prove the outcome from the OS view — `ss -ltnp`:
count the listeners and note `[::]` versus a separate v4 row — never from "the unit
is `active`". Then offer the three real options: land the patch on the deployed tree
(which must follow the live-host rules in `upgrade-deployed-instance-with-patches.md`
§7, including never restarting the unit that hosts your own session), change the unit
to a form the current tree honours and demote the PR to a pure upstream contribution,
or record the dependency and leave it be.

Confirm **which tree each unit runs** (`venv/bin/<entry>`, a bin wrapper, an
`installs/<id>/…/workspace/` snapshot) before concluding anything: different units on
one host can serve different trees, so "deployed" is one fact per unit, not one fact
about the machine.

## 6. Purity and gate reminders that bite on this route

- **The briefing is a distinct voice in the user's chat — label it.** A webhook-drafted
  briefing lands in the same thread as the orchestrator's own replies, and the user reads
  two different "agents" speaking with one identity (their words: "我怎么感觉有两个Angelia").
  The fix lives in the ROUTE PROMPT, not in the drafter's goodwill: prefix every delivery
  with an explicit provenance line (e.g. `[pr-activity 简报]（本条为路由起草的只读简报，非直接发言）`)
  so the reader can tell report-from-sentinel from agent-answer at a glance. Prefer labelling
  over re-routing to a separate thread — splitting threads forces the user to track two
  columns and they will ask why.
- **A self-triggered briefing is noise, not new activity.** When WE post a comment or push
  to our own PR, the monitor sees fresh IDs and fires the route — the drafter then reports
  our own action back to us as if it were upstream news. Before acting on a briefing, check
  whether its trigger item is authored by us; if so, say "this is our own reply, nothing new"
  instead of re-litigating it. Suppressing self-authored items at the monitor (skip comments
  whose `user.login` is ours) prevents the loop entirely.

- **`gh api` itself may be gated mid-run** (see the fallback section under §1):
  `gh api`, `curl`, `git fetch` and compound/cd-prefixed commands can be refused
  by the harness gate while `web_extract`, `web_search` and single-purpose
  read-only shell still pass. Hit it, do not loop on the same blocked shape —
  fall back per §1, keep gathering with the tools that still work, and state the
  provenance of each fact in the briefing.
- **The PR body is a surface the monitor never re-reads, so it goes stale and impure
  in silence.** Audit it in every briefing that touches the PR, against the *current*
  head: the file list it names (`pulls/<n>/files` is ground truth), helper names since
  extracted into a new module, a verification checklist describing an older revision,
  and any own-tooling or own-infra term left over from the first draft. The diff
  moves with every rebase and the body never does — so a purity sweep that stops at
  `git diff` misses the most-read text on the PR. Propose a body rewrite as a
  recommendation; never apply it on this route.
- **Contribution purity applies to the BRIEFING too.** When proposing wording
  for a reply or a commit, propose it in the upstream project's own vocabulary
  ("system producer", "batch guard", "transcript surface"). Never let our
  device names, orchestrator/constellation terms, or deployment hostnames into a
  draft destined for the PR. Cheap to enforce while drafting, expensive to
  un-ship after posting.
- **If the review asks for a regression test, the plan must state the RED
  requirement up front** — new assertion fails without the fix, then passes
  with it. A plan that promises "add a test" without the negative control is
  incomplete, and a green assertion anchored on the input just consumed is
  false-green.
- **An append fix needs no force push.** Pushing new commits to the PR's head
  branch updates it; `--force-with-lease` is only for rewritten history. State
  which one the plan uses.
- **Stopping honestly is a valid briefing outcome.** If an item is advisory, or
  a stated state has been correctly read as non-blocking, the recommendation is
  "no action" — do not invent work to look responsive.
