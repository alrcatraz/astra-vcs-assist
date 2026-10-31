---
name: github-dependency-automation
description: "Use when enabling dependabot, auto-merge, or PR-title gates."
version: 1.0.0
author: alrcatraz
platforms: [linux]
metadata:
  hermes:
    tags: [github, dependabot, auto-merge, ci, dependency-update, declarative-build]
triggers:
  - "dependabot 配置"
  - "enable dependabot"
  - "auto-merge PR"
  - "gh pr merge --auto"
  - "dependabot PR 合并"
  - "dependency update safe with guix/nix"
---

# GitHub Dependency Automation & CI Hygiene

Class of task: set up and operate a repo's dependency-update automation
(`dependabot.yml`), an auto-merge path, and a semantic PR-title gate — and
decide, before enabling or merging anything, whether an update is safe given
the repo's declarative build layer (nix/guix) and its CI.

## Standing preferences (apply to every instance)

- **Never enable automation mechanically to "cover all repos."** Audit each
  repo first (language, lockfile, CI presence, fork/archived status) and only
  enable where it earns its keep. Forks, pure-doc repos, and repos with no
  lockfile and no CI get nothing.
- **A green dependabot PR is not a reason to merge it — the guix/nix impact
  is.** When builds standardise on Guix (Nix fallback), gate every dependency
  update on: does it touch the declarative toolchain (`.guix/manifest.scm`,
  `.guix/channels.scm`, `flake.nix`) or the pinned runtime (e.g. `Dockerfile
  ARG NODE_VERSION`)? If yes and CI cannot rebuild it autonomously, DEFER — a
  missing package there breaks the build. Updates that only touch ecosystem
  lockfiles (`package-lock.json`, `Cargo.lock`, `pubspec.lock`, `go.sum`) and
  workflow `uses:` versions are safe: they sit OUTSIDE the declarative layer.

## Procedure

### 1. Audit the repo before writing any config

```bash
# Language + automation state + archive flag
gh api repos/OWNER/REPO --jq '{lang:.language, auto:.allow_auto_merge, fork:.isFork, archived:.archived}'
# Dependency manifests / lockfiles (dotfile-safe: git tree, NOT contents API)
gh api "repos/OWNER/REPO/git/trees/HEAD?recursive=1" \
  --jq '[.tree[].path] | map(select(test("lock$|sum$|pyproject|package.json|flake.nix|go.mod|Dockerfile|workflows/"))) | .[0:40]'
# CI present? target branch protected? (auto-merge needs BOTH)
gh api repos/OWNER/REPO/contents/.github/workflows --jq '.[].name'
gh api repos/OWNER/REPO/branches/BRANCH/protection   # 404 = NOT protected
```

Decision:
- `archived: true` → read-only; a PATCH will 403. Find the live fork/mirror
  and configure THERE. Check `archived` even when `pushed_at` is recent — an
  archived repo keeps its last-push date.
- No lockfile + no CI → skip dependabot (nothing to detect / nothing validates).
- Pure-doc / mkdocs repo → skip dependabot; auto-merge has no object.

### 2. Write `.github/dependabot.yml`

One entry per ecosystem **per directory** (a monorepo needs one entry per
package dir with its own manifest). Cover the ecosystems the audit found:
`npm`, `docker`, `github-actions`, `pub`, `gomod`, `cargo` (one per Cargo
package dir), `gradle`. Weekly schedule; commit-message prefixes the PR-title
gate accepts (below).

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule: { interval: "weekly", day: "monday" }
    commit-message: { prefix: "deps" }
    open-pull-requests-limit: 10
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly" }
    commit-message: { prefix: "ci" }
