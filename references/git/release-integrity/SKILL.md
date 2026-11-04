---
name: astra-vcs-assist-release-integrity
description: "Use when a release claim, a tag, or a dual-remote push must be proven true."
version: 1.0.0
author: <owner>
platforms: [linux]
tags: [release, tag, lockfile, ci, verification, versioning, dual-remote]
triggers:
  - cutting a release
  - tagging a version
  - release claim
  - lockfile out of sync in ci
  - dual remote release
  - release assets
  - retroactive tag
---

# release-integrity — what makes a release claim true

Companion blocks: `references/git/release/SKILL.md` prepares the release (squash,
reword, tag, changelog); this block decides whether the resulting claim is
*true*. A signed tag whose forge flag reads Unverified is
`references/gpg/signature-provenance/SKILL.md`.

## When to Use

- Before bumping a version, creating a tag, or publishing a release
- After merging branches that both changed dependency manifests
- When a CI job fails in a way that does not reproduce locally
- Before telling the user a phase or a release is done

## 1. The next version is above the highest EXISTING tag

`package.json`'s current version is not evidence of the highest released version: a repo can carry
tags from an earlier or parallel line, and a line can be re-seeded from upstream at a lower number.

```bash
git tag --list 'v*' | sort -V | tail -5     # do this BEFORE choosing the bump
```

Pick a version strictly above the highest tag. A tag numerically below an existing release makes
"latest" ambiguous for every consumer, and a pushed tag cannot be taken back cleanly. If the line was
deliberately reset, say so in the release body and still bump above the highest tag.

## 2. Never accept git's auto-merge of a lockfile

When two branches touch dependency manifests, git merges `package-lock.json` line-wise into a file
that parses but is out of sync. The only symptom appears in CI:

```
`npm ci` can only install packages when your package.json and package-lock.json … are in sync.
Missing: <pkg>@<version> from lock file
```

Regenerate with the package-manager version the build image pins, not the workstation's:

```bash
npx -y npm@<pinned> install --package-lock-only
npx -y npm@<pinned> ci --dry-run          # must complete, not abort with EUSAGE
```

A local `npm install --package-lock-only` that reports "no change" proves nothing when the local
major differs from the pinned one.

## 3. A CI job can pass while the tool it provisions is unusable

Inside a container job the image's profile resets `PATH` when the step shell starts, so a setup
step's `PATH=…` written to `$GITHUB_ENV` never reaches `command -v`, even though the step's `env:`
block lists it first. The env block is not evidence — print `$PATH` at runtime, in the failure branch
of the assertion so passing runs stay quiet.

Writing the directory to `$GITHUB_PATH` restores visibility but not runnability: if the job then runs
under a toolchain shell that replaces `LD_LIBRARY_PATH` (e.g. `guix shell`), a binary built for the
host's ABI dies with `error while loading shared libraries` and exit 127.

Decide per image which tool the job must use, assert that choice explicitly, and after changing how a
tool reaches `PATH`, run the job that *executes* it — not only the one that *locates* it.

## 4. State the phase's exit condition before claiming it met

A phase ends when the condition the user named holds, not when the current task list empties. "Only
the security advisories remain" means every other named debt is gone — not that the task in hand is
green. Write the exit condition down when the phase starts and read it back before saying "done".

## 5. A dual-remote release is verified by trees, not by SHAs

Two forges that each merge `development → main` independently produce **different merge commits**
for the same content. Comparing `git ls-remote <remote> refs/heads/main` and treating unequal SHAs as
a failed release sends you chasing a non-problem.

```bash
git fetch <forge> main
git rev-parse <forge>/main^{tree}          # compare the trees
 git merge-base --is-ancestor <release-commit> <forge>/main   # the tag's commit must be in main
```

Rules that held up:

- Tag the **release commit** (the tip whose tree CI exercised, or an ancestor of it in main's
  history) — not a merge node, and not a commit CI never saw.
- Require every forge's `main` to move, then compare trees; equal content under different merge
  SHAs is a successful release.
- Push the tag to every remote and read back the **tag object id** with
  `git ls-remote --tags <remote> <tag>`. When both forges' mains point at the **same commit**, one
  signed tag object pushed to both is the stronger claim: identical object ids prove both carry it.
  When the mains diverged (each forge merged independently), they cannot share an object id — tag
  each remote's own head, then prove equality of *content* per remote:
  `git rev-parse <tag>^{tree}` on both must match the release tree, and each tag must be signed.
  State which case applies in the release note; a reader who expects identical ids will otherwise
  read the divergence as a failed release.
