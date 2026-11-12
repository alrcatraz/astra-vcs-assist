# A PR parked by upstream god-file decomposition

## Handling a PR parked by upstream god-file decomposition

When an open PR goes quiet with no conflicts initially, then later flips to
`mergeable: false`, the usual cause is upstream decomposing the giant file you
touched ("god-file shard" campaigns). Investigate via
`references/pr-conflict-investigation.md`; the decision steps specific to this
situation are below (mirrored in full detail in
`references/pr-conflict-investigation.md` ).

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
