---
name: git-history-reorg
description: "Git history & workspace reorganisation — flatten an entire phase (committed work + workspace changes) and re-commit as clean conventional-commit themes, OR classify uncommitted files into themed commits; net-effect grouping, reset-soft recipe, amend-trap recovery, force-push prep, untracking work dirs for public repos."
version: 0.1.0
author: alrcatraz
platforms: [linux]
metadata:
  hermes:
    tags: [git, rebase, history-rewrite, force-push, commit-cleanup]
related_skills:
  - astra-vcs-assist-git-release
  - astra-vcs-assist-git-dev
  - astra-vcs-assist-git-sync
tools:
  - git
triggers:
  - reorganise all commits
  - full history rewrite
  - 全部改动重新整理
  - 整个phase的commit规划
  - re-group commits by theme
  - net-effect commit grouping
  - force push cleaned history
  - untrack work directories
  - staging: references/staging-hygiene.md
  - classify uncommitted changes into commits
  - phase commit execution
  - group working tree by plan sub-item
---

# git-history-reorg — Full-History Commit Reorganisation

Load when the user asks to reorganise ALL commits so far (entire phase: already-committed
history + workspace changes) into a clean conventional-commit structure before a force-push.
The user's rule: **re-group everything by net effect — do NOT "keep existing + append new"**
("全部改动重新整理", 勿保留既有+追加).

### Which section you want

- **Choosing a `git filter-repo` mode** (identity vs delete vs text vs file-content, and
the verification that proves it worked) → `references/filter-repo-scoping-traps.md`.
  Read this BEFORE any history rewrite: the modes look interchangeable and are not, and
  three wrong choices in this repo each produced a silent, plausible-looking bad result.
  The same file also carries **how to prove a force-push or branch deletion loses nothing**
  (patch-id comparison across diverged histories) — do it before retiring any remote branch.
- **Secret/identity purge from already-pushed history** → `secret-purge.md` and
  `identity-rewriting.md`.
