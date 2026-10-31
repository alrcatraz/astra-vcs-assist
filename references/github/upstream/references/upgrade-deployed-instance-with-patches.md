# Upgrading a deployed instance that carries a local patch stack

Use when a production host runs a copy of the upstream project AND carries local
patches — some of which are still-UNMERGED upstream PRs. This is the execution
recipe for landing an upstream fix on that host (or refreshing the host wholesale).

Companion to SKILL.md §Step 0 ("is the fix already upstream?"): once that check
tells you the fix exists upstream, this is how you get it onto the host without
losing the local work.

## Step 0 — Inventory the local patches and classify them

Never start from "upgrade and see what happens". Enumerate first:

```bash
cd <deployed-copy>
git status --short                  # every local modification
git diff --cached --stat            # staged set
git diff --stat                     # unstaged set
git log --oneline origin/main..HEAD # local COMMITS (often none — patches live in the worktree)
```

Classify each file, because the disposition differs per class:

| Class | Meaning | Disposition after upgrade |
|-------|---------|---------------------------|
| **A — instance config** | host-specific values, private topology, internal endpoints | MUST keep; re-apply. **Never PR these** — they encode private infrastructure. |
| **B — bug fix with an open PR** | patch lands the fix before upstream merges | Re-apply; DROP only if upstream has since absorbed the semantics |
| **C — local feature with an open PR** | new capability upstream does not have | Re-apply (re-graft if the surrounding file was rewritten) |
| **D — obsolete** | upstream now owns the behaviour | DROP; verify upstream's version instead |

Prove class D rather than assuming it: `git show origin/main:<file> | grep -c <token>`
→ non-zero means absorbed. A refactor can absorb the behaviour while the token
still reads 0, so also read the call sites (`grep -rn <helper> <module>/`).

## Step 1 — Snapshot before touching anything

```bash
B=~/scratch/prod_upgrade_$(date +%s); mkdir -p "$B"
cd <deployed-copy>
git rev-parse HEAD > "$B/HEAD_before.txt"
git status --porcelain -uall > "$B/status_before.txt"
git diff --cached > "$B/patch_staged.patch"
git diff > "$B/patch_unstaged.patch"
# DB snapshot — use sqlite3's .backup API, never cp, on a live DB
python3 -c "import sqlite3;\
s=sqlite3.connect('file:<state.db>?mode=ro',uri=True);\
d=sqlite3.connect('$B/state.db.backup');s.backup(d);d.close();s.close()"
```

`cp` on a live SQLite file can capture a torn page state; `.backup()` takes a
consistent snapshot under a read lock. Keep this until the new version has booted
cleanly once, because a large-range upgrade may run schema migrations on first start.

## Step 2 — Stop the services

```bash
systemctl --user stop <unit1> <unit2>
systemctl --user is-active <unit1> <unit2>    # assert, don't assume
```

Stopping first avoids a half-upgraded process tree reading files mid-checkout.
Assert with `is-active`; units may already be inactive.

## Step 3 — Upgrade with ff-only, not the product's own updater

```bash
git fetch origin main
git merge --ff-only origin/main
```

On a host whose local patches are UNMERGED PRs, prefer the explicit ff-only merge
over the bundled `hermes update` / `* update` command: you keep the patches in the
worktree under your own control and re-apply them deliberately, and the pre/post
SHAs are directly comparable. The bundled updater's auto-stash → pull → pop cycle
is documented as not guaranteed to preserve patches.

**Scope that advice to the SOURCE step only.** A host whose units boot from an
environment generation snapshot still needs the product's own update to rebuild
that generation — ff-only moves the repo, which is exactly what the stamp does not
watch (see 7h and the stamp pitfall). The two are complementary, not alternatives:
ff-only for source, then the bundled takeover for the environment, with the patch
stack first locked into a reachable commit so no autostash can sweep it.

Large ranges (hundreds–thousands of commits) take minutes for fetch + tree
checkout — give the command a generous timeout rather than assuming a hang.

## Step 4 — Re-apply the local patches

```bash
git stash push -m 'prod-upgrade-<stamp>' -u -- <file1> <file2> ...   # if not already stashed
git stash apply stash@{0}
```

