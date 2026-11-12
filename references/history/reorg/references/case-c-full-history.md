# Case C — purge a term or file from an entire history

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
