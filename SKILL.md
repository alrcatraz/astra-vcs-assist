---
name: astra-vcs-assist
description: "VCS workflow orchestrator — GPG key management, Git init, commit workflow, release management, and cross-machine sync. Routes to VCS-specific sub-skills by task type."
version: 1.0.0
platforms: [linux]
related_skills:
  - astra-vcs-assist-gpg-key
  - astra-vcs-assist-git-init
  - astra-vcs-assist-git-dev
  - astra-vcs-assist-git-release
  - astra-vcs-assist-git-sync
---

# astra-vcs-assist — Version Control Workflow Orchestrator

## Trigger Conditions

Load this skill when:
- Setting up or extending version control workflow infrastructure
- Adding support for a new VCS (Git, Mercurial, Fossil, etc.)
- Planning GPG signing strategy across machines
- Designing the overall Git/GPG workflow for a project
- Registering a new VCS sub-skill

## Architecture

astra-vcs-assist is a **thin orchestrator** organised by domain. Each domain has its own sub-skill tree under its own directory. Sub-skills are stored in the main repository and symlinked into Hermes' skill discovery path.

```
astra-vcs-assist (orchestrator)
  │
  ├── gpg/                     ← VCS-independent: GPG key lifecycle
  │   └── astra-vcs-assist-gpg-key
  │
  ├── git/                     ← Git-specific workflow
  │   ├── astra-vcs-assist-git-init      Repo bootstrap
  │   ├── astra-vcs-assist-git-dev       Daily development flow
  │   ├── astra-vcs-assist-git-release   Commit cleanup + tagging
  │   └── astra-vcs-assist-git-sync      Push + remote + transfer
  │
  └── future VCS domains
      └── hg/                  ← Mercurial (when needed)
```

### Principles

1. **Domain separation.** GPG is VCS-agnostic — it lives at the top level, not under `git/`. New VCS support gets its own directory at the top level.

2. **Sub-skills own their domain.** The hub never duplicates sub-skill logic. It only routes and coordinates.

3. **Shared under `references/`.** Cross-cutting knowledge (Conventional Commits spec, force push safety) lives in `git/references/`. GPG-specific references live in `gpg/references/`.

4. **Scripts are reusable.** CLI scripts in `scripts/` are generic. VCS-specific scripts go under `git/scripts/`.

5. **Every workflow step is user-confirmed.** Present the plan → ask "proceed?" → execute → verify. (SOUL.md #1.1: 研究先行，方案求精).

## Sub-Skill Routing

The definitive routing table is in `routing.yaml` (machine- and human-readable).
Below is a summary for quick reference:

| Task type | Delegate to |
|:----------|:------------|
| GPG key management (check, import, generate, rotate) | `skill_view(name='astra-vcs-assist-gpg-key')` |
| Repository init (README, LICENSE, gitconfig, GPG binding) | `skill_view(name='astra-vcs-assist-git-init')` |
| Daily dev workflow (branch, stage, commit, stash) | `skill_view(name='astra-vcs-assist-git-dev')` |
| Release prep (squash, split, reword, tag, changelog) | `skill_view(name='astra-vcs-assist-git-release')` |
| Push, sync, transfer (dual remote, force push, bundle) | `skill_view(name='astra-vcs-assist-git-sync')` |

### Loading a Sub-Skill

Sub-skills live inside this repository and are symlinked into `~/.hermes/skills/`. Hermes discovers them automatically. To load a specific sub-skill:

```
skill_view(name='astra-vcs-assist-git-init')
```

Or let Hermes' auto-scan match the trigger keywords.

## VCS Domains

### GPG Signing & Encryption

GPG key management is VCS-agnostic — the same key signs Git commits,
Mercurial changesets, or email. This domain covers the full lifecycle:

| Sub-skill | Covers | Status |
|:----------|:-------|:------:|
| `astra-vcs-assist-gpg-key` | Key check/import/generate, VCS signing config, headless passphrase caching, cross-machine key strategy, rotation | ✅ Phase 1 |

### Git

Git is the first supported VCS. Its sub-skills cover the full workflow:

| Phase | Sub-skill | Covers |
|:------|:----------|:-------|
| Setup | `astra-vcs-assist-git-init` | README, LICENSE, .gitignore, gitconfig, GPG binding |
| Daily | `astra-vcs-assist-git-dev` | Branch, stage, commit, stash, merge/rebase during development |
| Release | `astra-vcs-assist-git-release` | Commit reorganisation, message writing, tagging, changelog |
| Sync | `astra-vcs-assist-git-sync` | Push, force push, dual remote, git bundle |

## SOUL.md Alignment

- **§3.3 活用版本管理** — This project is about disciplined version control; SOUL requires active use of version management for all project artefacts.

## Pitfalls

1. **Resist scope creep.** The hub's job is routing, not implementing GPG or Git logic. If you find yourself writing signing procedures inside the hub SKILL.md, that content belongs in `astra-vcs-assist-gpg-key`.

2. **Sub-skills inside the repo, not separate repos.** Unlike some Astra projects, sub-skills are stored inside this repo (under `gpg/` or `git/skills/`) and symlinked out. Edit them via their real path, not via `skill_manage`.

3. **New VCS domains get their own directory.** Adding Mercurial support means creating `hg/` at the top level — not stuffing it into `git/`.

4. **Shared scripts stay at root `scripts/`.** GPG-related scripts live in `scripts/` (not `gpg/scripts/`), because they're VCS-agnostic. Git-specific scripts live in `git/scripts/`.

5. **`automated-gpg-commit-push` is the predecessor.** That skill (devops category) contains HomeCentre01-specific HomeCentre01-specific credential tricks. Its generic GPG knowledge has been absorbed into `astra-vcs-assist-gpg-key`. If you're on HomeCentre01, load both — the old skill has machine-specific debugging notes.

6. **Credentials in GPG, never in skill text.** Password decryption always goes through `gpg --pinentry-mode loopback` or `gpg-preset-passphrase`. Never hardcode.
