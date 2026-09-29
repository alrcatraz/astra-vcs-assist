# Collapsing a two-repo fork into the public repo while an upstream PR is open

The end-state of `astra-flclash`-style drift: one PUBLIC repository carrying the tower
model, the private repo retired as read-only archive. The hard constraint throughout is
that **an open upstream PR is bound to a branch on the public fork by SHA** — GitHub
closes it unrecoverably if that branch or repo disappears. Everything else is negotiable;
the PR-carrier branch is not.

## Order of operations

1. **Prove nothing is lost before deleting any remote branch.** A diverged remote branch
   (e.g. an old `dev` with no role in the model) must be shown redundant, not assumed so:
   ```bash
   git rev-list --count <remote-br> ^main          # commits unique to the doomed branch
   # for EACH such commit, compare patch-id against main's whole lineage:
   git show <sha> | git patch-id --stable         # match against main's set → all matched?
   ```
   All-matched ⇒ duplicate lineage (a rebase left different SHAs on identical diffs), safe
   to retire. Any unmatched commit ⇒ real unique work; stop and reconcile first. "Ours is
   newer" is NOT sufficient evidence when ahead/behind counts are both large.
   - **A tree-level file diff can mislead in BOTH directions.** Two files present on the
     doomed branch but absent from ours looked like lost content; they were actually stale
     assets that an UPSTREAM commit had already replaced with newer files we carry. Read
     the commit that touched them (`git log --diff-filter=D -- <path>` and the adding
     commit's stat) before concluding either "we lost something" or "nothing differs".
2. **Tag the doomed branch tip on the remote BEFORE force-pushing over it**, so the rewrite
   is auditable and reversible:
   `git push <remote> <old-sha>:refs/tags/archive/pre-convergence-<br>`
3. **Force-push the branches that change** (`main`, `development`, non-PR `feat/*`). Use
   plain `--force` only after step 1 proved equivalence and step 2 tagged; prefer
   `--force-with-lease` where the lease can be bound to the recorded remote SHA.
4. **Never touch the PR-head branch.** Leave `feat/<pr-branch>` exactly at its remote SHA.
   Re-check the PR after every push: `gh pr view <n> --repo <upstream> --json
   state,mergeable,headRefOid` — expect OPEN / MERGEABLE / unchanged head OID.
   - **The red line applies to LOCAL commits too, not just pushes.** A scratch clone left
     checked out on the PR branch will absorb any commit you make without switching first,
     and an `&&` chain does NOT stop when `git checkout main` fails (a dirty worktree makes
     checkout print "Aborting" while the chained `git commit` still runs on the old branch).
     Assert location immediately before every state-changing git command:
     `git branch --show-current`. Recovery of a mis-placed unpushed commit: `git reset
     --hard <correct-sha>` on the wrong branch, redo the commit on the right one, then prove
     the wrong branch equals its remote (`git rev-parse` both sides). An unpushed mis-place
     is cheap; the same commit reaching the PR head changes what upstream reviews.
5. **Delete the role-less branch** last, once its tag exists: `git push <remote>
   --delete refs/heads/dev`.
6. **Create the upstream mirror namespace** on the public repo: fetch upstream shallow,
   push its tip to `refs/heads/up/main`. This is what makes `git log main..up/main`
   meaningful and replaces the overloaded-old meaning of `main`.

## Retiring the private repo (archive, never delete)

```bash
# audit tags FIRST, while the repo is still writable — see ordering trap below
git push <priv> <pre-rewrite-sha>:refs/tags/archive/pre-desensitise --no-sign
# align private branches to the corrected lineage, retire dev
git push --force <priv> main development feat/... --no-sign
git push <priv> --delete refs/heads/dev
# flip default branch (gh repo set-default takes positional args and errors oddly;
# the reliable form is the API PATCH):
gh api -X PATCH repos/<owner>/<priv> -f default_branch=main
git push <priv> main:refs/heads/main      # ARCHIVED.md pointer commit lands on main
github gh repo archive <owner>/<priv> --yes
```

Pitfalls specific to this sequence:

- **Archiving makes the repo read-only (403 on every push).** So audit tags and the
  default-branch flip MUST happen before `gh repo archive`. If you force-push branches off
  the pre-rewrite SHAs first, those commits become unreachable and a later attempt to tag
  them fails with "remote end hung up" — GitHub has no object to point the ref at. Push the
  tag ref itself (which uploads the object if absent) while still writable, or keep the
  pre-rewrite commit reachable until tagged.
- **Recovery from a premature archive**: `gh repo unarchive <owner>/<repo> --yes` — the
  `--yes` is mandatory; without it the command prints usage and exits WITHOUT error in a
  non-TTY session, leaving the repo archived while you believe the unarchive ran. Same
  class of silent no-op as `gh repo archive` needing `--yes`. Always re-read
  `gh repo view ... --json isArchived` after toggling; do not trust the exit code.
- **`gh repo set-default <owner>/<repo> <branch>` rejects extra args** in some CLI versions
  and the chained script keeps running. Use `gh api -X PATCH ... -f default_branch=<br>`
  and verify via `gh repo view ... --json defaultBranchRef`.

## Rewriting identity/text across history: which filter-repo mode

See `git-history-reorg`'s `references/filter-repo-scoping-traps.md` — that is the
authoritative mode table. The short version for a fork collapse: `--mailmap` for identity
(proven trees-byte-identical), `--replace-text` for literal token purge (verify each rule
actually matches the file's real text, extract patterns with `grep -nE` not memory), and
NEVER `--blob-callback`/`--path`/`--invert-paths` for scoping a single-file content rewrite
(each silently destroys something). Do identity + text in ONE combined invocation.

## Post-collapse doc truth

The AGENTS files record only what exists: the four branch roles, why the
PR-head branch deliberately does not flow back into `development`, the real
flake selector (`nix develop .#<attr>`, not bare `nix develop`), and the
host-specific env vars the shell reads. Verify each claim against the tree
before publishing it (`git cat-file -e main:<claimed-file>`); a doc that
describes an absent workflow is a fresh kind of leak. Split by sensitivity:
project-general facts go in `AGENTS.md`, private topology (user paths, machine
names, ports, internal domains) goes in `AGENTS.local.md` — scan whatever lands
in the public file before the push, same red line as the rest of the tree.
