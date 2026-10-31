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

- **🔑 GPG** — key lifecycle (VCS-agnostic pillar)
- **📦 Git** — init, daily workflow, review, release, sync, remote auth
- **🐙 GitHub / 🏭 Forge** — platform operations, PAT lifecycle, dependabot, issue→PR
- **🕰 History / 🏷 Versioning** — published-history rewriting, layer scheme + release line

Each domain has its own sub-skill tree under this repository, symlinked into
Hermes' discovery path for automatic loading.

## Architecture

One registered skill: the root `SKILL.md` routes, everything else is a block under
`references/<pillar>/<block>/`.

```text
astra-vcs-assist (macro skill)
├── SKILL.md                       router (no procedures)
├── routing.yaml                   machine-readable routing (name + block path)
├── scripts/scan-tracked-values.py whole-tree value scanner (pre-push gate)
└── references/
    ├── INDEX.md                   pillar registry
    ├── gpg/key-lifecycle/         GPG key lifecycle (VCS-agnostic)
    ├── git/{init,dev,fork,review,release,sync,remote-auth}/
    ├── github/{platform,pat,dependabot,issue-to-pr}/
    ├── forge/platform/            self-hosted Gitea/Forgejo (allowlisted pillar)
    ├── history/signing/           published-history rewriting
    ├── versioning/layers/         layer scheme + dual-branch release
    └── tower-model.md · branch-protection-model.md · trust-level-verification.md
        prose-artefact-layer-attribution.md · fleet-naming.md · skill-edit-sync.md
```

Load a block by path — blocks are not registered skills:

```
skill_view(name='astra-vcs-assist', file_path='references/git/dev/SKILL.md')
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

**This instance** (`your-forge.example.com`) uses:

| Layer | Name | Version Example |
|:------|:-----|:----------------|
| Personal | `<owner>` (human operator) | `1.3.0` |
| Agent | Hermes Agent name (e.g. `angelia`) | `1.3.0.angelia.0.0.0` |

Each segment (`<owner>`, agent name) carries a 1–3 digit version (`Z`), incremented independently when that layer's content changes.

## Sub-skills

| Sub-skill | Covers |
|:----------|:-------|
| `astra-vcs-assist` → `references/gpg/key-lifecycle/` | Check, import, generate GPG keys; configure for VCS signing; headless passphrase caching |
| `astra-vcs-assist` → `references/git/init/` | README, LICENSE analysis, gitconfig, GPG binding, remote setup, first commit |
| `astra-vcs-assist` → `references/git/dev/` | Branch, stage, commit, stash during active development |
| `astra-vcs-assist` → `references/git/release/` | Commit reorganisation, message writing, tagging, changelog |
| `astra-vcs-assist` → `references/git/sync/` | Dual-remote push, safe force push, git bundle |

## Quick Start

```bash
# Hermes auto-discovers these skills via symlinks.
# To load a sub-skill explicitly in a conversation:
skill_view(name='astra-vcs-assist', file_path='references/gpg/key-lifecycle/SKILL.md')
skill_view(name='astra-vcs-assist', file_path='references/git/init/SKILL.md')

# All sub-skills are in ~/.hermes/skills/vcs/
ls -la ~/.hermes/skills/vcs/
```

## Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/alrcatraz/astra-vcs-assist.git \
     ~/Projects/astra/astra-vcs-assist
   ```

2. Symlink into Hermes' discovery path — **the repo root only**:
   ```bash
   mkdir -p ~/.hermes/skills/vcs
   ln -sfn ~/Projects/astra/astra-vcs-assist \
     ~/.hermes/skills/vcs/astra-vcs-assist
   ```
   Sub-skills are discovered through this one link (each lives in its own
   topic directory inside the repo). **Do not create per-member links** —
   a second path to the same `SKILL.md` registers the same name twice and
   the loader refuses to guess. On a machine that keeps a separate
   production copy, link that copy instead of the development checkout.
   ```bash
   # Verify: every sub-skill reachable, and no stale per-member links
   for d in gpg/*/ git/skills/*/ github/*/ versioning/*/ gitea-forgejo/*/; do
     [ -f "$HOME/.hermes/skills/vcs/astra-vcs-assist/$d/SKILL.md" ] \
       || echo "MISSING: $d"; done
   ls -d ~/.hermes/skills/vcs/astra-vcs-assist-* 2>/dev/null \
     && echo "REMOVE these duplicate bridges"
   ```

3. Hermes will auto-discover the new skills on the next turn.

