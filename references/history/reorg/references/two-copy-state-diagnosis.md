# Reading a two-copy repo without misdiagnosing it

A dev checkout and a production/deploy copy of the same repo hold *different* honest
states, and each reads as a fault from the wrong angle. Twice in one session the same
copy was called a breach first and only later recognised as legitimate — once for
"hand-editing the production copy" when it was an in-flight feature branch, once for real
divergence when the count was a local-path artefact. The rule is that the diagnosis
comes AFTER three reads, never before them.

## The three reads, in order

```bash
git remote -v             # skipped by habit; the one that explains the other two
git status -sb            # branch + tracking state
git reflog --date=iso -8   # who moved HEAD, and when
```

`git remote -v` leads because it is the check people skip and it is upstream of both
symptoms below: with a path as the remote URL, `status` is describing a comparison
two local copies, and no fetch will correct it.

## Symptom → actual state

| What you see | The tempting report | What it usually is | Verify with |
|:--|:--|:--|:--|
| Uncommitted files on the copy expected to be read-only | "production copy edited by hand — discipline breach" | An in-flight work line: a `fix/*`/`feat/*` branch with edits a session left open | Branch name + `reflog` dates (whose work, when); `git stash list` before moving |
| `ahead N` against "the remote" | "this copy has diverged / unpushed work" | `git remote -v` shows a **filesystem path** — the tracking ref compares the other local copy | `git remote -v` shows `/path/to/other/checkout`, not a URL; `git ls-remote <real-url>` for server truth |
| Tags refused with `would clobber existing tag` | "the rewrite did not land" | Local tags are un-fast-forwarded after a history rewrite | `fetch --tags --force`, then re-read `git ls-remote --tags` |
| `ahead N, behind N` on a copy fetched before the rewrite | "real divergence" | Stale remote-tracking ref holding pre-rewrite SHAs | `fetch --prune --tags --force`, re-read `status -sb` |

Every row resolves the same way: **read state, then name it.** An unfinished work line is
reported as unfinished work and left alone — stash rather than reset or discard it —
and the exclusion is stated explicitly rather than left silent.

## What NOT to do when a copy looks wrong

- **Do not commit, reset, or "clean up" someone else's open work line** to make a copy
  look tidy. It is mid-flight, not debris; the reflog tells you it has an owner and a
  session. Moving it requires `git stash push -u -m '<what it is> (<date>)'`, and the
  stash message is the only record of what was held back — so name the work, not the date.
- **Do not merge one local copy into the other** to resolve a mismatch. The remote is the
  source of truth for both copies; a copy-to-copy merge bypasses the review gate along
  with it. Align each copy to the server: `git fetch <real-remote> --tags --force` then
  `git reset --hard <remote>/<branch>`.
- **Do not trust an ahead/behind count before reading `git remote -v`.** The count is
  arithmetic against whatever the tracking ref points at — and that may be a directory on
  the same machine, in which case the number is not a divergence at all.
- **Do not treat a clean scan of one copy as the fleet being clean.** Each copy's `HEAD`
  must be scanned on its own; see `post-rewrite-propagation.md` for the sweep.

## Why the two confusions recur

Both come from reading a signal that is *local and relative* as if it were *authoritative*:
`git status` and `ahead N` describe a comparison against a tracking ref, which is only as
correct as the last fetch and the remote URL. Server truth lives in `git ls-remote <url>`
and per-copy truth in `git status`/`reflog` — naming which of the three you are quoting is
what keeps a diagnosis honest.
