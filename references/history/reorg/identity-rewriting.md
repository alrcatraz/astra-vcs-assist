# Rewriting author identity and verifying the result

Rewriting author identity and verifying the result.

## Identity rewriting in an existing history (git filter-repo --mailmap)

Author/committer identity is part of a commit OBJECT, so a wrong identity cannot be
corrected by editing files or adding a commit — every commit carrying it must be
rewritten. Use the mailmap operation, which is the one filter-repo mode that changes
identity and nothing else.

```bash
printf 'Real Name <real@addr> <wrong@addr>\n' > mailmap.txt
git filter-repo --mailmap mailmap.txt --force
```

Mailmap lines key on the FULL identity pair as stored: a name that was rewritten by an
earlier email-only pass needs its own line keyed on the SURVIVING combo (e.g.
`Angelia (Hermes Agent) <correct@addr>`), not the original wrong pair — after a partial
fix, enumerate `%an <%ae>` again and build the map from what is actually in the objects.
Committer fields ride along automatically. When several distinct human-looking names should
all normalise to one canonical identity (legal name vs forge handle vs hostname local
part), ask once which wins, then emit one line per distinct stored pair — do not adjudicate
each commit separately.

Verify, all three, before pushing:

```bash
# 1. no branch carries the rejected identity any more
for B in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  printf '%-24s %s\n' "$B" "$(git log --format='%ae|%ce' "$B" | grep -c wrong@addr)"
done
# 2. TREES byte-identical (proves the rewrite touched no content)
git rev-parse <pristine>/<branch>^{tree} <branch>^{tree}
# 3. commit count, merge count and every commit subject unchanged
git rev-list --count <branch>; git rev-list --min-parents=2 --count <branch>
git log --format=%s <pristine>/<branch> | md5sum; git log --format=%s <branch> | md5sum
```

- **`--mailmap` is the tool to trust; the path and content modes around it are not.**
  It is identity-scoped, so it cannot leak into unrelated blobs. The three failures this
  repo has hit — a `--blob-callback` substring test clobbering 35 files, `--invert-paths`
  deleting the target file, `--path` collapsing 246 commits into 1 and dropping four
  branches — all came from scoping a rewrite by *content* or *path*. See
  `references/filter-repo-scoping-traps.md` before choosing any other mode.
- **Verify identity rewrites against BOTH name and email fields, and against the commit
  count.** A rewrite that reports success can still leave the rejected identity in place:
  `--email-callback` fixes only `%ae`, so a display name like `Angelia (Hermes Agent)`
  survives while every email looks clean, and a run whose worktree was dirty silently drops
  uncommitted commits (85 → 57 with exit 0). The check is therefore
  `git log --format='%an <%ae>' | sort -u` (not `%ae` alone) **plus** a pre/post
  `git rev-list --count HEAD` comparison against the ledger taken before the rewrite.
- **A wrong identity usually comes from inherited config, not a deliberate choice.** Check
  what `git config user.email` resolves to globally and per-clone before treating authorship
  as a decision: an agent-branded global value silently signs every commit in every clone
  lacking a repo-local override, so dozens accumulate with nothing looking broken. Fix the
  global value AND each clone's local value, then confirm the bad address is gone from
  `~/.gitconfig`.
- **Decide identity BEFORE the first public push, and treat the audit as part of it.**
  A clone inherits whatever `user.email` resolves to, so a wrong identity accumulates
  across many commits with nothing looking broken. Audit authorship across the whole
  branch (`git log --format='%ae' <branch> | sort -u`) before publishing — and fix the
  global config too, not just the repo, since a global value silently re-poisons any
  clone without a repo-local override.
- **Never author commits under an agent-internal address** unless the user explicitly
  authorizes it for that repo. Internal agent/lab addresses are infrastructure, not
  authorship; putting one in git metadata publishes it on every commit and every remote.

### Unblocking a PROTECTED branch for the post-rewrite force-push (API, no manual UI step)

Both hosts block the force-push itself, and each needs a different API move. Do this
BEFORE presenting the push plan, so the rewrite does not land nowhere:

**Gitea** — `PATCH /api/v1/repos/{owner}/{repo}/branch_protections/{branch}` (NOT `PUT`;
`PUT` returns 405, as does `POST .../branch_protections/{branch}` — only the collection
endpoint and PATCH work):

```python
call('PATCH', f'/repos/{owner}/{repo}/branch_protections/main',
     {'enable_push': True, 'enable_force_push': True})
```

- **`enable_push: true` is mandatory alongside `enable_force_push`.** Gitea models force
  push as an *extension* of push access: with `CanPush=false` the pre-receive hook rejects
  with `Not allowed to force-push to protected branch <b>` no matter what
  `enable_force_push` says. This is undocumented and cost several attempts (the stored
  field reads back as `true` while the hook still denies).
- **Recreating the rule via `POST` silently drops `enable_force_push`** — the create
  endpoint stores `false` even when the body says `true`. Set it afterwards with PATCH.
