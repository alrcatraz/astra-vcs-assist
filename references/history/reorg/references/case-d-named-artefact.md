# Case D — remove a named artefact from every commit

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