## Repository Structure

```
astra-vcs-assist/
├── SKILL.md               ← Hub orchestrator
├── README.md
├── LICENSE                 ← MIT
├── gpg/                    ← GPG (VCS-agnostic)
│   ├── gpg/key-lifecycle/SKILL.md
│   └── references/
├── git/                    ← Git-specific
│   ├── skills/             ← Sub-skills stored here
│   │   ├── git/init/
│   │   ├── git/dev/
│   │   ├── git/release/
│   │   └── git/sync/
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

- **🔑 GPG** — key lifecycle (VCS-agnostic pillar)
- **📦 Git** — init, daily workflow, review, release, sync, remote auth
- **🐙 GitHub / 🏭 Forge** — platform operations, PAT lifecycle, dependabot, issue→PR
- **🕰 History / 🏷 Versioning** — published-history rewriting, layer scheme + release line

每个领域在本仓库下拥有独立的子技能树，通过符号链接挂载到 Hermes 的自动发现路径。

## 架构

```
astra-vcs-assist（编排器）
  │
  ├── github/
  │   └── github/platform           GitHub 平台操作
  ├── gitea-forgejo/
  │   └── forge/platform            Gitea/Forgejo 平台操作（仅私有）
  ├── gpg/
  │   └── gpg/key-lifecycle         GPG 密钥生命周期
  │
  ├── git/
  │   ├── astra-vcs-assist-git-init      仓库引导
  │   ├── git/dev                   日常开发工作流
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

本实例（`your-forge.example.com`）的命名规则：

| 层 | 标识符 | 版本号示例 |
|:---|:-------|:-----------|
| 个人版 | `<owner>`（人工操作员） | `1.3.0` |
| Agent 版 | Hermes Agent 名称（如 `angelia`） | `1.3.0.angelia.0.0.0` |

各段（`<owner>`、agent 名称）独立递增其版本号。详见 [`VERSION`](VERSION)。

## 子技能

| 子技能 | 功能 |
|:-------|:-----|
| `astra-vcs-assist` → `references/gpg/key-lifecycle/` | GPG 密钥检查、导入、生成；VCS 签名配置；免交互密码缓存 |
| `astra-vcs-assist` → `references/git/init/` | README、LICENSE 分析、gitconfig、GPG 绑定、远程配置、首次提交 |
| `astra-vcs-assist` → `references/git/dev/` | 开发中的分支、暂存、提交、贮藏管理 |
| `astra-vcs-assist` → `references/git/release/` | 提交重新组织、消息编写、打标签、变更日志 |
| `astra-vcs-assist` → `references/git/sync/` | 双远程推送、安全强制推送、git bundle |

## 快速开始

```bash
# Hermes 通过符号链接自动发现这些技能。
# 在对话中显式加载某个子技能：
skill_view(name='astra-vcs-assist', file_path='references/gpg/key-lifecycle/SKILL.md')
skill_view(name='astra-vcs-assist', file_path='references/git/init/SKILL.md')

# 所有子技能位于 ~/.hermes/skills/vcs/
ls -la ~/.hermes/skills/vcs/
```

## 安装

1. 克隆本仓库：
   ```bash
   git clone https://github.com/alrcatraz/astra-vcs-assist.git \
     ~/Projects/astra/astra-vcs-assist
   ```

2. 符号链接到 Hermes 的发现路径 —— **只链仓库根**：
   ```bash
   mkdir -p ~/.hermes/skills/vcs
   ln -sfn ~/Projects/astra/astra-vcs-assist \
     ~/.hermes/skills/vcs/astra-vcs-assist
   ```
   子技能全部经这一个链接被发现（各自位于仓库内的主题目录）。**不要为子技能单独建链接** ——
   同一份 `SKILL.md` 出现两条发现路径会让同名技能重复注册，加载器会拒绝猜测。
   若本机另存生产副本，请链接生产副本而非开发检出。

3. Hermes 将在下一轮对话中自动发现新技能。

## 仓库结构

```
astra-vcs-assist/
├── SKILL.md               ← 编排器技能
├── README.md
├── LICENSE                 ← MIT
├── gpg/                    ← GPG（VCS 无关）
│   ├── gpg/key-lifecycle/SKILL.md
│   └── references/
├── git/                    ← Git 相关
│   ├── skills/             ← 子技能目录
│   │   ├── git/init/
│   │   ├── git/dev/
│   │   ├── git/release/
│   │   └── git/sync/
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