Expect **most files clean, one hot file `UU`**. The hot file is the one upstream
keeps re-authoring; its conflict is neighbour renovation, never supersession.

For the `UU` file:

1. Read both sides AND the surrounding upstream function — upstream may have
   rewritten the structure your hunk assumed.
2. Prove supersession vs renovation: `git show HEAD:<file> | grep -c <your_helper>`
   → `0` = your feature still missing → renovate (re-graft); non-zero = absorbed →
   drop your side.
3. Re-apply your delta onto upstream's new body; do not keep-your-version inside
   the conflict hunk.
4. Sweep and compile:
   ```bash
   grep -rn '^<<<<<<< \|^=======\|^>>>>>>>' <file>
   <venv>/bin/python -m py_compile <file>
   ```

## Step 5 — Surface ambiguous patches to the user, don't guess

If a conflicted patch is a **feature the user may no longer want**, stop and ask.
Present a table (patch → status → what breaks if dropped) plus the single question
that decides it (e.g. "do you still need dual-stack `--host` binding?"). Dropping
a local feature changes host behaviour more than re-grafting it does, so the call
is the user's — re-grafting silently and dropping silently are both wrong.

## Step 6 — Verify by effect, then restart

```bash
# per-patch feature token grep, then:
git diff --check
systemctl --user start <unit1> <unit2>
systemctl --user is-active <unit1> <unit2>    # expect active
```

A diff readback proves nothing. For a bind-related patch, a loopback dual-bind
smoke test (v4 + v6 both connect) is the acceptance check. For a behaviour patch,
the acceptance check is the user-visible symptom no longer reproducing.

### Trap: completion-loop after manual git upgrade

A host upgraded with `git merge --ff-only` (rather than the product's own
`update` command) still runs the product's own completion machinery on the next
service start. Two failure modes:

1. **The completion step loops if you restart during it.** Startup enters a
   "finishing an interrupted source update" pass (rebuilds TUI/Web/desktop) and
   does not bind until it completes. The sentinel file
   `~/.hermes/.hermes-update-in-progress` (content: `PID` + newline + epoch)
   marks the pass. While it exists, `systemctl --user restart <serve unit>`
   merely spawns a fresh completion pass — never keep restarting. Wait for
   `✓ Update complete!` in the journal, then for `HERMES_BACKEND_READY` /
   `listening on`.
2. **`is-active` is not proof of serving.** The unit reports `active` for the
   whole completion pass with nothing bound. Assert the LISTENER:
   `ss -ltn | grep ':<port>'` (expect both `0.0.0.0` and `[::]` rows for a
   dual-stack bind) — only that, plus the READY line in the journal, means the
   service is actually up.

Also: `git clean -fd` in the repo while tidying up wipes `hermes_cli/.web_dist-*`
build caches; the next start then rebuilds the web UI and takes noticeably
longer. That delay is a rebuild, not a hang — check for `web_dist/` still
present before suspecting the patches.

## Step 7 — Landing a NEW local patch (not a re-apply) on a live host

This is the dangerous variant: you are adding a patch the host has never carried,
while the host is serving the session you are working from. Four rules, each of
which cost a production outage when violated.

### 7a. NEVER edit the deployed tree to test. Edit the dev copy, then patch.

Testing a fix means running the project's test suite, so the instinct is to drop
the change into the deployed tree and run pytest there. Do not. The deployed tree
is what the live process imports; a half-written edit is immediately live for any
new process that starts. The correct shape:

1. Apply and verify the change in the **dev copy** (working test environment).
2. Prove it there: targeted tests green, plus a statement-level import check.
3. Only then generate the patch and apply it to the deployed tree, with the
   service stopped (7c).

If the dev copy's interpreter is broken but the deployed one works, do **not**
reach across by `cp`-ing files between trees to make a test run. Run the suite in
the dev copy, or run it against the dev copy's files with an explicit
`PYTHONPATH` — never by mutating the deployed tree.

### 7b. Verify the IMPORT, not just the syntax, before restarting

`py_compile` passing and `grep -c 'def <newsymbol>'` returning 1 are both
insufficient: a module can import fine on its own while a *different* module's
`from X import newsymbol` fails, and a stale `__pycache__` `.pyc` can satisfy an
`import X` while still lacking the symbol.

