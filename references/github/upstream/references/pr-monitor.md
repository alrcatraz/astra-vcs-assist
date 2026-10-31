# PR Activity Monitor — design that reports WHAT happened, not just counts

The user runs a cron script (`~/.hermes/scripts/pr-monitor.py`) that watches
open PRs and reports new activity. Lesson learned the hard way: a monitor that
tracks **counts** is useless — "1 new comment(s)" tells the user nothing about
who commented, when, or what they said. The rewrite tracks **IDs** and prints
full content.

## State design: track IDs, not counts

State file `~/.hermes/scripts/pr-monitor-state.json`, per PR key:

```json
{
  "NousResearch/hermes-agent#73849": {
    "status": "open", "mergeable": true,
    "comment_ids": [5138206823],
    "inline_ids": [3684464632],
    "review_ids": [4821020069]
  }
}
```

Compare current ID sets against stored ones; report items whose ID is new.
Counts are derived, never stored — counts can't distinguish "same comment
edited" from "new comment", and simultaneous additions undercount.

**Suppress the `mergeable: null` recompute blips at the source.** GitHub resets
`mergeable` to `null` while it re-evaluates a head (after pushes, base advances,
or periodic recalc), so a naive change-comparison fires an alert on True → None
and again on None → True, waking the briefing route for zero content. The guard
must be TWO-sided: skip when `now_mergeable is None` (transient reading) AND when
the stored `prev["mergeable"] is None` (the previous tick saw a mid-recompute
window, and a stored null compared against a fresh bool yields a guaranteed false
False→True alert). Only a real bool→bool transition is worth reporting:

```python
if (
    "mergeable" in prev
    and now_mergeable is not None
    and prev.get("mergeable") is not None
    and prev.get("mergeable") != now_mergeable
):
    changes.append(f"Mergeable: {now_mergeable}")
```

Verify after editing: run the script twice back-to-back — both runs must be
silent (stdout empty) when nothing changed. A lone `Mergeable:` alert on a PR
with no new comment/review IDs is still suspect; briefers should read it as a
possible blip (see `pr-briefing-workflow.md` §1a).

**The `mergeable_state` transition needs the SAME kind of guard — and must reject
the sentinel value.** The `mergeable` guard above is two-sided against `None`, but
the `mergeable_state` comparison (`if now_ms and prev_ms and now_ms != prev_ms`)
passes any truthy string on both sides, so a transition whose TARGET is
`unknown` is reported as if it were a real state change. `unknown` is GitHub's
documented member of the enum (`{dirty, blocked, clean, unstable, has_hooks,
unknown}`) but it means the mergeability check could NOT be computed — a
sentinel, not a state. The mechanism that manufactures it: `check_pr` forces a
recompute via `pulls/{n}?test=1`, and that response returns `mergeable: null`
mid-window, so the `if merge.get("mergeable") is not None` block is skipped; the
field then carries the previous tick's reading or, when the payload was empty, the
code's own sentinel (`keys or ["unknown"]` at the webhook layer). Guard both sides:

```python
LEGAL_MS = {"dirty", "blocked", "clean", "unstable", "has_hooks", "unknown"}
if now_ms in LEGAL_MS and prev_ms in LEGAL_MS and now_ms != prev_ms:
    changes.append(f"Mergeable state: {prev_ms} -> {now_ms}")
```

The `unknown` member must be excluded EXPLICITLY — it is IN the legal set, so
"both sides legal and different" does not drop it (that reasoning is circular and
re-introduces the bug). Require both sides legal, different, AND neither side
`unknown`:

```python
if (now_ms in LEGAL_MS and prev_ms in LEGAL_MS
        and now_ms != prev_ms
        and now_ms != "unknown" and prev_ms != "unknown"):
    changes.append(f"Mergeable state: {prev_ms} -> {now_ms}")
```

A transition INTO `unknown` (a failed read) is never news, and a transition OUT of
a stored `unknown` (a recovering baseline) is only worth reporting once the
destination is a real, different state. Verify with the double-run rule above: a
run where `?test=1` is throttled must be silent, not a false `-> unknown` alert.
Without this guard the monitor wakes the briefing route for zero content — the
exact failure the `mergeable: null` guard was added to prevent, re-introduced
through the sibling field, and the symptom is a fleet-wide `unknown` flare (several
PRs flipping on the SAME tick during a recompute window) rather than any one PR's
state moving. A legal-set filter that merely INCLUDES `unknown` is the half-done
version of this fix: the storage guard can be correct while the report side still
fires, so check both independently by replaying a throttled read.

