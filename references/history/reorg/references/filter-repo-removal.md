# Removing a term, file or artefact from a full history

One home for every variant of the same operation. Pick the case, then follow its section — each section
is written to be copy-paste complete on its own, so the backup/verify/push blocks repeat by design
rather than sending you to another file mid-operation.

## Which case

| Situation | Case | Mode |
|:--|:--|:--|
| A term must disappear from messages **and** content everywhere | A — term purge | `--replace-text` + `--replace-message` |
| The term also leaked into file **names** | B — scrub term or artefact | adds `--invert-paths`/`--path-rename` |
| Whole files must go (a memo, a credential file, a directory) | C — purge file or term | `--invert-paths --path …` |
| One named artefact (a trace, a dataset) must be removed from every commit | D — artefact removal | `--invert-paths` on the exact path, then verify counts |
| You need the mechanics: what filter-repo does, where it rewrites, how to scope | E — mechanics | reference, not a recipe |

## Non-negotiables, whatever the case

- **Back up the whole repo first** — a bundle with `--all` is the only rollback that survives a rewrite.
- **Decide the disclosure plan before the first rewrite commit**, not after: the rewrite is the clip.
- **A rewrite renumbers every commit** — propagate to clones, pins, submodule pointers and documented SHAs
  in the same pass; nothing in the error messages points back to the rewrite.
- **`--force-with-lease`, never `--force`**, and prove the remote head with `ls-remote` afterwards.


## Case E — the filter-repo mechanics

Use when a word, approach or file must disappear from **every commit**, not
just from the working tree — and the repository is still small, private and
uncollaborated, so rewriting is cheap now and expensive later.

## Decide before you touch anything

- **A commit that removes the term documents the removal.** Deleting the files
  and committing leaves their names and contents reachable in the log. "Commit
  the cleanup" and "erase the record" are opposites; pick one deliberately.
- **Rewrite now or seed later.** Rewriting a 50-commit private repo costs one
  afternoon. The same rewrite after clones, mirrors and CI references exist
  costs a coordination effort. If the public repo does not exist yet, seeding a
  fresh history at publish time is a legitimate alternative — say which path you
  are taking and why before starting.
- **Refs can leak the term too.** Tags and branch names (`pre-<term>-removal`,
  `chore/remove-<term>`) carry it; delete those refs *before* the rewrite so
  they are not rewritten and re-published.

## Safeguard (do this first, every time)

```bash
git bundle create ~/backups/<repo>-$(date +%Y%m%d-%H%M).bundle --all
# copy it to a DIFFERENT machine, then prove it restores:
git clone --mirror <bundle> /tmp/verify && git -C /tmp/verify rev-list --all --count
```

A same-machine copy is not a backup. Also confirm nothing else needs the old
hashes (other clones, CI caches) — if something does, stop.

## Do the rewrite on a clone, never on the working repo

`filter-repo` refuses a non-fresh clone (use `--force` on later passes) and
removes `origin` when it runs, so work in a mirror clone and push the result
back from the real repository afterwards (its credential helper is the one that
works).

```bash
git clone --mirror <repo> /tmp/rw/repo.git && cd /tmp/rw/repo.git
git tag -d <leaky-tag>               # ref names leak too
```

## Two passes: paths, then text

`--invert-paths` and `--path-rename` cannot be combined, so run them
separately.

**Pass A — delete files that must never have existed.**

```bash
git filter-repo --force --invert-paths \
  --path path/to/script_a.py --path path/to/script_b.py
```

**Pass B — rename a file across history, then scrub text.** A file whose *name*
carries the term leaks even when its contents are clean; rename it in every
commit, including sidecars:

```bash
git filter-repo --force \
  --path-rename 'old/Name.cs:new/Name.cs' \
  --path-rename 'old/Name.cs.uid:new/Name.cs.uid' \
  --replace-text /tmp/replace.txt \
  --replace-message /tmp/messages.txt
```

## The `--replace-text` traps that cost a rebuild

1. **Every rule must be one line.** A wrapped literal (a phrase broken across
   two lines, `==>` on the second) makes the first line a *match with empty
   replacement*, and filter-repo writes the literal string `***REMOVED***` into
   every blob it touches. The result compiles and reads like corruption. Audit
   the rules file before running: `grep -v '==>' rules.txt` must print nothing.
