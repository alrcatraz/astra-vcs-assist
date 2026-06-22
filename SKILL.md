---
name: astra-vcs-assist
description: "VCS workflow orchestrator — GPG key management, Git init, commit workflow, release management, and cross-machine sync. Routes to VCS-specific sub-skills by task type."
version: 1.0.0
author: ANGELIA
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

| Task type | When to load | Delegates to |
|:----------|:-------------|:-------------|
| GPG key check / import / generate / rotate | User mentions GPG keys, signing, or encryption setup | `astra-vcs-assist-gpg-key` |
| New repo bootstrap (README, LICENSE, .gitignore, gitconfig) | User says "init repo", "start a new project", or "bootstrap" | `astra-vcs-assist-git-init` |
| Daily git workflow (branch, stage, commit during dev) | User says "working on feature X", "commit this", or mid-development state | `astra-vcs-assist-git-dev` |
| End-of-phase commit prep (squash, split, reword, tag) | User says "clean up commits", "prepare release", "squash before merge", "tag version" | `astra-vcs-assist-git-release` |
| Push, dual remote, bundle transfer | User says "push", "sync to remote", "transfer commits" | `astra-vcs-assist-git-sync` |

### Loading a Sub-Skill

Sub-skills live inside this repository and are symlinked into `~/.hermes/skills/`. Hermes discovers them automatically. To load a specific sub-skill:

```
skill_view(name='astra-vcs-assist-git-init')
```

Or let Hermes' auto-scan match the trigger keywords.

## VCS Domains

### Git (Phase 1)

Git is the first supported VCS. Its sub-skills cover the full workflow:

| Phase | Sub-skill | Covers |
|:------|:----------|:-------|
| Setup | `astra-vcs-assist-git-init` | README, LICENSE, .gitignore, gitconfig, GPG binding |
| Daily | `astra-vcs-assist-git-dev` | Branch, stage, commit, stash, merge/rebase during development |
| Release | `astra-vcs-assist-git-release` | Commit reorganisation, message writing, tagging, changelog |
| Sync | `astra-vcs-assist-git-sync` | Push, force push, dual remote, git bundle |

### Planned Domains

| VCS | Status | Notes |
|:----|:-------|:------|
| Mercurial | 🔮 Future | If needed |
| Fossil | 🔮 Future | If needed |

## SOUL.md Alignment

- **§3.2 代码规范**: Conventional Commits, commit message discipline enforced by `git-dev` and `git-release`
- **§3.3 活用版本管理**: Everything in this project is about version management discipline
- **§x.x 凭证管理**: GPG keys managed by `gpg-key` sub-skill; repo credentials by `git-init`
- **§x.x 双备份/多 remote**: Coverage in `git-sync`

## Pitfalls

1. **Resist scope creep.** The hub's job is routing, not implementing GPG or Git logic. If you find yourself writing signing procedures inside the hub SKILL.md, that content belongs in `astra-vcs-assist-gpg-key`.

2. **Sub-skills inside the repo, not separate repos.** Unlike some Astra projects, sub-skills are stored inside this repo (under `gpg/` or `git/skills/`) and symlinked out. Edit them via their real path, not via `skill_manage`.

3. **New VCS domains get their own directory.** Adding Mercurial support means creating `hg/` at the top level — not stuffing it into `git/`.

4. **Shared scripts stay at root `scripts/`.** GPG-related scripts live in `scripts/` (not `gpg/scripts/`), because they're VCS-agnostic. Git-specific scripts live in `git/scripts/`.

5. **`automated-gpg-commit-push` is the predecessor.** That skill (devops category) contains HomeCentre01-specific HomeCentre01-specific credential tricks. Its generic GPG knowledge has been absorbed into `astra-vcs-assist-gpg-key`. If you're on HomeCentre01, load both — the old skill has machine-specific debugging notes.

6. **Credentials in GPG, never in skill text.** Password decryption always goes through `gpg --pinentry-mode loopback` or `gpg-preset-passphrase`. Never hardcode.
