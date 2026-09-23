---
name: astra-vcs-assist-versioning
description: "Three-layer SemVer 2.0 versioning scheme for the astra-vcs-assist repo, covering official/personal/agent layers and the dual-branch release workflow between Gitea and GitHub."
version: 1.4.0+alrcatraz.1.0.0
author: alrcatraz
platforms: [linux]
metadata:
  hermes:
    tags: [semver, versioning, dual-branch, gitea, github, release]
related_skills:
  - astra-vcs-assist
  - astra-vcs-assist-git-release
  - astra-vcs-assist-git-sync
triggers:
  - version scheme
  - versioning
  - three-layer versioning
  - dual branch release
  - public branch preparation
  - version stripping
  - semantic version tag
---

# astra-vcs-assist-versioning — Three-Layer Versioning & Dual-Branch Release

## Overview

This skill documents the versioning scheme used by the `astra-vcs-assist`
repository. It covers two distinct but related workflows:

1. **Three-layer version numbering** — how official, personal, and agent
   versions relate
2. **Dual-branch release** — how to prepare `main` (Gitea) and `public`
   (GitHub) branches from a development copy

## Promotion Pitfalls

Read before pushing any layer.

### 1. Instance-copy commits often bundle agent-layer bumps — strip them

Instance-copy commits (`~/.astra/repos/astra-vcs-assist`) routinely pair
content changes with agent-layer version bumps. When promoting to Gitea main,
strip the `.angelia.*` suffix back to 3-layer. Working procedure:

```bash
git fetch ~/.astra/repos/astra-vcs-assist main   # FETCH_HEAD
git cherry-pick -n FETCH_HEAD                                   # stage, don't commit
# batch-replace "version: X.Y.Z+alrcatraz.A.B.C.angelia.*" → "X.Y.Z+alrcatraz.A.B.C"
# in SKILL.md, VERSION (plain number, NO "version: " prefix!), and all sub-skill SKILL.md
git commit
```

VERSION file format gotcha: the repo-root `VERSION` file is a bare version
string (`1.2.0+alrcatraz.1.0.0`) with no `version:` prefix — batch replaces
must handle it separately from YAML frontmatter.

### 2. Content classification for `public` — private-multi-remote goes Gitea-only

Rule: GitHub = minimal public subset, Gitea = +private, instance copy = +local. Anything referencing the private multi-remote architecture is
Gitea-only, never public:

- Gitea domain/URLs (`git01.wrt.astra-lab.org`), instance version tables
- "Double-push gitea+github" workflow instructions with `git push -u gitea ...`
- Branch layout naming `main` (Gitea) vs `up/public` projection workspace

Subset direction matters: Gitea MAY have content GitHub lacks (that's the
point); GitHub must NEVER have content Gitea lacks. Verify with
`git diff main public` — allowed diffs: `gitea/` dir, version suffixes, and
private-architecture docs. Everything else is a leak.

### 3. Terminology: it is THREE-TIER, not "4-layer"

`1.3.0+alrcatraz.1.0.0.angelia.0.0.0` = 3 LAYERS (Official / Personal /
Agent); the string has 3 numeric groups but the + build-metadata segments are
NOT extra layers. Use the documented layer names (Official/Personal/Agent) —
colloquial "4-layer" confused the user.

## When NOT to Use Three-Layer Versioning

The 3-layer scheme is for INTERNAL / skill-class repos that carry personal
information and need owner-segment provenance in the version string.

Independent PUBLIC projects seeded from upstream use PLAIN SemVer tags
(`v3.8.50` style): no owner segments, no build metadata. Tag fresh from
your own main — check `git tag -l` first (upstream tags are usually not
cloned; if any exist, delete and rewrite them). Decision rule:
personal info to protect / owner provenance needed → 3-layer;
otherwise plain SemVer.

## Three-Layer Version Scheme

Uses SemVer 2.0 build metadata (`+`) to express the inclusion chain
without affecting priority comparison (SemVer 2.0 §10).

