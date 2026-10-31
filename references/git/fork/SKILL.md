---
name: astra-vcs-assist-git-fork
description: "Fork and adapt upstream open-source projects — dual-remote setup, branch strategy, copyright handling, README adaptation, and upstream sync."
version: 1.4.3
author: <owner>
platforms: [linux]
metadata:
  hermes:
    tags: [fork, upstream, git, licensing, copyright, adaptation, vcs]
triggers:
  - fork workflow
  - fork upstream
  - fork adaptation
  - open source fork
  - git fork setup
  - upstream fork management
  - fork documentation
  - fork licensing
tools:
  - git
---

# `references/git/fork` — Fork & Adapt Upstream

## Trigger Conditions

Load this skill when:

- You need to fork an upstream open-source project and set up your own remote
- Adapting a fork with infrastructure changes (Docker, config, CI)
- Handling copyright and licence lines in a fork
- Structuring a fork's README (Astra adaptations + upstream attribution)
- Preparing a PR from your fork back to upstream
- Committing fork-specific changes in the right order

## Related VCS Skills

| Topic | Skill |
|:------|:------|
| Repository init (README, LICENSE, .gitignore, GPG) | `skill_view('astra-vcs-assist-git-init')` |
| Licence selection guide | `skill_view('astra-vcs-assist-git-init', file_path='references/license-guide.md')` |
| PR submission from fork to upstream | `skill_view('astra-vcs-assist-git-release')` |
| GPG key management | `skill_view('astra-vcs-assist-gpg-key')` |
| Dual-remote push & sync | `skill_view('astra-vcs-assist-git-sync')` |

## Workflow

> **When upstream will not take our plumbing (CI/nix/packaging), read the
> umbrella-level `../../tower-model.md` first**
> (`skill_view('astra-vcs-assist', file_path='references/tower-model.md')`) —
> the universal tower-and-projection model: stack INFRA/ADAPT/PATCH/BASE in one
> linear tower, serve audiences via slice-projections, never parallel branches.
> This skill is that model's operational landing for the fork case.

### 1. Git Setup

```bash
# 1. Keep upstream remote (read-only)
git remote rename origin upstream

# 2. Add your remote
git remote add origin https://github.com/YOUR_USER/REPO_NAME.git

# 3. Create adaptation branch (not master)
git checkout -b your-branch-name
```

### 2. Repo / Directory Naming

- If part of the astra ecosystem, use `astra-*` prefix
- Keep consistent with the `astra-aiagent-infra` portal registry

### 3. LICENSE

MIT License fork convention:

```diff
 Copyright (c) 2025 Original Author
+Copyright (c) 2026 YOUR_GITHUB_USER
```

- **Keep upstream copyright line** — do not remove or modify
- **Append your own copyright** — use your GitHub account name, not a nickname

### 4. README Documentation

Structure order: **your info > upstream attribution > original content**

```
┌─ astra header ──────────────────────┐
│  Logo · Title · badges → your repo  │
│  "Part of astra-aiagent-infra"      │
│  "Adapted from upstream (MIT)"      │
├─ Astra Adaptations (expandable) ────┤
│  Table listing all adaptation diffs │
├─ ─── divider ───                    │
├─ Quick start (clone URL → your repo)│
├─ ─── divider ───                    │
├─ Upstream original content ...      │
└─────────────────────────────────────┘
```

**Badges:** Point to your repo (stars, last commit), not upstream.

### 5. Fork documentation: the AGENTS pair, not a FORK.md

Fork facts are carried by the project's agent-instruction files, split by trust
layer — never by a standalone `FORK.md`. A single FORK.md duplicates the README,
has no disclosure boundary, and goes stale the moment topology changes.

- **`AGENTS.md` (public layer)** — a short fork notice near the top, plus
  publishable adaptation detail under the repo's agent-doc convention
  (e.g. `.agents/adaptations.md`): why the fork exists, the adaptation table,
  the external interface contract, build instructions. Repoint any reference to
  a retired FORK.md at these files.
- **`AGENTS.local.md` (private layer)** — branch map, remote topology,
  multi-remote version rules, credential pointers. Disclosed only to remotes at
  ≤ L1; gitignore it when the repo has no ≤ L1 remote (see
  `astra-vcs-assist` → `references/git/init/` for the decision tree and skeletons).

```markdown
## This is a fork

Adapted from [upstream](https://github.com/OWNER/REPO) (MIT). Why the fork
exists, the adaptation table, and the interface contract live in
[.agents/adaptations.md](.agents/adaptations.md); topology and branch-model
facts live in the gitignored `AGENTS.local.md`.
```

Migrating an existing FORK.md: `git rm` it on the work branch, move the
publishable content into the AGENTS pair, then re-grep the whole skill library
for `FORK.md` and repoint every surviving mention — a retired filename left in
another skill's prose re-teaches it to the next agent.

### 6. Commit Strategy

Split different concerns into separate commits:

| Commit type | Content |
|:------------|:--------|
| `chore:` | Copyright, LICENSE, metadata |
| `fix:` | Bug fixes, compatibility changes |
| `docs:` | README / AGENTS.md documentation |
| other | Conventional Commits as appropriate |

If intermediate steps add-and-remove (e.g. adding upstream promo text then deleting it), squash with `git reset --soft HEAD~2`.

### 7. Push to GitHub

- Create a **blank remote repo** (no README/.gitignore/LICENSE template)
- Push only your adaptation branch (e.g. `astra`), **not upstream branches** (e.g. `master`)
- Set default branch to your adaptation branch on GitHub

### 8. Release & Sponsors

- **Do not** publish a v1.0.0 release for only infrastructure adaptation — wait for substantive new features
- **Do not** add a Sponsors button for minor adaptations — wait until the fork grows independent value

### 9. GitHub Fork Object vs Standalone Private Repo

GitHub refuses to convert a **public** fork to private (API 422 "Public forks
can't be made private") and the API-created fork keeps its network identity.
So for a long-lived private fork: create a standalone private repo, push
mirrored upstream branches into it, and sync manually. You lose the "Sync fork"
button; gain privacy + CI control.

A GitHub **fork object** carries a network identity and a "Sync fork"
affordance but cannot be private if created public. An **independent repo**
seeded from upstream has no such binding. Running both side by side — one
holding the PR-carrier branches, the other the integration + INFRA branches —
splits history: the same patch lands twice under different SHAs, and
identically-named branches come to mean different things per remote. Detect it
early:

```bash
git diff --name-only <up-base>..<branch-a> <up-base>..<branch-b>   # content same?
git show <sha-a> | git patch-id --stable                          # compare against <sha-b>
```

Equal `patch-id` ⇒ duplicate history, keep one lineage. Unequal ⇒ genuine
divergence, resolve before merging anything. Collapse to one repository whose
branches follow the tower model; retire the other as archive, never delete (the
PR-head branch is bound to the open upstream PR by SHA — see
`references/collapse-to-public-with-open-pr.md`).

### 10. Submodules behind auth walls

A `.gitmodules` SSH URL fails for anonymous CI/build clones. Fix per-clone:
`git config submodule.<path>.url https://... && git submodule update --init <path>`
— do not commit the rewrite unless the fork owns the submodule too.

## Pitfalls

- **Establish the repo's CURRENT topology before planning fork work.** A fork's
  layout is a moving target: a two-repo private/public split gets consolidated
  into one repo, branches migrate, a repo retires to archive. Any doc describing
  the arrangement — including the build skill for that instance and the fork's
  own design doc — records *intent at the time of writing*, not present state.
  Verify per instance before proposing a plan:
  ```bash
  git remote -v && git branch -a -vv && git worktree list
  git log --oneline origin/main..origin/development     # direction of divergence
  ```
  Then act on the graph. Planning new content (a local AGENTS layer, a branch
  model) into a repo that is already retired or mid-consolidation wastes the
  whole plan — check first, and re-read the instance doc's retirement clause.
- **A `fix/*` or `feat/*` branch merges to `development`, never straight to
  `main`.** `main` is the release line and receives features only through a
  `development → main` PR. A leftover work branch is easy to mistake for
  "just one commit behind main, merge it" — that reasoning skips the integration
  tier and lands an unreviewed fix on the release line. Cut the local
  `development` from its remote, merge the work branch there (`--no-ff`, message
  `merge: <branch> into development`), and leave the `development → main`
  promotion for the release step. Full three-tier rules:
  `skill_view('astra-vcs-assist', file_path='references/branch-protection-model.md')`.
- **`AGENTS.md` is a protected agent-instruction file — writes need live
  approval.** Editing it (or `AGENTS.local.md`) raises a confirmation prompt,
  and a prompt that times out is a REFUSAL, not consent: the write is blocked
  and re-attempting it through `terminal`/`execute_code` is forbidden. Surface
  the block to the user, show the proposed text inline, and ask them to
  re-trigger approval — never route around the guard. Content that must land
  unattended belongs in a normal file under `.agents/`, which carries no such
  guard.
- **Check .gitignore** — are `.env`, large binaries, or generated files excluded?
- **Scan README for upstream URLs** — search for the upstream org/user name; there may be multiple URLs to update
- **LICENSE must retain upstream copyright** — do not replace, only append
- **Remove upstream promotional blockquotes** — keep only factual attribution
- **Check `grep -r "upstream-org" .`** for any remaining upstream references in source files, configs, or CI scripts

## References

- `references/astra-camofox-browser.md` — concrete walkthrough of adapting an upstream browser fork
- `references/upstream-pr-from-selfhosted-git.md` — submitting patches from your fork back to upstream as PRs
- `references/collapse-to-public-with-open-pr.md` — retiring a private fork repo while an upstream PR stays open (PR-carrier red line, archive ordering, filter-repo modes)