- `bypass_allowlist` grants do not substitute; the push/login identity is the plain user.

**GitHub** — `DELETE /repos/{o}/{r}/branches/{b}/protection`, push, then restore:

```bash
gh api repos/{o}/{r}/branches/main/protection > protection.json     # snapshot FIRST
gh api -X DELETE repos/{o}/{r}/branches/main/protection
# ... force-push ...
gh api -X PUT repos/{o}/{r}/branches/main/protection \
  -H 'Accept: application/vnd.github+json' --input restore.json
```

- **Restore with `--input <file>`, never `-F key=value`.** `-F` sends the value as a
  string, so nested objects (`required_status_checks`, `restrictions`) fail schema
  validation with `No subschema in "anyOf" matched` / `is not an object`. The PUT shape is
  `{"required_status_checks":null,"enforce_admins":false,
  "required_pull_request_reviews":null,"restrictions":null, ...}`.
- End state that proves it: `allow_force_pushes.enabled == false`,
  `enforce_admins.enabled == false`, `required_pull_request_reviews == null`.

Both hosts allow disabling protection with an admin-scoped token, so **a "you must click
this checkbox in the web UI" conclusion deserves the same scepticism as any other
permission claim** — re-probe the API shape (method + companion fields) before asking the
user for manual steps.

### A plain `git push --tags` re-publishes fetched remote-tracking tags

Fetching a remote's tags into a namespaced ref pattern (`git fetch <url>
'+refs/tags/*:refs/tags/<x>-*'` for a read-only comparison) leaves ordinary local tags that
a later `git push --tags` ships right back — including onto the OTHER remote. Symptom:
`git push origin --tags` reports `* [new tag] origin-v1.3.0` for every comparison tag.
Fix: delete them both sides (`git push <remote> :refs/tags/<t>` + `git tag -d <t>`) and
re-verify with `git ls-remote --tags <remote>`. Prefer comparing via SHA lookups
(`git rev-parse <sha>^{tree}`) or a separate clone over importing refs into the repo you are
about to push.

### Retiring a redundant parallel lineage (duplicate history from an old merge)

A merge-era fork leaves two lineages with the same subjects and different SHAs. When the
user says "merge them", the honest answer is usually RETIRE, not `git merge` — merging two
histories that already carry the same content keeps both ancestors and makes the
duplication visible forever.

Prove it is safe, in this order:

```bash
# 1. same-subject check: every "unique" commit has a twin on the survivor line
for h in $(git log --format=%h <lost> ^<our>); do
  s=$(git log -1 --format=%s $h); git log <our> --format='%h %s' | grep -F "$s"
done
# 2. patch-id check (unequal ids usually mean rebase-rewritten twins, not unique content):
#    unequal ids usually mean rebase-rewritten twins, not unique content
# 3. for anything still unmatched, DIFF THE FILES:
#    git diff <lost-branch> <our-branch> -- <path>   # empty = content already present
```

Then pin before deleting: `git update-ref refs/tags/archive/<name> <sha>` — **not
`git tag -m`**, which invokes `$EDITOR` and dies with `cannot run nvim` on a box where
`EDITOR=nvim` is exported but nvim is not installed. Verify each archive tag resolves
(`git log -1 --format='%h %s' archive/<name>`) before `git branch -D`.

- **Stale side-branches from the same era carry the same bad authors and should be retired in
  the same pass — audit them for genuinely unique content first
  (`git log --format="%H %s" <ref> ^main` + patch-id), then delete both locally and on
  every remote.
- **NEVER inherit a "content already merged" verdict from a sibling analysis — re-run
  it per branch.** Hit for real: one branch was deleted because a *different* branch
  had been proven redundant, and the assumed-symmetric file turned out NOT to be in
  main (`git diff main <ref> -- <file>` = 7 insertions / 22 deletions, i.e. unique
  work). The branch ref itself survived as a loose object, which is the only reason it
  was recoverable. The check is one command and it is per-branch, always:
  ```bash
  git diff main <ref> --name-only        # empty ⇒ genuinely merged; anything ⇒ unique
  ```
  Deleting a branch whose content never landed is the ONE history-rewrite cleanup
  mistake that destroys work rather than reorganising it. If the diff is non-empty
  AFTER deletion, recover the ref first (`git update-ref refs/heads/<name> <sha>` —
  the commit object outlives the ref) and then cherry-pick onto current main instead
  of rebasing the old line.

### Cheap path for a contiguous run of bad-author commits: rebase --exec, not filter-repo

When every wrong-author commit sits in one unbroken range (nothing to delete, no content
to rewrite), `git rebase <base> --exec` with a guarded amend is far lighter than a
filter-repo pass — same identity-only guarantee, no mirror clone, no remote stripping:

```bash
export GIT_EDITOR=: GIT_SEQUENCE_EDITOR=:
FILTER='test "$(git log -1 --format=%ae)" = "<wrong-email>" \
  && git commit --amend --reset-author --no-edit || true'
