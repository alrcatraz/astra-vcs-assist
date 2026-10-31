---
name: astra-vcs-assist
description: "VCS workflow orchestrator — GPG key management, Git init, commit workflow, release management, and cross-machine sync. Routes to VCS-specific sub-skills by task type."
version: 1.5.0
author: <owner>
triggers:
  - "git 工作流"
  - "版本控制"
  - "仓库操作"
  - "提交前检查"
  - "怎么建仓库"
  - "git 初始化"
  - "双远端"
  - "fork 管理"
  - "签名提交"
platforms: [linux]
metadata:
  hermes:
    tags: [vcs, git, gitea, github, gpg, orchestrator, workflow]

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
astra-vcs-assist (macro skill: one router body, knowledge in references/)
  │
  ├── SKILL.md                 ← this router only; no procedures live here
  │
  └── references/
      ├── INDEX.md             ← pillar registry
      ├── gpg/                 ← VCS-independent key lifecycle
      │   ├── key-lifecycle/   (SKILL.md)
      │   └── gpg-key-lifecycle.md
      ├── git/                 ← Git workflow blocks
      │   ├── init/ dev/ fork/ review/ release/ sync/ remote-auth/
      │   ├── conventional-commits.md safe-force-push.md
      │   ├── git-bundle-sync.md dual-remote-push.md
      ├── github/              ← GitHub platform
      │   ├── platform/  migration/ pat/ dependabot/ issue-to-pr/
      ├── forge/               ← self-hosted Gitea/Forgejo (allowlisted: private-forge facts)
      │   └── platform/
      ├── history/             ← published-history rewriting
      │   ├── signing/  reorg//
      ├── versioning/          ← this repo's layer scheme + release line
      │   └── layers/
      ├── tower-model.md branch-protection-model.md trust-level-verification.md
      └── prose-artefact-layer-attribution.md git-credentials.md
