# Proving the rewrite or the release actually holds


## Release-loop closure — a version bump is NOT a release

Four faces must each hold before a version counts as released; they fail
INDEPENDENTLY and silently. A real incident (a release-to-release upgrade) found
`main` three versions behind `development`, tags sitting on development (never
merged to main), and releases missing on the private mirror entirely — only the
version-bump commit had been made. The GitHub `Latest` badge / last release does
NOT prove the loop closed. Verify each face:

```bash
# 1. main merged? (release commit on main)
git merge-base --is-ancestor <release-commit> main
git rev-list --count main..development     # 0 = dev fully merged
git rev-list --count development..main     # 0 = main has nothing unique (clean FF)

# 2. tag on the RIGHT commit, on ALL remotes?
git log -1 --oneline vX.Y.Z                # release commit, NOT a feature/merge node
git ls-remote github 'refs/tags/vX.Y.Z'
git -c http.version=HTTP/1.1 ls-remote gitea 'refs/tags/vX.Y.Z'

# 3. release created on BOTH remotes?
gh release list --repo <owner>/<repo> | grep vX.Y.Z
curl -s -u "user:$PASS" "$GITEA/api/v1/repos/<owner>/<repo>/releases?limit=50" \
  | python3 -c 'import sys,json;print([r["tag_name"] for r in json.load(sys.stdin)])'
```

Recurring failure modes: **main stranded** (missed merge strands every later
version — the classic multi-version gap); **tag on development-only** (main never
advances); **release missing on the mirror** (GitHub fine, Gitea only ever got the
first version). Verify with `git show <public-remote>/<branch>:<internal-file>`
fails for any internal doc/PLAN the public end must not leak (esp. a private
Gitea remote identity — replace `gitea`/private-host words in AGENTS/CHANGELOG
with neutral `private mirror` before public push).

**Sync release bodies GitHub→Gitea**: `gh release view <tag> --json body -q
.body`, then `POST .../releases` (create) or `PATCH .../releases/<id>` (get the id
via `GET .../releases/tags/<tag>` first) with `tag_name`/`name`/`body` JSON, Basic
auth (line 1 of the pass entry = password). Do NOT `curl | python3` on one line
(scanner flags pipe-to-interpreter).

**Non-destructive repair (no history rewrite)**: fast-forward `main`→`development`
(only if `development..main` is empty); if a mirror's main diverged via an old
merge node, `git merge --no-edit <mirror>/main` creates a structural merge so the
push is normal (not `--force`) yet history stays connected; re-tag the correct
commit GPG-signed, push tags to all remotes, re-sync releases, re-run the checks.

### The AGENTS pair across a history reorg

Project instruction files follow the two-file model (see astra-vcs-assist
`git-init`): **`AGENTS.md`** is committed and behaves like code in a
reorg — its CONTENT must obey the public-repo red line at every ≥ L2 remote
(no secrets, no private remote identity, no internal hostnames/IPs; sanitise
to neutral terms like `private mirror`). **`AGENTS.local.md`** is the private
layer (remotes, topology, credentials) and is disclosed only to ≤ L1 remotes
(tower-model) — a reorg that rewrites history must keep it out of every
≥ L2 tree, and where no ≤ L1 remote exists it belongs in `.gitignore`
(proof: `git show <public-remote>/<branch>:AGENTS.local.md` must fail).

A reorg never records *what leaked in the past* in either file — both stay
present-tense usage documents describing the clean current state; history
(including any sanitisation) belongs in the commit log, not the files.

## Shared-tree commits: stage by path, never by tree (verification pass)

**Load this section whenever the repo has OTHER uncommitted work in it** — several agent
sessions, worktrees, or a sibling copy touching the same work tree. This is the normal
state of the shared skills library and the infra repos, not an edge case.

`git add -A`, `git add .`, and `git commit -a` are forbidden here. They stage the whole
tree, so a sibling session's backlog rides into your commit, and a reviewer then has to
pick unrelated edits out of your change to review it. Stage and commit by PATH, twice:

```bash
git add <path> [<path>...]                          # stage only your paths
git commit -m "<type>(<scope>): <desc>" -- <path> [<path>...]   # commit only your paths
```

Audit the landing set before and after, and stop on any line you cannot account for:

```bash
git status --short          # files you never touched = someone else's backlog
git diff --cached --stat    # what will actually land
git show --stat HEAD        # the same check after the fact
```

- **Per-file paths are not the same as a narrow commit.** If a file you name also carries
  another author's hunks, `git add <path>` takes the WHOLE file. Split with `git add -p`,
  or say so in the commit body. The test is whether any diff hunk in your commit is one you
  cannot explain.
- **Already swept stray changes in?** Unwind and redo rather than explaining it away:
  `git reset --soft HEAD~1`, re-commit by path, then `git reset` to return the rest to the
  worktree unstaged.
- **A `??` directory you created for verification** (a scratch clone, a rendered output)
  is exactly what a later `git add -A` sweeps in; delete or ignore it in the same pass.

## Verifying authorship of a change — read the log, do not recall it

Before writing "this hunk is mine" / "this is another session's" into a report or a commit
body, spend one command on it. Long sessions drift, and a parallel session may be actively
rewriting the same work tree you are looking at.

```bash
git log -S'<a distinctive string from the hunk>' -- <path>   # which commit introduced it
git show <older-commit>:<path> | grep -c '<string>'          # 0 = it did not exist then
```

Getting this backwards sends a fix to the wrong repo, or leaves your own work uncommitted
while you attribute it to someone else. `git log -S` is the authority; recollection is not.

## Two clones of the same repo may be DIVERGED lineages

A repo kept as a dev copy (`~/Projects/<org>/<repo>`) plus a private copy
(`~/.astra/repos/<repo>`) can drift into two independent lineages — each ahead of the other,
so neither is a fast-forward of the other:

```bash
git fetch <other-copy> main:refs/remotes/other/main
git rev-list --left-right --count other/main...main    # e.g. `44  40` = both sides unique
```

In that state, landing a change is an ARCHITECTURE decision, not a sync step. Commit on the
lineage you are responsible for, keep the change scoped to its own files, report the
divergence with counts, and let the user rule on which line wins — never `merge` or force
one copy over the other on your own initiative. The same divergence explains other oddities
in such repos: the same file can hold different content on each side, so a tool showing
"missing" content elsewhere may just be reading the other lineage.