| Layer | Format | Example | Where |
|:------|:-------|:--------|:------|
| Official | `MAJOR.MINOR.PATCH` | `1.0.0` | GitHub `public` branch |
| Personal | `MAJOR.MINOR.PATCH+\<owner\>.\<seg\>` | `1.0.0+alrcatraz.0.0.0` | Gitea `main` branch |
| Agent | `MAJOR.MINOR.PATCH+\<owner\>.\<seg\>.\<agent\>.\<seg\>` | `1.0.0+alrcatraz.0.0.0.angelia.0.0.0` | Private copy |

### Rules

- Each layer's segment increments independently as that layer's content changes
- Initial state uses `0.0.0` for personal and agent segments (no established
  differences from the layer above)
- After pushing and comparing, non-zero values indicate actual differences
- `VERSION` file at repo root holds the current private-copy version
- Each SKILL.md YAML frontmatter has a matching `version:` field

### Stripping Rule

When publishing to a higher (cleaner) layer, strip lower-layer suffixes:

```
Private:    1.0.0+alrcatraz.1.2.3.angelia.4.5.6
           ↓ (strip angelia)
Gitea:     1.0.0+alrcatraz.1.2.3
           ↓ (strip alrcatraz)
GitHub:    1.0.0
```

## Three-Layer Content Architecture — Subsets, not Stripping

> This section is the authoritative implementation detail of the umbrella-level
> `references/tower-model.md` «Projection B · disclosure state» (sanitisation
> checklist and diff verification are governed here); see that file for the
> theory layer.

The dual branches are **nested content subsets**, not independent lines.
Content flows by ADDITION as you move up the layers; it is never "stripped"
from a fuller layer into a smaller one (that was the sync-public.sh model —
DEPRECATED, never adopted; the manual workflow below is authoritative):

```
GitHub (public branch)  = minimal public subset
  Gitea (main branch)   = GitHub + private content (gitea/, internal host refs)
  Instance copy (.astra/repos) = Gitea + machine-local (untracked skills,
                               local commits, local routing.yaml entries)
```

Hard rules:
- **Never add content to a higher layer that is missing from the layer
  below.** A public-only commit (e.g. the fork skill added straight to
  `public`) is a workflow gap — cherry-pick it into `main` so Gitea stays
  a superset.
- **Instance copy never pushes.** Machine-local commits (e.g. git-dev
  collaboration-docs) and untracked skills (git-review, vcs-review routing
  entries) stay in `~/.astra/repos/<repo>`; the dev repo
  `~/Projects/astra/<repo>/` is the only place edits are committed for
  Gitea/GitHub.
- Version suffixes strip downward (private→Gitea→GitHub) per the Stripping
  Rule below; content itself does not strip — it is added upward.

### Dual-remote division of labour — direction is universal, layout is per-repo

The *direction* of the dual-remote split is consistent across every
astra dual-track repo: **Gitea = full / private-bearing track, GitHub =
sanitised / public track.** GitHub must never carry content Gitea lacks.
But the *branch layout* that realises this differs by repository — do NOT
copy this skill's `main (Gitea)` / `up/public → GitHub main` mapping onto another
repo.

- This skill / astra-vcs-assist repo: dev on the development copy
  (`~/Projects/astra/astra-vcs-assist/`), push `main`→Gitea and derive
  `up/public`→GitHub `main`, with **plain SemVer tags** (`vX.Y.Z`).
- Other repos (e.g. astra-agent-constellation) instead: develop on
  `development` → merge to local `main` → push `main`→**Gitea
  `development` branch** → sanitise local `main` into `public` →
  push `public`→**GitHub `development` branch**. Single-layer SemVer
  (`v0.x.y`). Release titles carry **only** the version (`v0.2.3`).
- **The per-repo flow is governed by that repo's `AGENTS.md`**, not by
  this skill. If a repo has a documented release procedure in its
  AGENTS.md, follow the AGENTS flow; treat this skill as the general
  dual-remote principle + the astra-vcs-assist-specific layout.

General dual-track release checklist (any repo):
1. Merge/cherry-pick the dev work onto the full track branch (`main`).
2. Push the full branch to the Gitea dev/delivery branch.
3. Derive the sanitised branch **from the full branch** (never `git merge
   main` into public — that drags private files back in). `git rm --cached`
   the private-only paths, strip machine names / host IPs / real domains
   to placeholders, then scan the whole staged tree for leaks.
