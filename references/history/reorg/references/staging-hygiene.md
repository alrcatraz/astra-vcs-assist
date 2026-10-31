# Staging Hygiene in a Shared Working Tree

Rule set for committing in a repo that OTHER workers also edit — a skills
library, a dotfiles repo, a shared checkout on a fleet machine. Such a tree
carries foreign uncommitted edits at all times, and the tracking commands
treat a file as one unit, so the risk is not `git add -A` alone.

## The failure the command set invites

`git add <file>` stages that file's **whole** diff. A file you legitimately
touched may also hold another worker's pending edits, and those hunks ride
into your commit under your message — the commit is scoped by path but not by
content. A file count that matches your change set is therefore NOT proof the
commit is clean.

## Procedure

```bash
git add <explicit paths>                # never -A / . in a shared tree
git diff --cached -- <path>             # every hunk shown must be yours
#   ^ the per-file check is the one that catches foreign hunks
git commit -m '<msg>' -- <explicit paths>   # name the paths twice: stage + commit
git show --stat HEAD                        # file list must equal your change set
```

Read the staged diff of **every** file you touched, not just the ones you
suspect. A file that is only half yours looks identical to a file that is
entirely yours in `git status`.

When your own fresh edit is invisible in `git diff`: either the write never
landed (a remote/base64/heredoc write can exit 0 having written nothing —
verify read-back byte-exact before believing "written"), or the file was
already partially staged so the edit shows under `git diff --cached` while
older staged hunks show under plain `git diff`. Check both sides plus the
`git status --short` column positions before concluding what changed.

## Recovery without losing the other worker's work

```bash
git reset --soft HEAD~1                  # uncommit; index and disk untouched
git restore --staged <foreign-file>      # drop that file from the commit
git add <every intended path>            # reset --soft keeps the OLD tree in the index
git commit -m '<msg>' -- <explicit paths>
git reset                                # remaining backlog back to unstaged
```

- **Never `reset --hard` here** — it destroys exactly the uncommitted work the
  scoping was protecting.
- After `git reset --soft`, the index still holds the previous commit's tree:
  re-add every path you intend to commit, or the new commit silently captures
  pre-edit bytes. Tells: a file you believe you just committed still shows as
  modified; `git show --stat HEAD` is not the shape you expected.
- Assert on the **committed blob**, not the working tree, when the commit's
  meaning depends on specific bytes (`git show HEAD:<path> | grep -n '<line>'`).

## Deletion variant

`git rm <path>` refuses on a file with staged/unstaged modifications in a
dirty tree: stage the deletion and commit scoped (`git commit -- <path>`)
rather than forcing it through a wide `git add`.

## Verify against the server, not the cache

`origin/<branch>` is a cache of the last successful fetch, not the remote's
state — a failed fetch in a shallow clone leaves it pinned and a successful
push then reads as reverted. Confirm remote state with
`git ls-remote <remote> refs/heads/<branch>`, or the forge API, before drawing
any conclusion about what the remote holds.
