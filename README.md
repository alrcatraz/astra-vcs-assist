# astra-vcs-assist

> Version control workflow orchestration for Hermes Agent — GPG key lifecycle,
> Git repository bootstrap, commit workflow, release management, and
> cross-machine sync. Part of the [Astra ecosystem](https://github.com/alrcatraz/astra-aiagent-infra).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Overview

`astra-vcs-assist` is a modular Hermes Agent skill and CLI toolkit that
structures the full version control workflow into domain-specific sub-skills:

- **🔑 GPG** — Key lifecycle management (check, import, generate, rotate)
- **📦 Git** — Repository init, daily dev workflow, release prep, push & sync

Each domain has its own sub-skill tree under this repository, symlinked into
Hermes' discovery path for automatic loading.

## Architecture

```
astra-vcs-assist (orchestrator)
  │
  ├── gpg/
  │   └── astra-vcs-assist-gpg-key       GPG key lifecycle
  │
  ├── git/
  │   ├── astra-vcs-assist-git-init      Repository bootstrap
  │   ├── astra-vcs-assist-git-dev       Daily development workflow  (planned)
  │   ├── astra-vcs-assist-git-release   End-of-phase commit cleanup  (planned)
  │   └── astra-vcs-assist-git-sync      Push, remote, transfer  (planned)
  │
  └── hg/  (future)
```

## Sub-skills

| Sub-skill | Status | Covers |
|:----------|:-------|:-------|
| `astra-vcs-assist-gpg-key` | ✅ Phase 1 | Check, import, generate GPG keys; configure for VCS signing; headless passphrase caching |
| `astra-vcs-assist-git-init` | ✅ Phase 1 | README, LICENSE analysis, gitconfig, GPG binding, remote setup, first commit |
| `astra-vcs-assist-git-dev` | 🔮 Planned | Branch, stage, commit, stash during active development |
| `astra-vcs-assist-git-release` | 🔮 Planned | Commit reorganisation, message writing, tagging, changelog |
| `astra-vcs-assist-git-sync` | 🔮 Planned | Dual-remote push, safe force push, git bundle |

## Quick Start

```bash
# Hermes auto-discovers these skills via symlinks.
# To load a sub-skill explicitly in a conversation:
skill_view(name='astra-vcs-assist-gpg-key')
skill_view(name='astra-vcs-assist-git-init')

# All sub-skills are in ~/.hermes/skills/vcs/
ls -la ~/.hermes/skills/vcs/
```

## Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/alrcatraz/astra-vcs-assist.git \
     ~/Projects/astra/astra-vcs-assist
   ```

2. Symlink into Hermes' discovery path:
   ```bash
   mkdir -p ~/.hermes/skills/vcs
   ln -sfn ~/Projects/astra/astra-vcs-assist \
     ~/.hermes/skills/vcs/astra-vcs-assist
   ln -sfn ~/Projects/astra/astra-vcs-assist/gpg/astra-vcs-assist-gpg-key \
     ~/.hermes/skills/vcs/astra-vcs-assist-gpg-key
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-init \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-init
   ```

3. Hermes will auto-discover the new skills on the next turn.

## Repository Structure

```
astra-vcs-assist/
├── SKILL.md               ← Hub orchestrator
├── README.md
├── LICENSE                 ← MIT
├── gpg/                    ← GPG (VCS-agnostic)
│   ├── astra-vcs-assist-gpg-key/SKILL.md
│   └── references/
├── git/                    ← Git-specific
│   ├── skills/             ← Sub-skills stored here
│   │   ├── astra-vcs-assist-git-init/
│   │   ├── astra-vcs-assist-git-dev/   (future)
│   │   ├── astra-vcs-assist-git-release/  (future)
│   │   └── astra-vcs-assist-git-sync/  (future)
│   ├── references/
│   ├── scripts/
│   └── templates/
├── scripts/               ← Shared utility scripts
├── config/
└── templates/
```

## Related Projects

- [astra-aiagent-infra](https://github.com/alrcatraz/astra-aiagent-infra) — Astra ecosystem portal
- [astra-sre](https://github.com/alrcatraz/astra-sre) — Infrastructure reliability orchestration

## License

[MIT](LICENSE) © 2026 alrcatraz

---

_🇨🇳 中文摘要：astra-vcs-assist 是 Hermes Agent 的版本控制工作流编排工具集，
涵盖 GPG 密钥管理、Git 仓库初始化、开发工作流、版本发布和跨机器同步。
采用模块化子技能架构，每个子技能独立维护在仓库目录中，通过符号链接
挂载到 Hermes 的技能发现路径。_