4. Push the sanitised branch to the GitHub dev/delivery branch. If the
   remote sanitised line has diverged, this is a `--force` push (normal for
   the public track) — confirm with the user first.
5. **Advance each remote's `main` by PR from that remote's `development`**
   — `development` → `main` (Gitea PR + GitHub PR), merged as a merge
   commit. A release is NOT done until both remotes' `main` reflect the new
   version. Pull-request-first is a hard user expectation — never flat-out
   release without it.
6. Tag each track's `vX.Y.Z` on the corresponding commit and create
   releases with title = version only.

## Side-Branch Archaeology (before merging)

When a side branch (e.g. `main-sync`) introduces tooling, verify it was ever
ADOPTED before merging — don't merge on faith:
1. `git branch --contains <sha>` — is the content reachable from main?
2. Compare commit timestamps: a script committed hours before main adopted a
   different approach (e.g. the manual dual-branch flow) was superseded.
3. `git log --all -S '<symbol>'` + grep docs — was it ever referenced?
`sync-public.sh` (a9f9f0b, main-sync) failed all three: never in main, no doc
references, superseded within 2 hours by the manual flow. The branch was
deleted; do not reintroduce the script.

## Instance-Copy Merge Pitfall

Syncing `~/.astra/repos/<repo>` from the dev repo: an **untracked directory
in the instance copy blocks the merge** when new main introduces a tracked
file of the same name (e.g. untracked `git-fork/` vs incoming tracked
`git/skills/astra-vcs-assist-git-fork/`). Remove/back up the untracked dir
BEFORE `git fetch dev && git merge`, then re-verify the machine-local
content still loads.

## Dual-Branch Release Workflow

All work happens on the **development copy** (e.g. `~/Projects/astra/astra-vcs-assist/`).

### Step 1: Personal version (→ Gitea)

```bash
git checkout main
# Verify version: fields have personal suffix
grep "version:" SKILL.md
grep "version:" gitea/astra-vcs-assist-gitea/SKILL.md
cat VERSION
# Commit personal changes
git add -A
git commit -m "feat: ..."
```

### Step 2: Public version (→ GitHub)

```bash
git checkout -b up/public main

# Remove internal-only directories
git rm -r gitea/

# Strip personal version suffixes back to official
# All SKILL.md: 1.0.0+alrcatraz.X.Y.Z → 1.2.0 (iterate from last tag!)
# VERSION:      1.0.0+alrcatraz.X.Y.Z → 1.2.0

# Clean README for public consumption:
# - Remove instance-specific naming tables
# - Remove gitea/ from architecture tree
# - Remove any git01.wrt.astra-lab.org references
# - Do NOT label branches — the README badge shows a VERSION link only
# - Remove "Branch: public" or "Branches: ..." lines if present

git add -A
git commit -m "chore: prepare public release — strip gitea/ and personal suffixes"
```

### Step 3: Review

```bash
git log --oneline -3 main
git log --oneline -3 up/public
git diff main..up/public --stat
```

**Present both branches to the user for approval before pushing.**

### Step 4: Push (after user approval)

```bash
# Push full content to Gitea
git push gitea main
git tag "vMAJOR.MINOR.PATCH+<owner>.<seg>" main
git push gitea "vMAJOR.MINOR.PATCH+<owner>.<seg>"

# Switch to the projection branch and push to GitHub
git switch up/public

# For self-hosted Gitea with a self-signed certificate,
# prefix with GIT_SSL_NO_VERIFY=1:
# GIT_SSL_NO_VERIFY=1 git push gitea main

git push origin up/public:main   # note: projection → GitHub's default `main`
git tag "vMAJOR.MINOR.PATCH" up/public
git push origin "vMAJOR.MINOR.PATCH"

# Clean up the throwaway projection branch
git switch main
git branch -D up/public
```

### Step 5: After-push — compare & update agent version (private copy)

The private copy pulls from Gitea, then compares every file to determine
which have real agent-specific differences:

