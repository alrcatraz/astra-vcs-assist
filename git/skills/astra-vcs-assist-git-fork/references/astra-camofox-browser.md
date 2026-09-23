# astra-camofox-browser — Concrete Fork Walkthrough

A complete walkthrough of adapting an upstream fork.

## Context

- Upstream: `jo-inc/camofox-browser` (MIT, v1.11.2)
- Local: `~/Projects/astra/astra-camofox-browser/`
- Branch: `astra`
- Remote: `origin-astra → https://github.com/alrcatraz/astra-camofox-browser.git`
- Mount: remote host via SSHFS → `~/Projects/<host>/`

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

Split into two commits:
- `6abcf32 chore: add copyright for astra fork`
- `920e41b fix: enable VNC and fix dynamic display detection`

### 4. README restructure

Order: astra header → Astra Adaptations (details) → divider → Quick start (our URL) → divider → upstream content

- All badges point at `alrcatraz/astra-camofox-browser`
- Removed the upstream promotional blockquote (kept only the attribution)
- Added a fork notice to AGENTS.md

### 5. Squash

`1a88312` + `19ec11e` → `97842fc` (the add-then-remove intermediate step squashed via `git reset --soft HEAD~2`)

### 6. Push

Pushed straight from the host with `git push origin-astra astra` (interactive TTY, GPG/GCM passphrase prompts succeed there)

### 7. Directory Rename

`camofox-browser` → `astra-camofox-browser` (consistent with other astra projects)

### 8. Release Decision

**Do NOT publish** v1.0.0 — infrastructure adaptation only (VNC, Podman volume, xvfb-run); no substantive new features.

### 9. Sponsors Decision

**Do NOT add** a GitHub Sponsors button — attaching one after minor adaptations to someone else's mature project is inappropriate.

## Final Commit History

```
97842fc docs: mark as astra fork, add adaptations summary
6abcf32 chore: add copyright for astra fork
920e41b fix: enable VNC and fix dynamic display detection
e5cc3d8 chore: astra platform adaptations
```
