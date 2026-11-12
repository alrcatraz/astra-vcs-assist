# The filter-repo mechanics every case shares (Case E)

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