```bash
cd <deployed-copy>
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
<venv>/bin/python -c "from <module> import <newsymbol>; print('IMPORT OK')"
```

Use the `from … import …` form (not bare `import`), because that is exactly what
fails when the two sides of a multi-file change are out of sync. A bare
`import a, b, c` can pass while `from a import f` still raises.

**Verify the whole symbol set, once, in one call.** For a change touching N files
with cross-imports, importing one module proves nothing about the others. Assert
identity across the importers so a mixed-tree load shows up here rather than at
the next restart:

```bash
<venv>/bin/python -c "
from <mod_a> import <sym>
from <mod_b> import <sym> as b_sym
assert b_sym is <sym>, 'cross-module symbol identity broken'
print('ALL IMPORTS OK')"
```

The `is` check is the point: the same name resolved from two different trees
produces two distinct objects, which is exactly the failure 7d describes.

### 7f. After the restart, prove the LIVE process reloaded — not just that it started

A clean start proves the file was importable, not that the running process picked
it up. Assert the loaded code, by behaviour, in the same environment the service
uses:

```bash
cd <deployed-copy> && <venv>/bin/python -c "
from <module> import <newhelper>
class A:
    def __init__(s): s._attr = '<system-reason>'
w = <newhelper>(A())
assert 'user' not in w.lower(), w          # the fix's actual contract
print('BEHAVIOUR VERIFIED:', w)"
```

Pick an assertion that is false on the OLD code and true on the new one — for an
attribution fix, "a system reason never renders as a user stop" is that
assertion. A restart that reports `active` while the session still fails on the
old symbol means the hosting process was not the one restarted (7c): the unit may
be `active` from the pre-edit start, so compare `ActiveEnterTimestamp` against the
moment you applied the patch.

### 7c. Restarting the service you are running inside kills your own session

On a host where the agent is served by the same systemd unit it is patching,
`systemctl --user restart <serve unit>` terminates the process backing the current
conversation. Symptoms: the tool call returns "session kernel died", or the reply
is replaced by a bare interrupt placeholder.

Before restarting, identify which unit is yours:

```bash
# Which unit's cgroup contains your own process tree, and its sys.path target?
ps -eo pid,lstart,etimes,cmd | grep -i '[h]ermes'
systemctl --user status <candidate units> --no-pager | head -30
```

The decisive fields are the **launch command's `sys.path` insertion** and the
process **start time** — a unit started before your first edit is running code
that predates it. If the unit hosting you must be restarted, hand the user the
exact command to run from their own shell; do not run it from a tool call.

**The hand-over is ONLY for the restart itself — keep diagnosing yourself.**
Delegating the restart does not license handing over every subsequent command.
Read-only inspection (`grep`, `ps`, `systemctl status`, `md5sum`, `ls`, `find`,
`git log`) changes nothing and must be run by you; a user who has just been asked
to run a one-line probe and is then asked to run five more will (correctly) say
"can't you look yourself?". Reach for the user's shell exactly once, for the
mutating step that would kill your own process.

**A broken IMPORT does not mean your tools are dead — try before delegating.**
When a half-applied patch makes the agent's own startup import fail, every tool
call can return the same `cannot import name ...` error before the command runs.
That is a real blocker for `terminal`/`execute_code`/`read_file`, but do **not**
conclude the whole surface is gone and route everything to the user: attempt the
reads anyway, because a diagnostic that avoids the failing import path may still
work, and only the ones that actually fail should be handed over. Report which
specific calls failed and with what error, rather than a blanket "I can't look".

### 7d. Two trees can both be on `sys.path` — a workspace snapshot and the repo

An install that was set up via the product's own environment/plugin installer can
carry a **second copy** of the source under an installs/workspaces path, and that
copy can be earlier on `sys.path` than the repo you are editing. Confirmed shape:

```
.../installs/<id>/environments/<hash>/workspace/agent/<file>.py   # often OLDER snapshot
.../.hermes/<project>/agent/<file>.py                              # the repo you edited
```

Consequences and the check to run before believing any diagnosis:

- The traceback's `(path/file.py)` names the module the interpreter *resolved*,
  which may not be the file your editor writes.
- `grep -rn '<newsymbol>' <root> --include='*.py'` across the whole install root
  will show BOTH trees; a symbol present in one and absent in the other is the
  signature of a cross-tree import.
- A workspace snapshot is **not** a symlink to the repo — syncing files into one
does not update the other, and it is not the thing to patch.
- Clearing `__pycache__` in the repo does nothing for a stale `.pyc` in the
  workspace tree; clear the installs root too when a stale-bytecode error refuses
  to clear.

### 7g. Multiple live processes may read DIFFERENT trees — land the patch in each

A host can run several units of the same product whose launch commands resolve
`sys.path` to different roots: one unit may `sys.path.insert(0, <repo>)` (reads
the git working copy you patched) while another runs from
`installs/<id>/environments/<hash>/workspace` (a separate snapshot). A patch
copied only into the repo reaches the first process on restart and NOT the second
— the fix appears half-live with no error anywhere. Before concluding the patch
"took", map every serving unit to its resolved tree:

```bash
for pid in $(systemctl --user show <unit1> <unit2> -p MainPID --value); do
  tr '\0' ' ' < /proc/$pid/cmdline | grep -o "sys.path.insert(0, '[^']*'"
done
```

If a unit resolves to a workspace snapshot rather than the repo, sync the changed
files into that snapshot too (`shutil.copy2`, then clear its module `.pyc` under
that tree's `__pycache__`) and verify byte-identity across both trees (`sha256`
match). Do not symlink the snapshot to the repo — the installer owns that
directory and will overwrite it on the next environment rebuild. The honest test
after this is per-process behaviour (7f), not one import check.

**Which tree each actor uses is visible in three places, and they can all differ.**
Do not infer coverage from the unit you think serves the user. Read, per process:
`tr '\0' '\n' < /proc/<pid>/environ | grep ^PYTHONPATH=` **and** the cmdline's
`sys.path.insert`. A TUI session launched from a shell can carry the REPO first on
`PYTHONPATH` while the systemd gateway for the same install runs from a generation
snapshot — so "my patch isn't live" may be true only for the messaging path, while
the session you are typing in is already patched. Ask the product's own planner
(`<cli> update --plan`, read-only) which services it sees and what code version
each reports running: it names the git SHA per service and beats reconstructing
the tree by hand.

### 7h. The bundled updater rebuilds the environment generation but does NOT rewrite a hand-written systemd unit — expect 203/EXEC

The product's own `update` is the correct way to make a generation-snapshot unit
pick up new source: its takeover step runs an *ordinary* venv sync, which builds a
fresh `environments/<uuid4>` and snapshots the working tree into its `workspace/`
via `_copy_core_inputs(source=<project root>)` — uncommitted patches included. It
then calls `collect_superseded_generations()` and reclaims the old ones.

What it does **not** do is edit a user-authored unit whose `ExecStart` hard-codes
the old generation path. `publish_launchers()` rewrites the launcher scripts it
owns, not your unit file. So after a successful update the gateway can sit in an
auto-restart loop:

```
Process: ExecStart=.../environments/<OLD-hash>/workspace/.hermes/bin/<cli> gateway run
         (code=exited, status=203/EXEC)
Active: activating (auto-restart)
```

Fix by pointing the unit at the generation the facts file now selects, then
`daemon-reload` + restart:

```bash
python3 -c "import json;print(json.load(open('<install>/facts.json'))['packages']['venv']['environment'])"
ls <selected-generation>/venv/bin/<cli>          # launcher lives in venv/bin, NOT workspace/.hermes/bin
sed -i 's|environments/<OLD-hash>/workspace/\.hermes/bin/<cli>|environments/<NEW-hash>/venv/bin/<cli>|g' ~/.config/systemd/user/<unit>
systemctl --user daemon-reload && systemctl --user restart <unit>
```

Three traps inside this recovery:

- **`MainPID=0` with the unit in `activating (auto-restart)` is the diagnosis**, not
  "I stopped it". `203/EXEC` means the executable path does not exist — check the
  target file before suspecting patch content.