```bash
# On the private copy (e.g. ~/.astra/repos/astra-vcs-assist/)
git fetch origin              # origin = dev copy (or Gitea directly)

# Reset to match what was just pushed
git reset --hard origin/main

# Compare — has the private copy added anything beyond what Gitea has?
git diff origin/main HEAD
# → If empty: every file gets agent segment = 0.0.0
# → If non-empty: changed files get agent segment = 1.0.0
```

Apply the agent suffix to every SKILL.md and VERSION:

```bash
# Replace "1.2.0+alrcatraz.1.0.0" → "1.2.0+alrcatraz.1.0.0.angelia.0.0.0"
# Use patch tool (one per file) or sed for bulk
sed -i 's/^version: \([0-9.]*\)+alrcatraz\.[0-9.]*$/version: \1+alrcatraz.0.0.0.angelia.0.0.0/' \
  SKILL.md gitea/astra-vcs-assist-gitea/SKILL.md github/astra-vcs-assist-github/SKILL.md \
  gpg/astra-vcs-assist-gpg-key/SKILL.md git/skills/*/SKILL.md
echo "1.2.0+alrcatraz.1.0.0.angelia.0.0.0" > VERSION
```

Then commit with message: `chore: update agent version suffix after sync`

### Version-Difference Etiquette

- If a file on Gitea is **identical** to its GitHub counterpart (not yet
  diverged), use `0.0.0` for the personal segment
- If a file has been **modified** (personal additions), use non-zero values
- The `gitea/` directory only exists on Gitea/private — its files inherently
  differ from GitHub (non-existent there)

## Naming Convention (this instance)

| Layer | Identifier |
|:------|:-----------|
| Personal | `alrcatraz` (human operator) |
| Agent | Hermes Agent name (configured per machine, e.g. `angelia`) |

Documented in the root README (not in sub-skill docs per user preference).

## Pitfalls

1. **Do NOT hardcode version numbers in README badges.** Reference the
   `VERSION` file instead: `[VERSION](VERSION)`.

2. **README is the canonical place for naming conventions, not sub-skills.**
   Instance-specific naming tables go in the root README or AGENTS.md, not in
   platform sub-skills.

3. **The `+` build metadata in SemVer 2.0 is stripped by most tools.**
   `npm view`, `pip-compile`, etc. ignore it. It's documentation-only and
   does not survive into most dependency-resolution ecosystems — that's
   intentional.

4. **Symlinked skills cannot be patched by skill_manage.** Skills nested
   under umbrella directories (e.g. `vcs/astra-vcs-assist/git/skills/...`)
   are symlinked from the repo and not addressable by skill_manage's name
   resolution. Edit them in the repo directly.

5. **Always check existing tags before choosing a version.** Run
   `git tag -l | sort -V` first. If the repo already has `v1.1.0`, the
   next version should be `v1.2.0` or `v2.0.0`, **not** `v1.0.0`. The
   version must iterate from the latest existing tag on the target branch,
   not start from scratch.

6. **Do not label branch names in README badge headers.** A line like
   `Branch: public` or `Branches: main + public` in the README badge bar
   is meaningless to readers — they see whatever branch they're viewing
   the file from. The version reference `[VERSION](VERSION)` is sufficient.

7. **`0.0.0` means "no difference established yet".** Once a layer has
   actual content changes (e.g. `gitea/` directory on Gitea, personal
   config in a skill), use a non-zero version like `1.0.0` for that
   segment. Files that exist on only one layer inherently differ from
   the layer above and should get a non-zero personal version.

8. **NEVER push the agent suffix to any remote.** The agent layer
   (e.g. `.angelia.0.0.0`) exists only in the local `~/.astra/repos/`
   copy. Before pushing to Gitea, strip the agent segment — Gitea gets
   only the personal (`+alrcatraz.*`) version. The GitHub release gets
   only the clean official (`X.Y.Z`) version. Pushing the agent suffix
   to Gitea pollutes the personal layer with machine-local metadata.

9. **Normalise the personal segment to exactly 3 numeric parts.**
   Always write `+alrcatraz.0.0.0` (three parts), never `+alrcatraz.0`
   (one part). The 3-part convention mirrors `MAJOR.MINOR.PATCH` and
   prevents ambiguity when higher segments carry non-zero values.
   Sweep before each release:
   ```bash
   # WRONG: +alrcatraz.0$ (one trailing digit)
   # CORRECT: +alrcatraz.0.0.0$ (three trailing digits)
   grep -rn 'version:.*+alrcatraz\.[0-9]\+$' --include='*.md'
   ```