git rebase <remote>/main --exec "$FILTER"
```

- **The `|| true` is mandatory.** A bare `test ... && ...` exec exits 1 on every
  *non*-matching commit and halts the rebase half-applied, leaving an interactive-rebase
  state to clean up (`--continue` / `--abort`). The guard's job is to choose which commit
  to fix, never to signal failure.
- **Neutralise both editors** (`GIT_EDITOR=` + `GIT_SEQUENCE_EDITOR=:`) or the sequence
  blocks on `$EDITOR`/a missing editor (`error: cannot run nvim`) mid-rewrite.
- **Stash the dirty worktree first** (`git stash push -m ...`, pop after): uncommitted
  changes make cherry-pick/rebase report conflicts unrelated to the rewrite, and a
  mistaken `cherry-pick` onto a mis-chosen base produces the same fake conflict.
- Verify with the three checks above (identity set, tree diff vs original tip empty,
  count unchanged). For commits already published on shared branches, the force-push
  safety nets in `rewrite-workflow.md` apply unchanged.
- **A stated intent is not a force-push approval.** "History should only contain human
  commits" authorises rewriting; it does NOT authorise `push --force` on a shared branch.
  Run that audit (which remotes hold each bad commit, which merge/PR records orphan,
  which clones break), present it as a table, and get explicit per-remote go-ahead —
  then rewrite locally, verify, and push one remote at a time.
- **The rewrite target is the identity pair, not just the email.** A user ruling of
  "history must contain only human identities" covers `%an` AND `%ae`: an agent-branded
  display name (`Angelia (Hermes Agent)`) surviving an email-only rewrite is still a
  violation, and machine-addressed commits (`user@hostname.lan`) leak infrastructure into
  every clone. Enumerate both fields across all branches before choosing the mode.
- **Enumerate BOTH fields on EVERY ref before sizing the job — and ask about ambiguous
  human identities instead of guessing.** The bad-author set is larger than the visible
  one: commits reachable only from a tag (no branch contains them) hide from branch scans,
  and parallel duplicate lineages (a merge-era copy vs the rewritten main: same subjects,
  different SHAs) multiply the count. Audit with `git log --all --format='%an|%ae' |
  sort -u` plus per-branch/per-tag containment, then classify each identity: agent-brand →
  rewrite to the human value; hostname-local-part email → fix the email; a REAL personal
  name variant (e.g. legal English name vs forge handle) → surface it and let the user
  rule whether it normalises or stays. Mailmap lines key on the wrong identity and map to
  the chosen canonical pair, one line per distinct bad identity.
- **Bad authors usually arrive in batches with tell-tale SHAs/mtime.** A cluster of
  same-second mtimes or sequential UUIDs across unrelated entries means one bulk import
  wrote them; classify the batch once, don't adjudicate each commit as an independent
  human edit.

## Post-rewrite verification: trees, not log shape

Prove the rewrite preserved CONTENT before pushing:

```bash
git diff <backup-branch> HEAD --stat   # 0 lines = content identical
```

A trailing-newline addition shows here as a 1-line diff — decide whether that is
intentional and state it, rather than reading a non-empty diff as either "rewrite broken"
or as noise to ignore.

**The four-check battery for an identity rewrite (run all, report all):**

```bash
# 1. identity set across EVERY ref, both fields — expect exactly one line
git log --all --format='%an <%ae>' | sort | uniq -c | sort -rn
# 2. topology frozen: commit + merge counts per branch vs pre-rewrite ledger
for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  printf '%s commits=%s merges=%s\n' "$b" \
    "$(git rev-list --count $b)" "$(git rev-list --min-parents=2 --count $b)"
done
# 3. tree byte-identical against the authoritative baseline held OUTSIDE the repo
git rev-parse main^{tree}   # == git -C <bundle-clone> rev-parse main^{tree}
# 4. subjects untouched in order
git log --format=%s main | md5sum   # == baseline clone's same value
```

Tree equality vs an external bundle clone replaces the in-repo pristine-diff comparison
(which filter-repo aliases away — see references/filter-repo-scoping-traps.md).

**Verify what the SERVER serves after every push leg — remote refs are part of the
rewrite scope.** `ls-remote` tips + tag derefs (`refs/tags/X^{}`) per remote, plus
identity over the fetched remote ref (`git fetch <remote> main && git log --format='%an <%ae>'
<remote>/main | sort -u`). Two silent failure shapes: (1) filter-repo strips remotes, so a
later "I pushed to origin" may have run against a nonexistent remote — re-check
`git remote -v` before claiming any leg done; (2) `git push --tags` pushes EVERY local
tag, including `origin-*` style collision-avoidance tags created by a scoped fetch — name
the tag refs explicitly (`git push <remote> refs/tags/vX refs/tags/archive/...`) instead of
using `--tags` on a polluted tag namespace.