2. **Order matters, longest phrase first.** Put specific phrases (`the X policy`)
   before the word-boundary catch-all (`\bX\b`), then add a repair rule for the
   duplication the catch-all creates (`policy policy==>policy`).
3. **Identifiers inside prose and code need their own rules** — class names,
   config keys, CLI flags, enum members. One catch-all on the acronym is not
   enough when the code spells it out.
4. **Commit messages are separate.** Bodies describe what was built; scrub them
   with `--replace-message` (same syntax) or `--message-callback`, and *drop*
   whole bullet lines that only describe the removed files rather than
   rewriting them into nonsense.

## Verify the rewrite before pushing

```bash
git rev-list --all --count                                   # same count unless commits emptied
git log --format='%h %ai | %ci | %s' | head -3                # dates unchanged
# no term anywhere in any commit:
git grep -inE '<term>|\b<Abbr>\b|<identifier>' $(git rev-list --all) -- '*.cs' '*.py' '*.md'
git log --all --format='%H%n%B' | grep -vE '^[0-9a-f]{40}$' | grep -inE '<term>'
git grep -c '\*\*\*REMOVED\*\*\*' $(git rev-list --all)  # must be 0
git log --all --name-only --pretty=format: | sort -u | grep -i '<term>'   # no leaky paths
```

Then clone the rewritten history into a scratch directory and **build and run
the test suite there** — the rewrite is a content change, and only a real build
proves the tree still compiles.

## Make the rewrite the final state, not a starting point

Your working tree may hold edits that duplicate what the rewrite already did.
Do not re-apply them: take the rewritten tree as authoritative, `diff` it against
the working copy, and commit only the genuine residual difference.

## After the force-push

```bash
git push --force origin main development
git push --force --tags origin
```

- **Local reflogs still hold the old commits.** `git reflog expire --expire=now
  --expire-unreachable=now --all && git gc --prune=now`, then prove it:
  `git cat-file -e <old-sha>` must fail.
- **The forge keeps them alive through PR refs.** A merged PR's
  `refs/pull/N/head` still points at a pre-rewrite commit and anyone with repo
  access can fetch it. Delete the PR, or record the residual exposure
  explicitly — do not report the history as clean while that ref exists.
- Server-side object GC is the host's business; refs being clean is what the
  rewrite guarantees.

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

## Case B — scrub a term or artefact out of every commit

For when a term, file, or approach must not appear in the repository's record
at all — not in the working tree, not in old blobs, not in file names, not in
commit messages.

## Decide the target before touching anything

A normal cleanup commit **documents** the removal: its diff shows the deleted
file names and the old blobs stay reachable from every earlier commit. So
"stop using it" and "it must not appear in any record" are different jobs, and
the second needs a history rewrite. Do it while the repository has one clone
and no collaborators; once others have cloned, or a mirror exists, the cost
multiplies.

## Prepare

```bash
git bundle create ~/backups/<repo>-$(date +%Y%m%d-%H%M).bundle --all
# copy the bundle to a SECOND machine — a backup on the same disk is not one
uv tool install git-filter-repo        # PEP 668 blocks `pip install --user`
git filter-repo --version
```

Work on a mirror clone of that bundle, never on the live working copy. Delete
any branch or tag whose **name** leaks the term first: refs are rewritten in
content but never renamed, and a tag called `pre-<term>-removal` defeats the
exercise.

## Rules file — one line per rule

Every line must be `match==>replacement`. **A line without `==>` counts as an
empty replacement and writes `***REMOVED***` into the matching text across the
whole history** — the classic way to corrupt a generated doc while believing
the rules were literal. Multi-line literals are the trap: keep one rule per
line. Put longer, more specific literals before the generic `\bTERM\b` rule,
and add a `word word==>word` repair rule last for duplications the generic rule
creates ("the TERM policy" → "the neutral neutral").

```text
Specific phrase containing TERM==>replacement phrase
IdentifierThatEmbedsTerm==>NewIdentifier
regex:\bTERM\b==>neutral-word
neutral-word neutral-word==>neutral-word
```

## Two passes: remove, then rename

`--path-rename` and `--invert-paths` cannot be combined. Pass 1 removes files
that should not exist at all; pass 2 renames files that should keep existing
under a neutral name:

```bash
git filter-repo --force --invert-paths --path a/old_thing.py --path b/old_thing_v2.py
git filter-repo --force \
  --path-rename 'src/OldThing.cs:src/Thing.cs' \
  --path-rename 'src/OldThing.cs.uid:src/Thing.cs.uid' \
  --replace-text rules.txt \
  --message-callback '
import re
out = []
for line in message.decode("utf-8").splitlines():
    low = line.lower()
    if "old_thing_v2" in low or "old_thing.py" in low:
        continue                      # drop the whole bullet about a deleted file
    l = re.sub(r"\bTERM\b", "neutral", line)
    out.append(l)
return ("\n".join(out) + "\n").encode("utf-8")
'
```

Dropping whole lines is usually cleaner than substituting inside a message that
describes a deleted file — the sentence has no referent afterwards.

## Audit before pushing

```bash
# blobs in EVERY commit, not just HEAD
git grep -inE "\bTERM\b|IdentifierThatEmbedsTerm" $(git rev-list --all) \
  -- '*.cs' '*.py' '*.md' | grep -v 'addons/'          # exclude vendor
# messages — drop the hash lines first, they match by accident
git log --all --format="%H%n%B" | grep -vE '^[0-9a-f]{40}$' | grep -inE "\bTERM\b"
# file names ever present
git log --all --name-only --pretty=format: | sort -u | grep -i term
# nothing corrupted, nothing lost
git grep -c '\*\*\*REMOVED\*\*\*' $(git rev-list --all)
git rev-list --all --count          # compare with the pre-rewrite count
git log --format="%ai | %ci" | head # author and committer dates are preserved
```

Expect false positives: `imitation` inside `limitation`, `BC` inside `RGB`, and
any two-letter token inside a hex hash. Use word boundaries and exclude
vendored directories rather than "fixing" them.

`--prune-empty` (default auto) drops commits that became empty, so the commit
count can legitimately fall; investigate any other change.

## Finish the job locally

filter-repo strips `origin`. Push from the clone that actually has working
credentials — a bare temp mirror often resolves a different credential helper —
by fetching the rewritten refs into the original clone as a temporary local
remote, then force-pushing from there.

```bash
git reflog expire --expire=now --expire-unreachable=now --all
git gc --prune=now
git cat-file -e <old-sha>            # must fail, or the history is still reachable
```

The reflog keeps every pre-rewrite commit reachable; without expiry `git
reflog` hands the old history straight back and the rewrite has achieved
nothing locally. Move any backup branch to its rewritten counterpart (or delete
it) before the gc.

On hosts with `tag.gpgsign=true`, `git tag -f` dies with `Terminal is dumb, but
EDITOR unset`; use `git tag --no-sign -f -m "<message>" <name>`.

## Server side is a separate problem

A host keeps pre-rewrite commits reachable through pull-request refs
(`refs/pull/N/head`). Deleting the PR is usually the only way to drop them; the
host's own object GC is separate and may need an admin action. Say this to the
user plainly instead of implying the rewrite covered it.

## Case C — purge a term or file from an entire history

Flattening commits (the main body of this skill) rearranges history. This file
covers a different job: making a name, file or phrase **not exist anywhere in
the repository's past**, while keeping the real commits, messages and dates.

Reach for it when the user says an approach, tool or artefact "must not appear
in any git record" — a shortcut taken early, a superseded sub-project, a name
that would embarrass them in a public mirror.

## Decide the scope first

Three levels, different costs. Get the user to pick explicitly:

| Level | What changes | Cost |
|---|---|---|
| presentation only | deck/paper/handover doc stop mentioning it | minutes |
| working tree | files deleted, docs rewritten, one commit | minutes |
| history | every commit rewritten, all hashes change, force-push | an hour, unrecoverable without a backup |

Committing the cleanup is **not** level 3: a commit that deletes the files
*records* them in its diff, and the old blobs stay reachable. Say that out loud
before starting level 3, because it is the reason the user is being asked.

## Back up before anything

```bash
git bundle create ~/backups/<repo>-$(date +%Y%m%d-%H%M).bundle --all
git clone --mirror ~/backups/<repo>-….bundle /tmp/verify && \
  git -C /tmp/verify rev-list --all --count      # must equal the source count
```