10. **Release is not done until BOTH remotes' `main` advance by PR.**
    Pushing `development` branches + creating a release is NOT sufficient —
    each remote's `main` must be advanced by a pull request from that
    remote's `development` (Gitea PR + GitHub PR), merged as a merge
    commit. Check the remote `main` SHAs before starting a release; if a
    remote `main` is stale, factor the PR into the plan up front. The
    AGENTS.md of each repo should carry the PR rule; if it documents only
    "push dev branch + tag" (as astra-agent-constellation v0.2.3 did),
    that is a gap — fix the AGENTS.md rule as part of the release.

11. **Historically-diverged remote `main` won't cleanly PR-merge.** If a
    remote `main` sat stale for releases (only `development` was pushed),
    it has diverged from the current `development` (each side has commits
    the other lacks), so `development → main` fails as "merge conflict /
    non-cleanable". Repair technique: one-time force-correct the stale remote `main` to the
    current `development` content first —
    `git push --force github up/public:main` (sanitised) / `gitea main:main`
    (full) — then subsequent releases PR-merge cleanly. Ask the user
    before forcing (it rewrites remote history). Also note local vs remote
    `main` deliberately differ in commit SHA after a remote PR merge:
    local `main` has a local merge, remote has the PR merge commit; what
    matters is the tree content matches, not the SHA.

12. **Release title is version-only; the Release Note BODY is separate and
    EXPECTED.** "Release title carries only the version" refers to the
    *title* — it does not forbid a Release Note body. An
    empty-body release is as much a failure as a prefixed title. Write a
    structured changelog in the body:
    `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file /tmp/notes.md`
    (or `gh release edit vX.Y.Z --notes-file ...` to backfill an existing
    empty release). Title = version only; Body = changelog. Both are
    required.

13. **Re-tag FORWARD when the user declares "this is the real X.Y.Z".**
    If the tag was cut, then MORE content landed on
    `main` (doc backfill, governance fixes), the user may declare the
    version should cover that content too — do NOT auto-bump to X.Y.Z+1 for a
    doc-only backfill. On explicit user word, move the tag forward to each
    track's own current `main` head:
    ```bash
    # private track
    git tag -d vX.Y.Z && git tag -s vX.Y.Z -m "vX.Y.Z (<scope>)" <gitea-main-sha>
    git -c http.version=HTTP/1.1 push gitea vX.Y.Z --force
    # public track — same tag NAME, different commit (temp annotated tag)
    git tag -s vX.Y.Z-pub -m "vX.Y.Z (public)" <github-main-sha>
    git push github vX.Y.Z-pub:refs/tags/vX.Y.Z --force
    git tag -d vX.Y.Z-pub        # local vX.Y.Z stays = private head
    ```
    Then `gh release edit vX.Y.Z --notes-file notes.md` to re-point the
    release at the moved tag. Verify `git ls-remote <remote> refs/tags/vX.Y.Z`
    equals that remote's `refs/heads/main`. Requires user approval
    (force-push + tag rewrite).

14. **Reconciling `public` against a diverged `github/main` re-imports leak
    files.** The rule "never `git merge main`
    into public" only guards `main`; merging `github/main` (when the public
    line diverged, per Pitfall 11) silently drags back every leak-topology
    file the old public track carried (`10-acp-mapping.md`, `a2a-interop.md`,
    `cordis-executor.yml.example`, ADR 0006, ...). Prevention/repair:
    - After ANY `git merge <remote>/main` into `public`, run the FULL-TREE
      leak grep (`git grep` for real hostnames/IPs/internal domains) — not
      just the changed files. Reconcile merges bring history, not diffs.
    - If leaks return, `git rm` the files + commit
      (`chore: remove <file> ... (sanitised)`), force-push the clean
      `public` to the GitHub dev branch, PR to main.
    - Treat the repo's AGENTS.md leak-exclusion list as absolute: a file on
      the list is not "acceptable because it was there" — its re-appearance
      is a bug to purge, never a reason to keep it.