**And never PERSIST `unknown` as the baseline.** A transition OUT of `unknown` is
noise because `unknown` should never have been stored: it means the mergeability
read FAILED, so the previous tick's good value must survive. The store-side guard
(needs BOTH the legal-set check above and this) keeps the last good value when the
new reading is `unknown`:

```python
"mergeable_state": (lambda _v: _v if _v != "unknown" else prev.get("mergeable_state", ""))(
    pr.get("mergeable_state", "")
),
```

With both guards, a throttled `?test=1` window (failed read → `unknown`) produces
zero output across a full double-run — the legal-set check stops it being REPORTED
and the store guard stops it being RECORDED. Applying only the report-side guard
still fires one false `unknown -> <real>` recovery alert on the next successful
tick, because the poisoned baseline is already on disk.

**State is a delta machine, so the delta is not a status report.** Two events
never appear in the pushed output even though both matter:

- **An item absorbed by a `check_pr`-based initialisation.** That call
deliberately seeds every existing comment as seen, so a substantive review that
landed just before initialisation is *never* reported. Seeding silently is the
right default (the alternative is blasting a PR's entire history at the user),
but it means the very comment that demanded action can be permanently invisible
to the monitor.
- **An edited comment.** The body changes; the ID does not, so a
  substantively revised review is silently missed.

Both are why the briefing step must enumerate all current items rather than
brief from the pushed text — see `pr-briefing-workflow.md` §1. When
you add a PR whose comment history is not yet baseline'd, read the existing
thread yourself and tell the user what is already there, instead of trusting
that the first quiet tick means "nothing to see".

## Three GitHub endpoints — all three are needed

| Endpoint | What it returns | Report format |
|:---------|:----------------|:--------------|
| `repos/{repo}/issues/{num}/comments` | PR-level discussion comments | `💬 Comment by <login> (<time>):\n    <body>` |
| `repos/{repo}/pulls/{num}/comments` | **Inline review comments on code lines** | `📝 Review comment by <login> (<time>) on <path>:<line>:\n    <body>` |
| `repos/{repo}/pulls/{num}/reviews` | Formal reviews (APPROVED / CHANGES_REQUESTED / COMMENTED) | `🔍 Review <STATE> by <login> (<time>):\n    <body>` |
| `repos/{repo}/pulls/{num}` | state + mergeable | `State: open → merged`, `Mergeable: True` |

**The inline endpoint is the one everyone forgets.** The first count-based
monitor missed 4 inline review comments on a PR entirely — including a
security review — because it only fetched issue comments and reviews. Always
fetch `pulls/{num}/comments`.

Details per item to capture: `user.login`, `created_at` (ISO → human readable,
`Z` → ` UTC`), `body` (strip whitespace), and for inline: `path` +
`line`/`original_line`. Skip reviews with `state == "PENDING"`.

## gh API pattern

```python
def gh_api(endpoint: str) -> dict:
    # Best-effort: a single slow/limited call must never abort the whole run.
    # 45s (above the common GitHub rate-limit stall), one retry on timeout,
    # then degrade to {} for THAT endpoint only.
    for attempt in range(2):
        try:
            r = subprocess.run(["gh", "api", endpoint, "--jq", "."],
                               capture_output=True, text=True, timeout=45)
        except subprocess.TimeoutExpired:
            if attempt == 0:
                time.sleep(3); continue
            print(f"GH API timeout (2x, {endpoint})", file=sys.stderr)
            return {}
        except OSError as e:
            print(f"GH API spawn error ({endpoint}): {e}", file=sys.stderr)
            return {}
        if r.returncode != 0:
            print(f"GH API error ({endpoint}): {r.stderr.strip()}", file=sys.stderr)
            return {}
        try:
            return json.loads(r.stdout) if r.stdout.strip() else {}
        except json.JSONDecodeError as e:
            print(f"GH API bad JSON ({endpoint}): {e}", file=sys.stderr)
            return {}
    return {}
```

Requires `gh` authenticated (check `gh auth status`). Empty dict on error keeps
the run silent rather than spamming false alarms.

**`TimeoutExpired` is NOT caught by the `returncode != 0` branch — `subprocess.run`
raises before setting `returncode`.** A bare `timeout=30` with no `except` makes
ONE slow endpoint abort the whole run with `Script exited with code 1`, which
`save_state()` at the end of `main()` never reaches: the run reports exit 1, the
state baseline is untouched, and the next tick re-fires every alert it already
emitted while any transition in between (`State: open → merged`) is lost forever.
The whole class of symptom — a cron job "keeps failing" with a `TimeoutExpired`
traceback naming a single endpoint — is one missing `except` clause, not a
network outage. Per-endpoint degradation + retry is the fix; see the
`save_state()` note below for the second half (wrap each PR / save incrementally).

**Make `import time` explicit** if you use the `time.sleep(3)` retry — do not
rely on `import json`/`os` incidentally pulling it in; the monitor may be exec'd
under a stripped `main.__dict__` by the cron runner.

## Cron integration

- `no_agent=true` script job, `every 30m`, `deliver=origin`; empty stdout =
  silent (watchdog pattern), non-empty stdout delivered verbatim.
- **Always save state, even when silent.** The old script only saved when
  changes existed, which corrupted the baseline on runs that found nothing.
- First run initialises state silently (baseline). When migrating an old
  counts-only state file, the first ID-based run reports ALL existing items
  once — treat that as a feature (it catches up on content the user never saw),
  and verify the second run is silent.

## File layout

- `~/.hermes/scripts/pr-monitor.py` — the monitor (PRS list at top, add repos)
- `~/.hermes/scripts/pr-monitor-state.json` — state, auto-managed

**Second delivery channel (webhook):** when the monitor also feeds an
interactive war-room thread, the same run that prints its cron stdout ALSO signs
a POST to a dedicated webhook route (`pr-activity`) carrying the change brief —
see `messaging-bridge-ops` §"The endpoint is a hub". Keep the cron stdout path
untouched (dual channel, zero loss) and wrap the POST so a gateway outage only
writes stderr and never blocks or fails the report; read the route secret from
`webhook_subscriptions.json` and host/port from `config.yaml` without importing
PyYAML (the cron interpreter may lack it). The route drafts into the thread; the
chat session does the work.

**Dual-copy trap:** a template copy lives at
`skills/upstream-contribution-github/scripts/pr-monitor.py`. The cron runner
effects only the runtime copy; edit BOTH lists when adding or retiring an entry,
then run the runtime copy once and confirm the new `"owner/repo#num"` key
appears in the state file (a missing key means you edited the wrong copy).
No job recreation is needed — the scheduler re-reads the script each tick.
Retired PRs: remove from both lists AND delete their state keys, otherwise they
are polled forever.

**Sync the template from the runtime after a session's edits, then diff=0 is the
gate.** The two copies drift whenever a session edits the runtime only (an
interrupted run is the common cause — the runtime edit landed, the template
sync never ran). After any batch of monitor edits: `cp runtime template` then
`diff runtime template` must print nothing. `py_compile` passing on both says
only that each file is individually valid — it says nothing about their being
THE SAME file. Commit the template in the same change, since the skills tree is
version-controlled while `~/.hermes/scripts/` is not.

**Self-trigger loop: suppress our own comments before firing the route.** When
we push or comment on a PR we are monitoring, the next tick sees new IDs and
fires the webhook — the drafting session then reports our own action back to us
as if it were upstream news. Fix at the source: resolve the authenticated gh
account once per run (`gh api user --jq .login`, in `main()`, passed into
`check_pr` as `my_login=""` default so a failed lookup degrades to old
behaviour rather than crashing), and in ALL THREE item loops (issue comments,
inline review comments, reviews) mark the ID seen and `continue` without
appending when `user.login == my_login`. Skipping-at-source is cheaper than
filtering downstream and prevents a self-reinforcing briefing loop that confuses
the war-room thread. Note: our own commits/force-pushes still show up as
`head_ref_force_pushed` timeline noise only if the monitor ever tracks timeline
events — today it tracks comments/reviews only, so login suppression covers it.

**Verify the skip landed in ALL THREE loops** — the reviews loop is the one that
gets missed, because its `for r in reviews:` body is written from a different
pattern (it filters `state != "PENDING"` first). Count occurrences rather than
grep for the intent: `t.count('get("login") == my_login')` must return **3**.
A count of 2 means one loop silently still reports your own activity, and the
evidence that it's wrong is subtle — your own reply appearing as a fresh
"upstream comment" in the next brief.

**The webhook POST is a delivery channel, not a report format.** The signed
body (`{"brief": ..., "prs": [...]}`) feeds the route's prompt template, whose
placeholder must match those exact top-level keys (`{brief}`). The cron stdout
format is a separate concern — change one without touching the other. If the
drafting session ever reports an unrendered placeholder as an "empty payload",
the bug is the template's placeholder spelling, not the monitor — see
`messaging-bridge-ops` §"Template placeholders".

`save_state()` is called once at the END of the main loop, so a single PR whose
`gh api` stalls (network flake, a repo that responds slowly) aborts the run with
`subprocess.TimeoutExpired` and writes **nothing** — including the new entry you
just added and every other PR's fresh baseline. A full-script run therefore looks
like it worked (exit code, no output) while the new key is silently absent.

**The consequence runs both ways and reaches the briefing:** the run can emit
its stdout alert (so the user *is* told) and still die before `save_state()`, so
the state keeps the pre-alert baseline. The same event then re-fires on the next
tick as if fresh, while a transition that happened *between* such runs (notably
`State: open → merged`) is never recorded at all. When a briefing cites a
monitor push, cross-check the job's run history (`~/.hermes/cron/jobs.json`,
`deliveries.db`) for `Script exited with code 1` and say plainly that the state
is one tick stale. Two structural fixes, in order of preference:

- Wrap each PR in `try/except` so one slow PR degrades to a warning line and the
  loop continues — `save_state()` then still runs for the PRs that succeeded.
- Call `save_state()` incrementally (after each successful `check_pr`) instead of
  once at the end.

Verify the fix by running the script twice back-to-back: both runs silent when
nothing changed, and the state file's `updated_at` advancing even when a PR
errors.

**A silent run proves NOTHING about the state file.** "No output" is produced by
an empty `changes` list, which a broken or never-firing comparison also yields.
Before trusting a quiet tick as "upstream is silent", assert the stored value
actually matches reality:

```bash
gh api repos/<owner>/<repo>/pulls/<n> --jq '[.state,.mergeable,.mergeable_state]|@tsv'
python3 -c "import json;print(json.load(open('<state-file>'))['<owner>/<repo>#<n>'])"
```

A mismatch means the last run never saved (aborted) or the comparison can't
fire — the monitor is blind, not the PR quiet.

## The payload a field is read from decides whether it can EVER fire

`check_pr` reads its gate/CI fields from ONE call whose `--jq` expression is the
literal `.` (i.e. `gh api repos/{o}/{r}/pulls/{n}`), and everything downstream is
therefore a **JSON key of that endpoint**. The `pulls/{n}` payload has `state`
(`open`/`closed` — never `MERGEABLE`), `mergeable` (`true`/`false`/`null` only),
`mergeable_state`, `reviewDecision`, `comments`, `review_comments`, `commits`,
`head`, `base`. There is no PR-readability field there, and no CI conclusion
(check-runs and commit status live on OTHER endpoints).

