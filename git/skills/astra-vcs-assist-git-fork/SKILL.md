---
name: astra-vcs-assist-git-fork
description: "Fork and adapt upstream open-source projects — dual-remote setup, branch strategy, copyright handling, README adaptation, and upstream sync."
version: 1.3.0
author: alrcatraz
platforms: [linux]
metadata:
  hermes:
    tags: [fork, upstream, git, licensing, copyright, adaptation, vcs]
related_skills:
  - astra-vcs-assist-git-init
  - astra-vcs-assist-git-release
  - astra-vcs-assist-git-sync
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

# astra-vcs-assist-git-fork — Fork & Adapt Upstream

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

### 5. AGENTS.md

Add a fork notice at the top:

```markdown
> **astra fork** — Part of [astra-aiagent-infra](...).
> Adapted from [upstream](...) (MIT).
```

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

## Pitfalls

- **Check .gitignore** — are `.env`, large binaries, or generated files excluded?
- **Scan README for upstream URLs** — search for the upstream org/user name; there may be multiple URLs to update
- **LICENSE must retain upstream copyright** — do not replace, only append
- **Remove upstream promotional blockquotes** — keep only factual attribution
- **Check `grep -r "upstream-org" .`** for any remaining upstream references in source files, configs, or CI scripts

## References

- `references/astra-camofox-browser.md` — concrete walkthrough of adapting an upstream browser fork
- `references/upstream-pr-from-selfhosted-git.md` — submitting patches from your fork back to upstream as PRs