```

### Principles

1. **Domain separation.** GPG is VCS-agnostic — it lives at the top level, not under `git/`. New VCS support gets its own directory at the top level.

2. **Sub-skills own their domain.** The hub never duplicates sub-skill logic. It only routes and coordinates.

3. **Shared under `references/`.** Cross-cutting knowledge lives at `references/` root (tower model, branch protection, trust verification, naming); per-domain shared docs live in their pillar (`references/git/conventional-commits.md`).

4. **Scripts are reusable.** CLI scripts in `scripts/` are generic and stay at the repo root; a domain-specific script goes under its pillar.

5. **Every workflow step is user-confirmed.** Present the plan → ask "proceed?" → execute → verify. (SOUL.md #1.1: research first, refine the plan).

## Sub-Skill Routing

The definitive routing table is in `routing.yaml` (machine- and human-readable).
Below is a summary for quick reference:

| Task type | Delegate to |
|:----------|:------------|
| GPG key management (check, import, generate, rotate) | `skill_view(name='astra-vcs-assist', file_path='references/gpg/key-lifecycle/SKILL.md')` |
| Repository init (README, LICENSE, gitconfig, GPG binding) | `skill_view(name='astra-vcs-assist', file_path='references/git/init/SKILL.md')` |
| Daily dev workflow (branch, stage, commit, stash) | `skill_view(name='astra-vcs-assist', file_path='references/git/dev/SKILL.md')` |
| Branch model / protection / CI gates / dual-forge push rules | `references/branch-protection-model.md` (in this skill) |
| Multi-remote topology / upstream relations / disclosure-layer clipping decisions | `references/tower-model.md` (in this skill) |
| Trust-level assignment / verification for a remote | `references/trust-level-verification.md` (in this skill) |
| Deciding which content belongs at the target level (the disclosure clip) | `references/prose-artefact-layer-attribution.md` (in this skill) |
| Measuring what a repo actually carries (values / INFRA inventory) | `python3 scripts/scan-tracked-values.py` (in this skill) |
| Release prep (squash, split, reword, tag, changelog) | `skill_view(name='astra-vcs-assist', file_path='references/git/release/SKILL.md')` |
| Fork & upstream adaptation (dual-remote fork, licensing, PR back) | `skill_view(name='astra-vcs-assist', file_path='references/git/fork/SKILL.md')` |
| Pre-commit review pipeline | `skill_view(name='astra-vcs-assist', file_path='references/git/review/SKILL.md')` |
| Push, sync, transfer (dual remote, force push, bundle) | `skill_view(name='astra-vcs-assist', file_path='references/git/sync/SKILL.md')` |
| This repo's version scheme + dual-branch release | `skill_view(name='astra-vcs-assist', file_path='references/versioning/layers/SKILL.md')` |
| Seeding an independent repo from an upstream (orphan root, rename) | `astra-vcs-assist` → `references/git/seed-from-upstream/` |
| Remote auth fails / credential helper prompts / `could not read Username` | `skill_view(name='astra-vcs-assist', file_path='references/git/remote-auth/SKILL.md')` |
| Migrating Gitea → Forgejo in place (schema version, runners) | `astra-vcs-assist` → `references/forge/migration/` |
| GitHub PAT handling (mint, scope, rotate, revoke) | `skill_view(name='astra-vcs-assist', file_path='references/github/pat/SKILL.md')` |
| Dependabot / auto-merge / PR-title gates on GitHub | `skill_view(name='astra-vcs-assist', file_path='references/github/dependabot/SKILL.md')` |
| Carry a fix upstream (fork, purity rules, PR body, CI parity) | `astra-vcs-assist` → `references/github/upstream/` |
| Take a GitHub issue through to a verified PR | `skill_view(name='astra-vcs-assist', file_path='references/github/issue-to-pr/SKILL.md')` |
| Rewriting published history (filter-repo, term purge, propagation) | `astra-vcs-assist` → `references/history/reorg/` |
| Commit signing or authorship looks wrong before a release | `skill_view(name='astra-vcs-assist', file_path='references/history/signing/SKILL.md')` |

### Loading a block

Blocks are **not registered skills** — a `SKILL.md` under `references/` is invisible to the skill
registry by design, so one skill name (`astra-vcs-assist`) owns the whole tree. Reach a block by path:

```
skill_view(name='astra-vcs-assist', file_path='references/git/dev/SKILL.md')
```

Only the repo root is linked into `~/.hermes/skills/vcs/` (see README); per-member links give blocks a
second discovery path and the loader refuses to resolve a duplicated name.
## VCS Domains

### GPG Signing & Encryption

GPG key management is VCS-agnostic — the same key signs Git commits,
Mercurial changesets, or email. This domain covers the full lifecycle:

| Sub-skill | Covers |
|:----------|:-------|
| `astra-vcs-assist` → `references/gpg/key-lifecycle/` | Key check/import/generate, VCS signing config, headless passphrase caching, cross-machine key strategy, rotation |

### Git

Git is the first supported VCS. Its sub-skills cover the full workflow:

| Phase | Sub-skill | Covers |
|:------|:----------|:-------|
| Setup | `astra-vcs-assist` → `references/git/init/` | README, LICENSE, .gitignore, gitconfig, GPG binding |
| Daily | `astra-vcs-assist` → `references/git/dev/` | Branch, stage, commit, stash, merge/rebase during development |
| Fork | `astra-vcs-assist` → `references/git/fork/` | Dual-remote fork setup, upstream adaptation, licensing, PR back |
| Review | `astra-vcs-assist` → `references/git/review/` | Pre-commit diff review pipeline, static checks |
| Release | `astra-vcs-assist` → `references/git/release/` | Commit reorganisation, message writing, tagging, changelog |
| Sync | `astra-vcs-assist` → `references/git/sync/` | Push, force push, dual remote, git bundle |
| Meta | `astra-vcs-assist` → `references/versioning/layers/` | Three-layer SemVer scheme + this repo's dual-branch release flow |

## SOUL Alignment

- **§3.3 Use version control actively** — this project is about disciplined version control; SOUL requires active use of version management for all project artefacts.

## Pitfalls

1. **Resist scope creep.** The hub's job is routing, not implementing GPG or Git logic. If you find yourself writing signing procedures inside the hub SKILL.md, that content belongs in `astra-vcs-assist` → `references/gpg/key-lifecycle/`.

2. **Sub-skills inside the repo, not separate repos.** Unlike some Astra projects, sub-skills are stored inside this repo (under `gpg/` or `git/skills/`) and symlinked out.

3. **Skill-edit sync gap — critical.** `skill_manage`/`patch` on a bridged path writes the **production** copy, not
   `~/Projects/`, so an edit can be silently discarded by the next sync. Every write goes to the dev copy and
   commits there — an edit made through the bridged path lands in the production copy and is discarded by the next sync.
4. **New VCS domains get their own directory.** Adding Mercurial support means creating `hg/` at the top level — not stuffing it into `git/`.

5. **Shared scripts stay at root `scripts/`.** GPG-related scripts live in `scripts/` (not `gpg/scripts/`), because they're VCS-agnostic. Git-specific scripts live in `git/scripts/`.

6. **`automated-gpg-commit-push` is the predecessor.** That skill (devops category) contains machine-specific credential tricks. Its generic GPG knowledge has been absorbed into `astra-vcs-assist` → `references/gpg/key-lifecycle/`. On that machine, load both — the old skill has machine-specific debugging notes.

7. **Credentials in GPG, never in skill text.** Password decryption always goes through `gpg --pinentry-mode loopback` or `gpg-preset-passphrase`. Never hardcode.