Three failure shapes all present as "the monitor stays silent":

- **A misspelled or absent key is filtered silently by `--jq .`** — `gh` prints
  nothing and exits 0 for a valid expression, so `pr.get("mergeableState")`
  returns `None` exactly like a key that merely hasn't been populated. Assert a
  new field against a synthetic dict (and against a live `gh api` read of the
  SAME endpoint) before believing a quiet run means "no change".
- **JSON truthy guards drop valid values.** `if pr.get(k)` never fires for `''`
  (a valid key with an empty review decision) and drops `0` (e.g. a
  `checks_total: 0` counter) — while `if k not in prev` first-seen logic drops
  `0` permanently, because `0` never counts as "present". Use explicit
  `is not None` / `in` comparisons, and exercise each new key with its EMPTY
  value before wiring it.
- **A field read from a different endpoint needs its own fetch.** CI conclusions
  come from `commits/{sha}/check-runs` + `commits/{sha}/status`, both keyed on
  `head.sha` — a `mergeable_state`/`reviewDecision` addition that also wants CI
  must fetch those too, and each extra fetch is one more place a timeout can
  abort the run (keep them inside the per-PR try/except below).

Store whatever gates the briefing's decision list: at minimum `mergeable_state`
and `reviewDecision` alongside `status`/`mergeable`. Without them the monitor
can never report the two changes a reader actually acts on — a review landing,
or the PR becoming merge-ready — no matter how often it ticks.

