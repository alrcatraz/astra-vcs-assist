# astra-vcs-assist

> Version control workflow orchestration for Hermes Agent — GPG key lifecycle,
> Git repository bootstrap, commit workflow, release management, and
> cross-machine sync. Part of the [Astra ecosystem](https://github.com/alrcatraz/astra-aiagent-infra).

<div align="center">

[![License](https://badgen.net/github/license/alrcatraz/astra-vcs-assist)](LICENSE)
[![GitHub stars](https://badgen.net/github/stars/alrcatraz/astra-vcs-assist)](https://github.com/alrcatraz/astra-vcs-assist)
[![GitHub last commit](https://badgen.net/github/last-commit/alrcatraz/astra-vcs-assist)](https://github.com/alrcatraz/astra-vcs-assist/commits)
[![Sponsor](https://img.shields.io/github/sponsors/alrcatraz?label=Sponsor&logo=github&color=ea4aaa&logoColor=white)](https://github.com/sponsors/alrcatraz)

> **Version:** [`VERSION`](VERSION)  · **Branches:** `main` (Gitea, personal) + `public` (GitHub, official)

</div>

---

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
  ├── github/
  │   └── astra-vcs-assist-github     GitHub platform ops
  ├── gitea/
  │   └── astra-vcs-assist-gitea      Gitea platform ops
  ├── gpg/
  │   └── astra-vcs-assist-gpg-key       GPG key lifecycle
  │
  ├── git/
  │   ├── astra-vcs-assist-git-init      Repository bootstrap
  │   ├── astra-vcs-assist-git-dev       Daily development workflow
  │   ├── astra-vcs-assist-git-release   End-of-phase commit cleanup
  │   └── astra-vcs-assist-git-sync      Push, remote, transfer
  │
  └── hg/  (future)
```

## Three-Layer Versioning

This repository supports a versioning scheme for managing local modifications
on top of an upstream baseline, whether you use the skills directly or maintain
a personal fork.

### Two-tier: Agent-only

When you use the upstream skills as-is and only an AI agent applies local
adjustments:

```
Official:  1.0.0                        (upstream baseline)
Agent:     1.0.0+<agent-name>.1         (agent-specific modifications)
```

### Three-tier: with self-hosted fork

When you maintain a personal fork (e.g. on a self-hosted Git instance such as
Gitea) with custom configuration, then clone to individual agent machines:

```
Official:  1.0.0                        (upstream, e.g. GitHub)
Personal:  1.0.0+<owner>.1              (fork with personal config)
Agent:     1.0.0+<owner>.1.<agent>.1    (agent-specific on top of personal)
```

### Rules

- Each layer's version segment increments independently as its content changes
- Use `+` build metadata (SemVer 2.0 §10) to express the inclusion chain — it
  carries documentation but does not affect version comparison
- Version strings go in the `version:` field of each skill's YAML frontmatter
  and in the project root `VERSION` file
- When publishing to a higher (cleaner) layer, strip the lower-layer suffixes

**This instance** (`git01.wrt.astra-lab.org`) uses:

| Layer | Name | Version Example |
|:------|:-----|:----------------|
| Personal | `alrcatraz` (human operator) | `1.0.0+alrcatraz.Z` |
| Agent | Hermes Agent name (e.g. `angelia`) | `1.0.0+alrcatraz.Z.angelia.Z` |

Each segment (`alrcatraz`, agent name) carries a 1–3 digit version (`Z`), incremented independently when that layer's content changes.

## Sub-skills

| Sub-skill | Covers |
|:----------|:-------|
| `astra-vcs-assist-gpg-key` | Check, import, generate GPG keys; configure for VCS signing; headless passphrase caching |
| `astra-vcs-assist-git-init` | README, LICENSE analysis, gitconfig, GPG binding, remote setup, first commit |
| `astra-vcs-assist-git-dev` | Branch, stage, commit, stash during active development |
| `astra-vcs-assist-git-release` | Commit reorganisation, message writing, tagging, changelog |
| `astra-vcs-assist-git-sync` | Dual-remote push, safe force push, git bundle |

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
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-dev \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-dev
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-release \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-release
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-sync \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-sync
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
│   │   ├── astra-vcs-assist-git-dev/
│   │   ├── astra-vcs-assist-git-release/
│   │   └── astra-vcs-assist-git-sync/
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

# astra-vcs-assist（中文版）

> Hermes Agent 的版本控制工作流编排工具集——GPG 密钥生命周期管理、Git 仓库初始化、提交工作流、版本发布和跨机器同步。
> 属于 [Astra 生态](https://github.com/alrcatraz/astra-aiagent-infra) 的一部分。

## 概述

`astra-vcs-assist` 是一个模块化的 Hermes Agent 技能和 CLI 工具集，将完整的版本控制工作流组织为领域特定的子技能：

- **🔑 GPG** — 密钥生命周期管理（检查、导入、生成、轮换）
- **📦 Git** — 仓库初始化、日常开发工作流、发布准备、推送与同步

每个领域在本仓库下拥有独立的子技能树，通过符号链接挂载到 Hermes 的自动发现路径。

## 架构

```
astra-vcs-assist（编排器）
  │
  ├── github/
  │   └── astra-vcs-assist-github     GitHub 平台操作
  ├── gitea/
  │   └── astra-vcs-assist-gitea      Gitea 平台操作
  ├── gpg/
  │   └── astra-vcs-assist-gpg-key       GPG 密钥生命周期
  │
  ├── git/
  │   ├── astra-vcs-assist-git-init      仓库引导
  │   ├── astra-vcs-assist-git-dev       日常开发工作流
  │   ├── astra-vcs-assist-git-release   阶段收尾提交整理
  │   └── astra-vcs-assist-git-sync      推送、远程、传输
  │
  └── hg/  (未来)
```

## 三层版本号

本仓库支持一套版本号方案，用于在上游基线之上管理本地修改——无论你是直接使用上游技能，还是维护个人 fork。

### 两层：仅有 Agent

如果直接使用上游技能，仅由 AI agent 做本地调整：

```
官方版：  1.0.0                        （上游基线）
Agent 版：1.0.0+<agent-name>.1         （agent 特定修改）
```

### 三层：有自托管 fork

如果维护了个人 fork（例如自托管的 Gitea），包含个人配置，再克隆到各个 agent 机器：

```
官方版：  1.0.0                        （上游，如 GitHub）
个人版：  1.0.0+<owner>.1              （fork，含个人配置）
Agent 版：1.0.0+<owner>.1.<agent>.1    （在个人版之上叠加 agent 信息）
```

### 规则

- 各层版本段独立递增
- 使用 `+` build 元数据（SemVer 2.0 §10）表达继承链——不影响版本比较，仅作文档用途
- 版本号记录在每个技能的 YAML frontmatter `version:` 字段和仓库根目录的 `VERSION` 文件
- 向更高（更干净）的层发布时，去掉下层的后缀

本实例（`git01.wrt.astra-lab.org`）的命名规则：

| 层 | 标识符 | 版本号示例 |
|:---|:-------|:-----------|
| 个人版 | `alrcatraz`（人工操作员） | `1.0.0+alrcatraz.Z` |
| Agent 版 | Hermes Agent 名称（如 `angelia`） | `1.0.0+alrcatraz.Z.angelia.Z` |

各段（`alrcatraz`、agent 名称）独立递增其版本号。详见 [`VERSION`](VERSION)。

## 子技能

| 子技能 | 功能 |
|:-------|:-----|
| `astra-vcs-assist-gpg-key` | GPG 密钥检查、导入、生成；VCS 签名配置；免交互密码缓存 |
| `astra-vcs-assist-git-init` | README、LICENSE 分析、gitconfig、GPG 绑定、远程配置、首次提交 |
| `astra-vcs-assist-git-dev` | 开发中的分支、暂存、提交、贮藏管理 |
| `astra-vcs-assist-git-release` | 提交重新组织、消息编写、打标签、变更日志 |
| `astra-vcs-assist-git-sync` | 双远程推送、安全强制推送、git bundle |

## 快速开始

```bash
# Hermes 通过符号链接自动发现这些技能。
# 在对话中显式加载某个子技能：
skill_view(name='astra-vcs-assist-gpg-key')
skill_view(name='astra-vcs-assist-git-init')

# 所有子技能位于 ~/.hermes/skills/vcs/
ls -la ~/.hermes/skills/vcs/
```

## 安装

1. 克隆本仓库：
   ```bash
   git clone https://github.com/alrcatraz/astra-vcs-assist.git \
     ~/Projects/astra/astra-vcs-assist
   ```

2. 符号链接到 Hermes 的发现路径：
   ```bash
   mkdir -p ~/.hermes/skills/vcs
   ln -sfn ~/Projects/astra/astra-vcs-assist \
     ~/.hermes/skills/vcs/astra-vcs-assist
   ln -sfn ~/Projects/astra/astra-vcs-assist/gpg/astra-vcs-assist-gpg-key \
     ~/.hermes/skills/vcs/astra-vcs-assist-gpg-key
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-init \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-init
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-dev \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-dev
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-release \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-release
   ln -sfn ~/Projects/astra/astra-vcs-assist/git/skills/astra-vcs-assist-git-sync \
     ~/.hermes/skills/vcs/astra-vcs-assist-git-sync
   ```

3. Hermes 将在下一轮对话中自动发现新技能。

## 仓库结构

```
astra-vcs-assist/
├── SKILL.md               ← 编排器技能
├── README.md
├── LICENSE                 ← MIT
├── gpg/                    ← GPG（VCS 无关）
│   ├── astra-vcs-assist-gpg-key/SKILL.md
│   └── references/
├── git/                    ← Git 相关
│   ├── skills/             ← 子技能目录
│   │   ├── astra-vcs-assist-git-init/
│   │   ├── astra-vcs-assist-git-dev/
│   │   ├── astra-vcs-assist-git-release/
│   │   └── astra-vcs-assist-git-sync/
│   ├── references/
│   ├── scripts/
│   └── templates/
├── scripts/               ← 通用工具脚本
├── config/
└── templates/
```

## 相关项目

- [astra-aiagent-infra](https://github.com/alrcatraz/astra-aiagent-infra) — Astra 生态门户
- [astra-sre](https://github.com/alrcatraz/astra-sre) — 基础设施可靠性编排

## 许可协议

[MIT](LICENSE) © 2026 alrcatraz