```

The `contents` API returns 404 for dotfiles like `.github/dependabot.yml` —
confirm existence with the git-tree query, not the contents endpoint.

### 3. PR-title gate (if the repo uses conventional commits)

A `pull_request` workflow running `amannn/action-semantic-pull-request`,
pinned to a **full commit SHA** (mutable major tags are a supply-chain risk on
a workflow fork PRs can trigger). Its allowed `types` MUST include every
commit-message prefix dependabot emits (`deps`, `build(deps)`, `ci`, plus
`revert`) or dependabot's own PRs fail the gate.

### 4. Enable auto-merge — ONLY where branch protection exists

```bash
gh api -X PATCH repos/OWNER/REPO -f allow_auto_merge=true   # repo-level switch
gh pr merge <n> --auto --squash                             # arm a PR
```

### 5. Operating an existing setup: the target branch and the bot's red checks

- **Set `target-branch` explicitly in every ecosystem block.** Without it dependabot
  opens against the repo's DEFAULT branch. When the team integrates on a different
  branch (`development`), every PR lands where nobody builds: its checks are red for
  reasons unrelated to the diff, it drifts from the integration branch, and the pile
  grows weekly. Ordering quirk: dependabot reads its config from the default branch, so
  the change takes effect only once it reaches that branch.
- **Identical failures across all open bot PRs are a base-tree problem, not six
  separate bugs.** Before approving, merging or debugging anything, check whether the
  same job fails on every bot PR and whether it reproduces on the base commit. One
  shared red check means the bots' diffs were never exercised — approving is
  rubber-stamping and debugging them is wasted time.
- **When the bots cannot validate a bump, apply it yourself on a branch whose CI runs.**
  Close the bot PRs with a one-line explanation (and the commit that carries the same
  change) instead of merging an unverified update into the default branch. Group bumps
  that would conflict with work already on the integration branch are better left to be
  regenerated against it than resolved by hand.
- **SHA-pinned actions: resolve the tag, keep the version comment.**
  `git ls-remote https://github.com/OWNER/ACTION refs/tags/vX.Y.Z` gives the commit to
  pin; replace the SHA and keep `# vX.Y.Z` so the line stays readable. Bump EVERY
  occurrence — including the `/save` and `/restore` sub-actions of a cache action, and
  any job that already carries the new major. A half-migrated matrix keeps the old
  runtime deprecation warnings and makes the bump look ineffective.

## Pitfalls

1. **`gh pr merge --auto` needs an explicit method AND branch protection.**
   Non-interactively it errors `--merge/--rebase/--squash required`; supply
   one. It can then still fail `Protected branch rules not configured for
   this branch (enablePullRequestAutoMerge)` — auto-merge means "merge when
   the branch's REQUIRED checks pass," which only exists under a protection
   rule. The repo-level `allow_auto_merge` switch alone is NOT enough: without
   protection arming fails (and with `UNSTABLE`/`CLEAN` state GitHub refuses
   the mutation). When NO protection rule exists, do NOT defer the merge as a
   blocker — fall back to a DIRECT merge (`gh pr merge <n> --squash`), which
   needs no protection. Verify with a read-back (`--json
   autoMergeRequest,mergeStateStatus`), because a failed arm is
   indistinguishable from success in the command's stdout.

2. **An advisory (`continue-on-error`) check marked FAILURE neither blocks a
   merge nor means the PR is broken.** `gh pr ... --json statusCheckRollup`
   lists EVERY check with `conclusion: FAILURE`, including advisory/security
   scans (DAST, scorecard, semgrep). Judge mergeability by `mergeable` +
   `mergeStateStatus` (`CLEAN`/`UNSTABLE` = mergeable; `DIRTY` = conflict),
   not by counting FAILUREs. `UNSTABLE` = only advisory checks red; with no
   required checks it still merges.

3. **`merged_by: <your login>, type: User` is indistinguishable from your own
   manual UI merge via the API — do not infer "an automation process merged
   it."** Confirm WHO acted by checking for a matching dependabot/auto-merge
   workflow and its config before building a story on "the bot did it."

4. **`git fetch remote1 remote2` parses as `fetch remote1 ref remote2`, not
   two remotes.** It fails `couldn't find remote ref` and — critically —
   short-circuits the whole `&&` chain, so pushes queued after it never run.
   Fetch each remote in its own command (`git fetch r1; git fetch r2`).

5. **Layer discipline decides whether an update is safe (the guix gate
   above).** Classify what a dependency PR touches: ecosystem lockfile /
   `uses:` version → safe (outside the declarative build); `manifest.scm` /
   `channels.scm` / `flake.nix` / pinned runtime ARG → run the guix/nix
   impact check, defer if CI can't rebuild it autonomously.

6. **A batch of comment+close calls partially fails behind a flaky link, and the
   loop will not tell you.** Iterating `POST /issues/N/comments` then
   `PATCH /pulls/N` with `curl -w '%{http_code}'` prints `000` on a TLS reset while
   the shell keeps going, so some PRs end up closed-without-a-reason and others
   commented-but-still-open. Always finish by re-listing
   `pulls?state=open` and diffing it against the list you meant to close; re-issue
   only the gaps (a second `PATCH {state: closed}` on a closed PR is harmless, and a
   missing comment can be posted after the fact). Do not report "closed N PRs" from
   the loop's own output.