**Detect `reviewDecision` transitions with the same two-sided pattern.** A PR
sitting at `reviewDecision: ""` (no maintainer verdict) is uninteresting until
someone APPROVES or REQUESTS_CHANGES. Unlike `unknown` in `mergeable_state`, the
empty string IS a valid stored value, so the guard only needs both sides to be
PRESENT in state and to differ:

```python
now_rd = pr.get("reviewDecision", "")
prev_rd = prev.get("reviewDecision")   # None = key not yet seeded
if "reviewDecision" in prev and now_rd and now_rd != (prev_rd or ""):
    changes.append(f"Review decision: {prev_rd or '(none)'} -> {now_rd}")
```

The `"reviewDecision" in prev` term does the work: on the FIRST tick after the
key is added, `prev` lacks it, so no spurious `(none) -> X` alert fires — the
seed run (run `check_pr` once manually before the next cron tick, as described
for new PR entries above) establishes the baseline, and only a genuine verdict
change reports thereafter. Without the presence check every PR in the fleet
would report a fake "review decision" alert on the tick after the key is
introduced.

Initialise the new key on its own, without walking the other PRs:

```bash
cd ~/.hermes/scripts && python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('pm', 'pr-monitor.py')
pm = importlib.util.module_from_spec(spec); spec.loader.exec_module(pm)
old = pm.load_state()
pm.check_pr('<owner>/<repo>', '<num>', old)   # side-effect: fills old[key]
pm.save_state(old)
print('initialised')
"
```

Then assert the key exists and its `status`/`mergeable` match reality:

```bash
python3 -c "import json; s=json.load(open('pr-monitor-state.json')); print(s['<owner>/<repo>#<num>'])"
```

**Initialising must be silent on purpose.** `check_pr` returns every existing
comment/review as "new" against an empty baseline, so on a real cron tick it
would blast the PR's whole history to the delivery target. Running the direct
initialisation above sets the baseline so the next tick reports only genuinely
new activity. The same applies when migrating a counts-only state file.

## Delivery target: `origin` is dead outside a chat session

A cron job with `deliver=origin` posts into the chat the job was created from.
In a TUI session there is **no live delivery channel** — the job still runs and
its output is saved for `cronjob action='list'`, but nothing reaches the user.
For a monitor the user is expected to notice, deliver to a gateway-connected
platform instead (`matrix:<room>`, `telegram:<chat>:<thread>`, ...).

**Every job on this host has its OWN room — do not borrow a sibling's.** The
Matrix targets are one-per-job (health-check, keepass, SRE, pricing each have a
distinct `!...` id), so copying a neighbouring job's room cross-posts unrelated
traffic into it. Ask the user which room a new monitor should report to (or for a
new room id), then set `deliver` via `cronjob action=update`; never guess a room
id and never assume a shared "alerts" room exists.

**Delivery target drifts with the job's purpose — re-check it, don't assume.**
A job that started as a read-only broadcast to a system-notification room stays
there until someone moves it, even after its output stops being read-only. When
a monitor becomes the trigger for an interactive workflow (a webhook route that
wakes an agent and asks the user for a decision), its reports need to land where
the user REPLIES — the working chat/thread — not the one-way notifications room.
Symptom of the mismatch: the agent's briefing is delivered to a room nobody
answers in, while the user asks from a different thread why nothing ever
reaches them. Fix by pointing `deliver` at the interactive surface and stating
plainly that the notifications-room copy stops (or is duplicated) — the user
should not have to discover the change from silence.
