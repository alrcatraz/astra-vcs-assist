# Post-rewrite propagation and the fleet-wide sweep

A history rewrite is finished when EVERY copy and every SIBLING REPO is clean — not when
the pushed branch is. Two distinct failure modes live past the push.

## 1. Re-point every copy of the rewritten repo

A force-push leaves every other checkout holding the abandoned line. The rewrite is not
done until each copy — dev checkout, production/deploy copy, and any machine that had the
repo cloned — is re-pointed and its tree re-verified.

- **Fetch with `--tags --force`, then `reset --hard <remote>/<branch>`.** A plain
  `git fetch --tags` REJECTS the rewritten tags with `would clobber existing tag`, because
  the local tags still point at the old line. `--force` is required. `reset --hard` is the
  correct verb — the superseded commits are not to be merged.
- **The production/deploy copy takes a rewrite by reset, never by merge.** It is a
  consumer of the remote, not a peer of the dev checkout.
- **Rewrite FIRST, reconcile copies SECOND.** Copies reset before the rewrite lands simply
  re-diverge. Order: rewrite → push → re-point copies → verify each copy's tree.
- **Stash before resetting a copy that has uncommitted work — and record what it was.**
  Those changes sit on the abandoned baseline and `reset --hard` discards them silently.
  `git stash push -u -m "wip: <what it is> (<date>)"` preserves them; the stash entry is
  what lets a later session find the work again. Report the stashes you left behind.
- **Scan each copy's `HEAD`, not just the remote.** A clean remote proves the remote. Only
  a per-copy tree scan proves that copy stopped serving the leak.

### Phantom divergence after a rewrite

A copy whose remote-tracking ref was last fetched before the rewrite reports
`ahead N, behind N` against a remote that is actually identical — the tracking ref holds
pre-rewrite SHAs. Run `git fetch --prune --tags --force` and re-read `git status -sb`
BEFORE diagnosing a divergence. Do not go hunting for commits that are not missing.

### A tracking ref may point at a local PATH

`git remote -v` can show a remote whose URL is a directory on the same machine
(`/path/to/other/checkout`). Such a remote's tracking refs are only as fresh as the last
fetch, and they go stale the moment the other checkout moves — producing a permanent,
meaningless `ahead N`. When a copy's dev/production pairing is configured this way, check
`git remote -v` before believing any ahead/behind count, and prefer a URL that names the
real server for the copy that is supposed to consume it.

### Retiring the old commits locally — a reset is not enough

After `git reset --hard` onto the rewritten line, the pre-rewrite commits are still
reachable through the reflog and `git cat-file -e <old-sha>` still succeeds: reset moves
refs, it does not expire history. Anyone holding the checkout can recover the purged
content until you do:

```bash
git reflog expire --expire=now --expire-unreachable=now --all
git gc --prune=now --quiet
git cat-file -e <old-sha> || echo 'old line unreachable'   # the probe must FAIL
```

Probe both an old commit and the old branch tip — purge one and the other can still be
reachable. Also re-point or delete any local-only backup branch (`backup/pre-*`) left on the
old line: it keeps the entire pre-rewrite graph alive and visible in `git log --all` even
after the reflog is expired.

### Force-push from the checkout whose remote auth already works

A scratch mirror clone made for the rewrite frequently cannot push — it has no working
credential context for the forge, and a non-interactive push dies with `could not read
Username for '<url>'`. Do not re-enter credentials into a throwaway clone; move the objects
to the checkout that already pushes fine and publish from there:

```bash
# in the working repo whose remote is known-good
git remote add rewritten /path/to/rewritten-clone
git fetch --force rewritten '+refs/heads/*:refs/remotes/rewritten/*' '+refs/tags/*:refs/tags/*'
git push --force origin refs/remotes/rewritten/<branch>:refs/heads/<branch>   # explicit refspec
git remote remove rewritten
```

Push by explicit refspec rather than `--all`: a fetch into `refs/remotes/rewritten/*` must
not be able to publish anything you did not name. Then reset the local branches onto the
rewritten tips and finish with the reflog/gc step above.

## 2. Sweep the WHOLE fleet for the leak class, not just the rewritten repo

Scanning only the repo you rewrote is the most likely way to leave a leak in place. A leak
class — internal IPs, machine names, forge FQDNs — is a convention the whole fleet shares,
so a token scrubbed from the rewritten repo is very likely still sitting in a sibling repo,
often one that is ALSO public, and often because a skill that holds operational commands
quotes the real value.

Run the same token set across every repo in scope before declaring the job done:

```bash
git grep -n -E "<internal-token-alternation>" HEAD    # per repo, not just the rewritten one
```

Then decide each hit by WHERE IT ACTUALLY REACHES, not by how it looks locally:

| Where the token lands | Verdict |
|:--|:--|
| An operational command / config line the skill exists to teach | Rewrite to neutral placeholders ONLY if the artefact is projected to a public end. A skill whose commands are useless without the real host is better kept PRIVATE than sanitised into nonsense. |
| A machine name used in prose ("on machines with the <host>-style setup") | Unambiguous leak — redact. The sentence teaches the same thing with a generic noun. |
| A directory excluded from the public projection | Not public — no rewrite needed. Say so explicitly rather than leaving it unmentioned. |
| A value visible on the PUBLIC end after checking the public raw URL | Needs a rewrite of that repo's history — the same cost as the one just completed. Surface it and let the user decide the scope; do not silently start a second rewrite. |

Verify reachability directly rather than inferring it — fetch the public raw URL for the
file and grep it. A hit that only exists on the private end is a different decision from one
already published.

### An allowlist entry is a permission, never proof of compliance

A repo's public `AGENTS.md` may carry a path-pattern allowlist ("these paths may name
instance facts") — the platform skills, the versioning notes, the README's own-instance
section. That list answers *may this path carry the value*, not *does this value reach the
target remote*. Those are different sets, and a single repo routinely has both at once: one
allowlisted directory dropped entirely from the public line, another allowlisted directory
carried across in full.

So do not resolve a hit by looking it up in the allowlist. Resolve it by measuring
projection membership — fetch the target's own URL for that exact file and grep it:

```bash
curl -s -o /dev/null -w '%{http_code}\n' "<public-url>/tree/<branch>/<allowlisted-dir>"   # 404 = excluded
curl -s "<public-raw-url-for-the-file>" | grep -c '<token>'                              # 1 = published
```

A token inside an allowlisted-but-excluded directory is compliant and needs no work; the
same token inside an allowlisted-and-published directory is a live leak the allowlist never
covered. Both readings are defensible from the allowlist text alone, which is why the
distinction must be measured per file rather than read off the policy. Report the excluded
case explicitly as "allowed by policy, not projected, no action" — silence about it is
indistinguishable from having missed it.

Corollary for the rewrite decision: an allowlisted directory that the projection excludes
needs no history rewrite *for the public end*, even when its content is thoroughly
instance-bound. Only the file that is actually served has to be clean.

"The rewrite is clean" and "the fleet is clean" are different claims. Only the second is
worth saying without qualification.