- **Rewriting the PUBLIC end of a repo (force-push to a remote others clone)** → `rewrite-workflow.md`
  (five safety nets before a PUBLIC history rewrite: bundle + SHA ledger, fork/collab check,
  isolated copy, classify-then-shape, second-stage tag/tracking-ref cleanup + fresh-clone
  verify — with the approval gate BEFORE the rewrite, and the filter-repo-vs-orphan
  escalation rule for when the rules file starts sprawling.

### Trigger: ANY commit-organisation / release-prep request on a repo with unpushed commits

The flatten rule fires not only on an explicit "reorganise ALL commits" request, but on
ANY 「整理 commits / 准备发布 X.Y.Z」 phrasing — even when the existing unpushed commits
were made by the agent itself during the iteration phase. Default to flatten; do not ask
"do you really mean flatten?".

### Field-Verified Correction (astra-agent-constellation 0.1.0 prep, 2026-08-04)

User rejected a 15-commit result: "0.1.0确认需要15个commit吗？我和你说过把所有改动放在一起
重新整理，要基于改动过贡献，而不是基于我们实际开发的先后顺序和phase规划".

Two mistakes made (both are exactly what NOT to do):
1. **Kept the 7 existing dev-iteration commits and APPENDED 8 new ones** — the "keep
   existing + append new" pattern the rule forbids. Existing unpushed commits are NOT
   sacred; they join the flatten. (In the end a fresh `git checkout --orphan` rebuild
   was the clean path for a small 30-file repo.)
2. **Grouped the new commits by the 7-item phase checklist** (task-brief, runbook,
   game-day, gate contract, audit format, language policy) — that is development
   sequence, not net effect. The user's definition of "贡献": what a READER receives.

Approved replacement grouping (net effect for a blueprint/docs repo — group by
repository section, not by what was done when):
1. `docs:` blueprint specification — all of `docs/` + `mkdocs.yml` (卷一规范)
2. `templates:` volume-2 reference implementations — all of `templates/` (卷二)
3. `scripts:` companion tooling — `scripts/`
4. `chore:` project metadata — root files (README / DESIGN / AGENTS / LICENSE / .gitignore)
- Re-tag v0.1.0 on the new HEAD, then push.
- Self-test for correct grouping: would a reader opening the repo see coherent
  deliverable sections, or a chronological diary of "what I did when"? Diary = wrong.

### Orphan-rebuild recipe (verified 2026-08-04, astra-agent-constellation 0.1.0)

Cleanest path for a SMALL repo (≤ a few dozen files) where the old root commit
has no value to preserve. `git checkout --orphan` carries the old INDEX along —
`git reset` is mandatory before the first group add, else commit 1 absorbs
everything.

```bash
git branch pre-reorg-backup            # rollback point (patch backup can't restore commits)
git checkout --orphan rebuilt
git reset                              # unstage ALL — orphan keeps old index staged
git status --short | wc -l             # expect all `??` entries, N = total files
git add docs/ mkdocs.yml && git commit -S -m "docs: ..."      # group 1
git add templates/ && git commit -S -m "templates: ..."       # group 2
git add scripts/ && git commit -S -m "scripts: ..."           # group 3
git add README.md DESIGN.md AGENTS.md LICENSE .gitignore \
  && git commit -S -m "chore: ..."                            # group 4
git branch -M rebuilt main             # replaces old main
git tag -d v0.1.0 && git tag -s v0.1.0 -m "..."   # RE-tag: old tag still points at old history
```

**When the rebuild is for a PUBLIC end, the gate runs against what the public
remote serves, and the safety nets cover refs the branch push does not touch:**

- **Verify with a fresh clone from the actual public URL**, not from the
  rebuild dir — the local repo proves the rewrite ran; only a clone proves the
  remote serves it. Scan its tracked tree for every leak class (hostnames,
  private IPs incl. `10.*`/`172.16-31.*`, machine paths, real version values).
- **Tags on the public remote do NOT follow a branch force-push.** They keep
  pointing at the abandoned history — and any object a ref reaches is
  fetchable, so old-history tags are a LIVE leak path even when every branch
  is clean. Enumerate them (`gh api repos/<o>/<r>/tags`), delete each one
  pointing at the old line, then re-tag ONLY versions that still mean
  something on the new history. Never re-create a set of historical version
  tags all pointing at the single new root — one root cannot have held N
  releases, and the mapping is a fiction.
- **Re-point every local tracking ref for that public remote after the
  rewrite** (`git fetch <remote> --prune --tags`). A stale tracking ref still
  naming an abandoned leaky tip is a live push source — the next `git push`
  of it re-publishes the very history the rewrite removed. Keep the out-of-repo
  bundle + SHA ledger as the rollback net; in-repo backup refs pin the dirty
  objects, so drop them once the bundle is confirmed.
- **Discard the pre-rebuild projection branch state** (its edits are superseded
  by the new root) and point that branch at the new root, so the local
  projection workspace and the public remote tell one story. If the rebuild was
  done in a temp worktree, `git worktree prune` first — a deleted worktree keeps
  its branch locked until pruned.
- **Pushing a tag into a clone with no push credentials**: pass the credential
  helper per-invocation
  (`GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0='!gh auth git-credential' git push origin v<X.Y.Z>`).

**Verify equivalence, not just success** (tree identity, not log shape):

```bash
diff <(git ls-tree -r --name-only pre-reorg-backup) <(git ls-tree -r --name-only main)
# empty = file tree identical; content-level: git diff pre-reorg-backup main --stat == 0
git log --show-signature --format="%h %G? %s"     # all `G`
git rev-parse v0.1.0^{}                            # annotated tag object hash ≠ commit hash;
                                                   # ^{} dereference MUST equal HEAD
git status --short | wc -l                         # 0
```

Pitfalls hit for real:
- **`git branch -d pre-reorg-backup` REFUSES** ("not fully merged") — orphan rebuild
  shares NO ancestry with the backup branch, so the merge check always fails. This is
  expected, not a sign of data loss. Either keep the branch as rollback (recommended,
  it never pushes unless explicitly named) or `git branch -D` after the user confirms.
- **GPG signing worked WITHOUT the flatpak preset dance** on this run — `git commit -S`
  and `git tag -s` succeeded with zero prep (gpg-agent cached the passphrase). Only reach
  for the preset workflow (the GPG signing note in `commit-delivery.md`) if signing actually fails; do not
  pre-emptively preset.
- **First publish of a repo with NO remote**: `git remote -v` empty is expected for a
  fresh blueprint. Flow: GCM credential fill → API check (`/api/v1/repos/<owner>/<repo>`
  → 404 = absent) → `POST /api/v1/user/repos` with `{"private":true,"auto_init":false,
  "default_branch":"main"}` → `git remote add gitea <url>` → push with `-c
  http.version=HTTP/1.1` (Gitea TLS 0A000126). Remote name is `gitea`, not `origin`.

## Where each subject lives

| Subject | File |
|:--|:--|
| Rewriting a history — traps, safety nets, shape, bootstrap | `rewrite-workflow.md` |
| Purging secrets and identities from published history | `secret-purge.md` |
| Rewriting author identity and verifying the result | `identity-rewriting.md` |
| Grouping workspace changes into themed commits | `workspace-grouping.md` |
| Delivering the grouped commits — PR, tags, branches, signing | `commit-delivery.md` |
| Proving the rewrite or the release actually holds | `verification.md` |
| Agreed grouping preferences | `grouping-conventions.md` |

`references/INDEX.md` registers the case files under `references/`;
`templates/` holds the reusable snippets.