- **A merge reported as `200` is a request, not a result.** After merging by API or CLI, `git fetch`
  the forge and read `<remote>/<branch>` before moving on. The same applies to a pull-request create:
  treat the printed URL/number as a claim and confirm the ref moved.
- When the tag already exists below the highest release number, retag at the next number above it
  and say so in the release body — deleting a published tag silently breaks consumers.

## 5b. A retroactive tag names a published state, not "the commit before the new work"

When versions are assigned after the fact ("call the previous one 0.1.0, this one
0.2.0"), the boundary is **what was published**, not where the next feature was
started. Everything that accumulated since the last published point belongs to
the new version — an unpublished fix that happened to land just before the new
work is not part of the old release, and putting it there invents a release that
never existed on the forge.

The cheap way to get this wrong: tag the last commit *before* the feature you
just finished, which silently hands that feature (and every unmerged fix under
it) to the previous number. Find the published point instead — the remote's
branch tip or the commit the last pushed artefact was built from — and tag that.

```sh
git log --oneline origin/main..HEAD        # exactly what a tag would carry
git diff --stat <candidate-tag> HEAD       # must read as the new version's feature set
```

Sign and state the meaning in the tag body (annotated, `git tag -s -a`): a tag
message that lists the feature set is what lets a later reader tell whether the
mapping was deliberate. Verify with `git tag -v` after creating, push tags
explicitly (`git push origin <tag>…`), and read the tag **object** ids back from
each remote — an annotated tag's object id is not the commit id it points at.

## 6. Built binaries ship as release assets, not as tracked files

Generated deliverables — Office documents, zip containers, compiled PDFs from a generator — are not
committed. The tree carries the **generator and its spec** (the diffable source of truth); the
Release carries the built artefacts.

Why: OOXML/ODF are zip containers, so git shows every rebuild as an opaque blob rewrite — no review,
no bisect, and permanent history bloat for something reproducible in one command.

Mechanics:

```gitignore
# built deliverables — distributed via Releases
<pkg>/Built-Artifact.pptx
.local-build/
```

```bash
gh release create v1.0.0 --title "v1.0.0 — …" --notes "…" \
  .local-build/a.pptx .local-build/a.potx .local-build/out.pdf
gh release view v1.0.0 --json assets -q '.assets[] | .name + " " + (.size|tostring)'
```

Always read the asset list back with sizes: `gh release create` reports a URL even when a path
argument did not resolve, so an unverified release can be silently missing the file users came for.
The README then points readers to the Release for "download and use" while documenting the rebuild
command, so the two distributions stay explainable.

## Pitfalls

1. **A green matrix validates that tree, not the numbers around it.** Tag the commit whose tree the
   run exercised; if later commits follow, either re-run or tag the commit that ran and say so.
2. **Do not fix a release blocker by changing an error contract.** Making a long-standing
   never-throwing promise throw, or re-pointing how a tool resolves, converts one red job into several
   and re-opens the release. Minimal fix on a release branch; contract changes get their own cycle.
3. **A flaky gate is not a passing gate.** Rerun the single failed job to prove flakiness, then fix the
   race; a green rerun is evidence for "flaky", never a substitute for the fix.
4. **Never `--amend` a commit that has already been pushed.** Amending rewrites the commit id under a
   published branch, so the remote and local histories diverge and the next push is rejected or needs a
   force — on someone else's repo that is a rewrite of published history. Add a new commit instead, and
   if the change belongs with the earlier work, say so in the new message rather than retrofitting it.
   The same applies to a tag that is already on a remote: retag at the next number above it, never move it.
5. **Verify a push by reading the remote, per artefact.** Branch head, tag object id and the
   forge-side verification flag are three separate claims: `git ls-remote` for the refs, and
   `gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.verified` for the signature
   claim. A successful `git push` proves the transfer, not that the forge shows the commit as verified.
6. **A queued build is not a released artefact.** Tagging and merging finish the *source* side of a
   release; until the image/package job has actually run, there is nothing to deploy. A job sitting in
   `queued` on a hosted label with a frozen `started_at` is waiting on provider capacity — check the
   job's `labels`/`status`, not the workflow. The `actions/runners` endpoint lists self-hosted runners
   only, so `total_count: 0` on a repo that uses `ubuntu-latest` is normal and proves nothing.
7. **A local build is not a substitute unless the token can publish it.** Running the container build
   on the workstation and pushing it to the registry changes the release's provenance; confirm the
   registry write permission first (`curl -sSI -H "Authorization: Bearer $TOKEN" https://api.github.com/user`
   and read `x-oauth-scopes` for `write:packages`). Without it, say the build is blocked rather than
   deploy a locally built image under the release tag.
