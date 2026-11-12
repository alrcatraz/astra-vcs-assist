# Case B — scrub a term or artefact out of every commit

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
