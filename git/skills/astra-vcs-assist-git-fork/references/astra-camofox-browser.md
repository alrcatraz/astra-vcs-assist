# astra-camofox-browser — Concrete Fork Walkthrough

完整的上游 fork 适配流程记录。

## Context

- 上游: `jo-inc/camofox-browser` (MIT, v1.11.2)
- 本地: `HomeCentre01 ~/Projects/astra/astra-camofox-browser/`
- 分支: `astra`
- 远程: `origin-astra → https://github.com/alrcatraz/astra-camofox-browser.git`
- 挂载: SUSET01 SSHFS → `~/Projects/homecentre01/`

## Steps Taken

### 1. Git Status Check

- Remote: `origin` (upstream) + `origin-astra` (our fork, not yet created on GitHub)
- Branch: `astra` based on upstream `master`
- 3 modified files: Dockerfile, camofox.config.json, vnc-watcher.sh

### 2. LICENSE Update

```diff
 Copyright (c) 2025 Jo, Inc
+Copyright (c) 2026 alrcatraz
```

### 3. Commit Splitting

分开两个 commit：
- `6abcf32 chore: add copyright for astra fork`
- `920e41b fix: enable VNC and fix dynamic display detection`

### 4. README restructure

顺序：astra header → Astra Adaptations (details) → divider → Quick start (our URL) → divider → upstream content

- Badges 全部指向 `alrcatraz/astra-camofox-browser`
- 删除了上游 Jo promotional blockquote（只保留 attribution）
- AGENTS.md 加了 fork notice

### 5. Squash

`1a88312` + `19ec11e` → `97842fc` (用 `git reset --soft HEAD~2` squash 了「先加后删」的中间步骤)

### 6. Push

在 HomeCentre01 上直接 `git push origin-astra astra`（有 TTY 的终端，GPG/GCM 交互式弹密码成功）

### 7. Directory Rename

`camofox-browser` → `astra-camofox-browser`（和其他 astra 项目统一）

### 8. Release Decision

**不发** v1.0.0。理由：只有基础设施适配（VNC、Podman volume、xvfb-run），没有实质新功能。

### 9. Sponsors Decision

**不加** GitHub Sponsors。理由：在别人的成熟项目上做少量适配就挂赞助链接不合适。

## Final Commit History

```
97842fc docs: mark as astra fork, add adaptations summary
6abcf32 chore: add copyright for astra fork
920e41b fix: enable VNC and fix dynamic display detection
e5cc3d8 chore: astra platform adaptations
```
