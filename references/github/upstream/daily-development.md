# Working the fork day to day

## Daily development

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
unique, in `references/pr-briefing-workflow.md` )
