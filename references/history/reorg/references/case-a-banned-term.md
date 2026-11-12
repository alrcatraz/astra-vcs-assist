# Case A — purge a banned term or a superseded approach

## Case A — purge a banned term or superseded approach

When the user says an approach "should not appear in any deck, paper, or git
record" (a shortcut taken to get a presentable prototype, a deprecated
algorithm, a de-branded name), that is a multi-artefact purge, not a rename.
Settle the tier before touching anything: the tiers differ by an order of
magnitude in blast radius.

## Tiers

| Tier | Scope | Cost |
|:--|:--|:--|
| **A — presentation surface** | decks, papers, handover PDFs, README prose, code comments | cheapest; no behaviour change |
| **B — working tree** | delete/rename files, regenerate generated docs, prune index entries naming the deleted modules, clean untracked artefacts | code must keep identical behaviour; build + test must stay green, and the docs build must still resolve every index entry (a `::: module` line for a deleted module fails it) |
| **C — history** | `git filter-repo` over all history | every hash changes; every clone, fork and remote must be coordinated |

Default to A + B. **Skip C when the publication-facing mirror does not exist
in a clean state yet** — a repo seeded fresh at publication time never carries
the term, so rewriting internal history buys nothing and risks divergence.
State that decision explicitly so a later session does not reopen it.

**Say the contrapositive out loud before committing tier A+B.** A cleanup commit is itself a
record: its diff names every deleted file and its message describes the removal, so
`git log` now documents exactly what the user wanted forgotten. When their bar is "must not
appear in ANY git record" (not "must not be in the deck / the public mirror"), A+B cannot
meet it and only C can. Put that trade-off in front of them rather than committing and
letting them discover it in the log; two facts usually decide it:

- **A rewrite preserves chronology.** `git filter-repo` keeps every commit's author and
  committer date; only commits that become empty (the ones that existed solely to add the
  purged files) are pruned — the surviving commits keep their original timestamps, so
  "as long as it does not change the dates" is satisfied.
- **It is cheapest right now.** Cost scales with clones, forks, collaborators and published
  refs; a repo with one checkout and no second clone will never be cheaper to rewrite.

When they choose C, the mechanics live in `filter-repo-scoping-traps.md`
(mode selection, replace-text traps, audit shapes) and
`post-rewrite-propagation.md` (force-push, local reflog/gc retirement, copies).

## Decide rename vs delete by usage, not by name

A file whose *name* carries the term may implement the generic mechanism the
project still needs. Grep its references first (`grep -rn <Type> --include=*.cs
--include=*.tscn .` excluding vendor dirs); if another type constructs it or it
implements an interface, it is load-bearing — **rename** it and keep behaviour
identical. Only files whose whole purpose is the banned approach get deleted.

Name forms a term hides in, check all of them:

- file and directory names, plus generated sidecars (Godot `.uid`, `.meta`)
- type name, enum members (`PolicyMode.Bc` → `.Onnx`)
- `[Export]`ed property names and private fields (`_bc` → `_policy`)
- helper methods (`ResolveBcModelPath` → `ResolveModelPath`)
- CLI flags and `choices=[...]` lists shared between C# and Python
- default resource paths (`res://bc_policy.onnx` → `res://policy.onnx`)
- doc comments, log strings, docstrings, generated API pages
- `.tscn`/scene files: check them **before** renaming an `[Export]` property —
the engine serialises by property name and a silent mismatch leaves the scene
bound to a property that no longer exists

## Replace with counted assertions, not blind `sed`

Run a small Python script (write it locally, `scp` it, run it with cwd = repo
root) built from `(relpath, old, new, expected_count)` tuples. Each tuple
asserts the occurrence count and aborts the pass on mismatch, so an unexpected
code shape stops the run instead of half-editing. Identifier-shaped tokens get
a second pass with word boundaries (`re.subn(r"\b_bc\b", ...)`), because plain
string replacement mangles longer identifiers that contain them.

Finish every pass with a residual audit that excludes vendor code — third-party
addons are not yours to scrub for wording:

```bash
git grep -niE '<term>|bc_policy|BcInference|_bcReady' -- '*.cs' '*.py' '*.md' \
  | grep -v 'addons/<vendor>/'
```

## Verify the build that actually contains the change

Building the test project often compiles only the dependency-free core; the
engine/app assembly is a separate project and a rename in the engine-facing
code is **not compiled at all** by `dotnet test <Core>.Tests.csproj`. Build both,
then run the thing once and grep for the runtime line that proves the renamed
path resolved (e.g. `policy mode=Onnx ... inference ready=True obs_dim=399`).
Record the test count before and after — identical pass counts are the evidence
that behaviour was preserved.

## The ban covers commit messages

A conventional-commit subject or body that names the purged term re-introduces
it into the permanent record. Write the message in terms of what the code now
does ("generalise the ONNX policy seam" / "drop the superseded export scripts"),
never in terms of the removed approach.

## Safeguard

Branch + tag before the first edit (`git tag --no-sign -m <why> <name>` — an
annotated tag needs a message, and `tag.gpgsign` makes a bare `git tag` fail
with `Terminal is dumb, but EDITOR unset`). Leave the tag unpublished; it is
the rollback path for a purge that turns out to overreach.