A bundle on the same machine is not a backup — copy it to a second host. Then
work on a **mirror clone**, never on the working repository.

## Audit what actually leaks

```bash
git log --all --name-only --pretty=format: | sort -u | grep -iE '<pattern>'
git log --all --format='%H%n%B' | grep -vE '^[0-9a-f]{40}$' | grep -inE '<pattern>'
git grep -inE '<pattern>' $(git rev-list --all) -- '*.cs' '*.md' '*.py'
```

The second command matters: commit **bodies** carry far more leaked prose than
subjects, and `--grep` matches bodies too, so a subject-only scan under-reports.

## Rules for the rewrite

**Every `--replace-text` rule must be a single line.** A literal that spans two
lines has no `==>` on its first line, so filter-repo treats it as a
match-with-empty-replacement and injects the string `***REMOVED***` into every
file containing that line — silently, in every commit. This is the expensive
trap: it looks like a successful rewrite and the damage only shows in a later
diff. Before running, assert the file is well formed:

```bash
grep -vn '==>' replacements.txt && echo 'MALFORMED — would inject ***REMOVED***'
grep -c '==>' replacements.txt
```

Then, if it does happen: **rebuild from the pristine bundle**, do not patch the
resulting history. Patching cannot recover the intermediate blobs.

**`--invert-paths` and `--path-rename` cannot be combined** — filter-repo
refuses the invocation. Run two passes on the same clone with `--force`:

```bash
# pass 1 — drop files that must not exist
git filter-repo --force --invert-paths \
  --path old/tool.py --path old/tool_v2.py

# pass 2 — rename a file that must exist under a neutral name in EVERY commit
git filter-repo --force \
  --path-rename 'src/OldName.cs:src/NewName.cs' \
  --path-rename 'src/OldName.cs.uid:src/NewName.cs.uid' \
  --replace-text replacements.txt \
  --message-callback '<python that rewrites `message` bytes>'
```

`--path-rename` is what removes a *filename* leak; text replacement alone leaves
the old name visible in every historical tree listing.

**Delete refs whose NAMES leak before rewriting** — a backup tag or work branch
called `pre-<term>-removal` re-introduces the term in the ref namespace. Keep
the bundle instead of a self-describing tag.

**Order replacements longest-first.** `BcInference` → `OnnxPolicy` before a
catch-all `\bBc\b` → `Onnx`; otherwise the broad rule mangles the identifier it
was meant to leave alone. Add `\b` word boundaries to letter-only tokens, or
`\bBC\b` will rewrite `RGBCamera` in vendor code.

**Never rewrite vendor/upstream files.** A third-party addon's docstring that
happens to contain the word is not the user's shortcut; leave those paths alone
and say so in the report.

Dates: filter-repo preserves author and committer timestamps on every surviving
commit — hashes change, dates do not. Commits that become empty are pruned, so
the commit **count** can fall even though no timestamps shifted.

## Verify before pushing

```bash
git rev-list --all --count
git log refs/heads/<main> --format='%h %ai | %ci | %s' | head -3   # dates intact
git grep -inE '<pattern>' $(git rev-list --all) | grep -v <vendor-dir>   # must be empty
git log --all --name-only --pretty=format: | sort -u | grep -i '<pattern>'  # paths
git grep -c '\*\*\*REMOVED\*\*\*' $(git rev-list --all)          # must be 0
```

Then build and test the rewritten tree in a throwaway clone (`dotnet build`,
`dotnet test`, whatever the project uses) — a rewrite that compiles nothing is
not verified.

## Push, then make the old objects unreachable

```bash
git fetch --force <local-mirror> '+refs/heads/*:refs/remotes/rewritten/*'
git push --force origin refs/remotes/rewritten/main:refs/heads/main …
```