- **A glob returning nothing does not prove the workspaces were reclaimed.** Shell
  leaves the literal pattern when nothing matches, so a `*/workspace/.hermes/bin/*`
  probe reads as "all destroyed". Iterate generations explicitly
  (`for g in …/environments/*/; do ls "$g"; done`). This misread cost a false alarm.
- **Verify the fresh generation actually carries the patch** instead of assuming the
  snapshot worked: grep your own new symbols under
  `environments/<new>/workspace/`. If present, the update achieved what hand-copying
  could not, and the snapshot never needs touching again.

Prefer this route over hand-syncing files into a snapshot (7g): the snapshot is
installer-owned, replaced on every rebuild, and a partial copy yields a
mixed-version tree.

### 7e. A rollback is not complete until the hosting process restarts

Copying the original files back (`cp *.orig`, `git checkout HEAD -- <files>`) and
re-running the import check can both report success while the live process still
holds the failed import in memory. If the error persists after a correct rollback,
the remaining variable is the **process**, not the file — restart the hosting unit
(7c) and re-test. Do not re-roll the files a third time; you will start reverting
working state.

## Rollback

```bash
cd <deployed-copy> && git reset --hard $(cat "$B/HEAD_before.txt")
# restore the DB only if the upgrade migrated it:
#   systemctl --user stop <units>; cp "$B/state.db.backup" <state.db>
```

For a *symbol-level* rollback (undo one bad patch without discarding an upgrade),
prefer `git checkout HEAD -- <file> …` over copying a saved `.orig`: the git form
is authoritative and cannot itself be stale. A backup made with `git show
HEAD:<file> > <file>.orig` is only as good as whatever `HEAD` pointed at when it
ran, so verify it still lacks your symbol before trusting it:

```bash
grep -c '<newsymbol>' "$B/<file>.orig"   # expect 0 for a pre-change backup
```

## Pitfalls

- **A stash that conflicts on exactly one hot file is the normal outcome, not a
  failure.** Report the per-file result ("5 clean, 1 conflict") instead of
  treating the conflict as a blocked upgrade.
- **The local patch that must NEVER be PR'd** is the instance-config class — it
  carries private topology (internal endpoints, tokens for self-hosted services).
  Expect it to keep re-applying forever; that is correct, not drift to clean up.
- **Do not re-apply a patch whose semantics upstream absorbed just because the
  token grep reads 0.** Refactors rename and restructure; check the call sites.
- **A patch whose PR is still OPEN is a permanent downstream obligation.** If the
  PR is unmerged, the fix is NOT in any upstream release, so every future upgrade
  re-applies it. Track it in PR monitoring so you notice when it lands and can
  retire the patch.
- **A source change never invalidates the environment stamp, so `pm install` is a
  no-op after patching source.** The generation stamp hashes the lockfile, extras,
  the pinned interpreter, and the PLUGIN member set — not core source. Editing
  `agent/*.py` leaves the stamp identical, `current=True`, and the sync
  short-circuits without rebuilding the snapshot. `repair` is worse here: it replays
  the recorded workspace rather than re-copying source. Only the ordinary sync inside
  the product's update takeover builds a fresh generation from the current tree (7h).
  Consequence: upgrading the repo by hand leaves a generation-snapshot unit serving
  stale code forever — silently, with no error anywhere, which looks exactly like a
  fix that failed to work.
- **Never pick a sibling environment as the pristine reference for restoring a
  snapshot without proving the siblings share a generation.** Copying three files
  from a neighbouring generation produced an `ImportError` on a constant its own
  `message_metadata.py` did not define — different source vintages despite matching
  mtimes. Verify the reference tree's internal imports resolve (grep the needed
  constant across candidates) or restore from VCS instead of another snapshot.
- **Lock the patch stack into a reachable commit before running the bundled
  updater.** Its autostash sweeps the working tree and its own code flags
  "uncommitted work riding an autostash across branches" as genuinely unsafe. A
  local commit plus annotated tag costs nothing, keeps the tree clean so no
  autostash fires, and makes the work unreachable-by-accident-proof (an
  already-reachable commit is left alone). This does not abandon patch mode: the
  per-PR split patch files stay on disk for re-evaluation at each upgrade.