Pushing **from the working repo** beats pushing from the mirror: the mirror has
no stored credentials and its credential helper may fail (a .NET-based helper
needs a runtime the mirror's environment lacks). The working repo already
authenticates.

Afterwards the old commits are still reachable through the reflog:

```bash
git reflog expire --expire=now --expire-unreachable=now --all
git gc --prune=now
git cat-file -e <old-sha>     # must now fail
```

Also re-point any remaining local branch that still tracks a pre-rewrite commit,
and delete the temporary mirror remote.

## What stays dirty

- Server-side: a merged-PR ref (`refs/pull/N/head`) can keep the pre-rewrite
  commit fetchable even after a force-push, and the host's own object store only
  drops it on its next GC. Report this instead of implying the server is clean.
- A fresh public mirror created later should be **seeded** from the cleaned tree
  (squashed or curated commits), not pushed from a history you have not audited.

## Case D — remove a named artefact from every commit

---
license: MIT
---

# Removing a named artefact from every commit

Use when the user wants something gone from the record — a file, an identifier,
a phrase, a line of a commit message — across **all** history, while the
surviving commits keep their original dates. This is a different job from
re-grouping commits (`git-history-reorg`'s main body): nothing is being
reordered, only scrubbed. Same end state: a force-push.

Decide the scope before touching anything — it changes the whole plan:

| Ask | Consequence |
|:--|:--|
| Must the internal repo be clean, or only the future public one? | Internal ← rewrite now. Public only ← seed the public repo from a clean tree; leave internal history alone. |
| Are there clones, collaborators, or a mirror? | Each one needs re-cloning or re-pushing; rewrite cost grows fast, so rewrite while the repo is still single-copy. |

A commit that *deletes* the artefact is not a fix. It leaves the filename, the
old blob and the removal diff in the log — committing the cleanup and removing
the trace are opposite operations. Say this out loud before the user picks.

## 1. Back up, then verify the backup restores

```bash
git bundle create ~/backups/<repo>-$(date +%Y%m%d-%H%M).bundle --all
```

Copy the bundle to a **second machine** (a copy on the same host is not a
backup), then prove it: `git clone --mirror <bundle> /tmp/verify && git -C
/tmp/verify rev-list --all --count` must print the same commit count as the
original. Do this before any rewrite; filter-repo is fast and destructive.

## 2. Install the tool

`git filter-repo` is not part of git. On a managed Python (PEP 668) `pip
install --user` is refused; use an isolated tool install:

```bash
uv tool install git-filter-repo      # binary lands in ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"
```

## 3. Rewrite on a clone, never in the working repo

```bash
git clone --mirror <repo> /tmp/rw/repo.git && cd /tmp/rw/repo.git
git tag -d <backup-tag-named-after-the-artefact>     # ref NAMES leak too
```

**Every ref name is part of the record.** A backup tag or branch whose name
contains the thing being removed must be deleted before rewriting, or the
positive-looking history ends up with it stamped on a ref.

## 4. Two passes — the flags cannot be combined

`--invert-paths` and `--path-rename` are mutually exclusive. Do removals
first, renames second (the second pass needs `--force`):

```bash
# pass A — delete files from every commit
git filter-repo --force --invert-paths \
  --path path/to/one.py --path path/to/two.py

# pass B — rename files, scrub text, scrub messages
git filter-repo --force \
  --path-rename 'sim/scripts/Old.cs:sim/scripts/New.cs' \
  --path-rename 'sim/scripts/Old.cs.uid:sim/scripts/New.cs.uid' \
  --replace-text /tmp/replace.txt \
  --message-callback '<python operating on `message` bytes, returns bytes>'
```

Rename **every historical path** of a moved file: a directory reorg leaves the
old location in older commits, and `.uid`/`.meta` sidecars must move with it,
or the filename survives in the tree at that revision.

## 5. The `***REMOVED***` trap (read before writing the rules file)

`--replace-text` takes one rule per line, `literal==>replacement` or
`regex:<pattern>==>replacement`. **A line with no `==>` is a rule whose
replacement is empty, and filter-repo renders that as the literal string
`***REMOVED***`** — in every blob it matches, in every commit.

So a multi-line literal (wrapping a long sentence over two lines in the rules
file) silently splits into one good rule and one `***REMOVED***` rule that
stamps your source files with junk. Guard mechanically before every run:

```bash
grep -vn '==>' /tmp/replace.txt && echo '!! line without ==> — ABORT' || echo 'rules well-formed'
```

If it already happened, do **not** patch the result: restore the pristine
bundle and re-run with well-formed rules. Repair passes over a botched rewrite
cannot prove the intermediate commits are clean.

## 6. Rules that catch the variants

Prose about the removed thing rarely uses one spelling. Cover, in this order
(most specific literal first, blanket regex last):

```
OldClassName==>NewClassName
old_module_v2==>new_module
old_file_name==>new_name
some_flag=old==>some_flag=new
In `old` mode==>In `new` mode
regex:`old`==>`new`
regex:(?i)behaviou?r(?:al)?[- ]cloning==>policy training
regex:\boldword\b==>replacement
policy policy==>policy          # collapse duplicates the blanket rule created
```

`behaviou?r(?:al)?[- ]` matters: `behavior`, `behaviour`, `behavioral`,
`behavioural`, and hyphenated `behavioural-cloning` are four different strings.
A blanket `\bold\b` rule will produce `the policy policy` wherever the prose
was `the old policy`; keep a dedup rule at the end and re-audit.

## 7. Messages: drop whole lines, not just words

A commit body that exists only to describe the removed work should lose the
line entirely; rewording it produces a sentence about something that no longer
exists. `--message-callback` receives `message` as bytes and must return bytes:

```python
import re
out = []
for line in message.decode("utf-8").splitlines():
    low = line.lower()
    if "old_module" in low or "old_file" in low:
        continue                       # line only existed to describe it
    l = re.sub(r"\bOLD\b", "NEW", line)
    out.append(l.replace("policy policy", "policy"))
return ("\n".join(out) + "\n").encode("utf-8")
```

## 8. Audit with word boundaries, not naked substrings

```bash
# blobs, every revision
git grep -inE '\bimitation\b|\bcloning\b|\bBC\b|old_file_name|OldClassName' \
  $(git rev-list --all) -- '*.cs' '*.py' '*.md' '*.toml' '*.cfg*'

# messages, with hash lines filtered out
git log --all --format="%H%n%B" | grep -vE '^[0-9a-f]{40}$' \
  | grep -inE '\bBC\b|old_module'
```

Two false-positive classes that will send you chasing nothing: **substrings
inside words** (`limitation` contains `imitation`; `RGB` contains `BC`) and
**commit hashes** (any 40-hex line matches a two-letter pattern by chance).
Always use `\b` and filter the hash lines.

## 9. Dates and empty commits

filter-repo preserves **author and committer dates** on every surviving
commit; only hashes change. Commits that become empty after a path removal are
pruned, so the count can drop — that is a vanished commit, not a shifted date.
Verify by diffing `git log --format='%h %ai | %ci | %s'` before and after.

## 10. Push from the repo that has credentials

The mirror clone in `/tmp` has no credential helper state and dies with
`could not read Username for '<server>'`. Push from the original working
repo instead:

```bash
cd <real-repo>
git remote add rewritten /tmp/rw/repo.git
git fetch --force rewritten '+refs/heads/*:refs/remotes/rewritten/*' '+refs/tags/*:refs/tags/*'
git push --force origin refs/remotes/rewritten/main:refs/heads/main \
                    refs/remotes/rewritten/development:refs/heads/development
git push --force origin refs/tags/<tag>
```

If `tag.gpgsign=true` is set globally, `git tag` refuses with "Terminal is
dumb, but EDITOR unset": pass `--no-sign -m "…"`.

## 11. Make the old commits unreachable locally

Rewriting refs is not enough — reflogs keep the old commits alive and
recoverable:

```bash
git branch -f <local-backup-branch> <rewritten-sha>   # anything still pointing at pre-rewrite commits
git reflog expire --expire=now --expire-unreachable=now --all
git gc --prune=now
git cat-file -e <old-sha> && echo 'STILL REACHABLE' || echo 'gone'
```

Run the `cat-file -e` assertion on the old `HEAD` and the old default-branch
tip; both must fail.

## 12. Server-side residue to report, not silently accept

- Forgejo/GitHub keep `refs/pull/<n>/head` alive for merged PRs; that ref still
  points at a pre-rewrite commit and stays fetchable. Tell the user; deleting
the PR (or letting them) is their call.
- Server object storage keeps unreachable objects until the host's own GC.
- Any other clone of the repo still has the full old history.

## 13. Reconcile the working tree afterwards

The rewritten tree will not match your handwritten cleanup exactly — files you
never touched can differ because a replacement hit prose inside them. Diff the
rewritten tree against the working copy, read each difference, and decide:
accept the rewritten wording, or land one small convergence commit with a
message that names nothing that was removed. Never restore the old file to
"keep my edits" without checking which side is cleaner.
