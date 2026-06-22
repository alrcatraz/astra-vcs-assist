---
name: astra-vcs-assist-git-init
description: "Git repository bootstrap — project initialisation, README conventions, licence selection and analysis, gitignore strategy, per-repo identity, GPG binding, remote setup, and first commit."
version: 1.0.0
author: alrcatraz
platforms: [linux]
---

# astra-vcs-assist-git-init — Repository Bootstrap

## Trigger Conditions

Load this sub-skill when:

- Initialising a new git repository (`git init` or `git clone`)
- Creating a new project from scratch (needs README, LICENSE, .gitignore)
- Setting up an existing repository with GPG signing and per-repo identity
- Unsure which licence to choose for a new project
- Configuring remote (origin) and credential helpers
- Making the very first commit of a project

## Overview

A well-initialised repository is the foundation of disciplined version control. This sub-skill walks through the full bootstrap:

```text
Plan repo purpose → Pick licence → Write README →
Set up gitconfig → Bind GPG key → Create .gitignore →
Set remote → First commit
```

## 1. Repository Planning

Before touching git, clarify:

| Question | Why it matters |
|:---------|:---------------|
| **What does this project do?** | Drives README structure, licence choice, gitignore patterns |
| **Public or private?** | Public → open-source licence, CI, community standards. Private → simpler |
| **Single developer or team?** | Determines commit convention strictness, PR workflow |
| **Language / framework?** | Gitignore templates, CI config, contribution guide |
| **Primary author identity?** | Which GPG key, which git user.name/email |

## 2. Licence Selection

Licence selection is a **three-step workflow**:

```
Analyse project context  →  Recommend licence  →  User decides  →  Execute
   │                             │                      │
   └── Check Fact Store /        └── Present 1–2        └── User confirms
       memory for preferences        candidates with        → Ready to
       & the existing                  rationale               implement
       project pattern
```

### Step 1 — Analyse

Before recommending, check:

1. **Fact Store** (`fact_store(action='search', query='license')`) — any stored
   preference about licences the user has stated before
2. **Project purpose** — is it code? Documentation? Tutorial? Mixed?
3. **Existing ecosystem pattern** — do the user's other similar projects use
   a consistent licence?
4. **Public or private?** — public projects need explicit licence; private can
   be "All rights reserved"

### Step 2 — Recommend

Present 1–2 candidates with rationale. Reference the matrix below for
comparison. Let the user decide before touching any file.

### Decision matrix (for reference during analysis)

| Want this? | Choose this | Notes |
|:-----------|:------------|:------|
| Maximum adoption, permissive | **MIT** | Short, simple, lets anyone do anything. Industry standard for tools and libraries |
| Share alike, copyleft | **GPL-3.0** | Derivative works must also be GPL. Use for projects where you want to enforce openness |
| Weak copyleft (libraries) | **LGPL-3.0** | Can be linked from proprietary code without forcing GPL on the whole program |
| Patents protection | **Apache-2.0** | Like MIT but with an express patent grant. Used by Google, Android, Kubernetes |
| Documentation only | **CC BY-SA 4.0** | Creative Commons for docs. Note: GitHub recognises `CC-BY-SA-4.0` only if the LICENSE file is the standard text (no preamble) |
| Dual licence | **MIT + CC BY-SA 4.0** | Code under MIT, documentation under CC BY-SA. Common for tutorial projects. Keep in `LICENSE` + `LICENSE.DUAL.md` |
| No licence | **All rights reserved** | Default. Others cannot copy, modify, or distribute. Deliberate choice for private projects |

### Practical steps

```bash
# 1. Choose your licence
# MIT (simplest):
curl -sL https://raw.githubusercontent.com/licenses/license-templates/master/templates/mit.txt \
  -o LICENSE

# CC BY-SA 4.0 (docs):
curl -sL https://raw.githubusercontent.com/samuel-phan/CC-Licenses/master/CC-BY-SA-4.0.md \
  -o LICENSE

# 2. For dual-licence projects, create a companion file
cat > LICENSE.DUAL.md << 'EOF'
# Licence Notice

This project is dual-licensed:

- **Code** is licensed under the MIT License (see `LICENSE`).
- **Documentation** is licensed under CC BY-SA 4.0.
EOF
```

### Licence verification

After adding the licence file, verify GitHub's detection:

```bash
# Push to GitHub first, then check
curl -s https://api.github.com/repos/<owner>/<repo>/license \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('license',{}).get('spdx_id','NOT DETECTED'))"
```

Expected: `MIT`, `CC-BY-SA-4.0`, `Apache-2.0`, etc. If `NOASSERTION`, the licence file may have extra text before the standard template.

## 3. README

### Badge bar (classic four)

The README header should carry these four badges — they're the first thing
visitors see and communicate project health at a glance:

```markdown
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/owner/repo)](https://github.com/owner/repo)
[![GitHub last commit](https://img.shields.io/github/last-commit/owner/repo)](https://github.com/owner/repo)
[![Star history](https://api.star-history.com/svg?repos=owner/repo&type=Date)](https://star-history.com/#owner/repo&Date)
```

| Badge | Service | Meaning |
|:------|:--------|:--------|
| License | `shields.io` | Licence type, colour-coded |
| Stars | `shields.io` | Popularity indicator |
| Last commit | `shields.io` | Active maintenance signal |
| Star history | `star-history.com` | Growth trend over time |

Replace `owner/repo` with the actual GitHub repository path.

### Sponsor badge (conditional)

Search Fact Store for sponsor information:

```
fact_store(action='search', query='sponsor OR funding OR donate')
```

- **Result found** → ask the user: "Should I include a sponsor badge?"
- **No result** → skip. Do not fabricate or prompt about it.

If the user confirms a sponsor link, add it to the badge bar:

```markdown
[![Sponsor](https://img.shields.io/badge/sponsor-❤️-red.svg)](<sponsor-url>)
```

### Standard sections

After the badge bar, the README body follows a conventional structure:

#### README template

````markdown
## Description

A paragraph explaining the project's purpose, audience, and key differentiators.

## Quick Start

```bash
# Installation and first-use commands
```

## Usage

Brief examples or a link to full documentation.

## Development

How to set up a development environment, run tests, build.

## Contributing

Link to CONTRIBUTING.md or brief guidelines.

## Licence

[Licence name] — see [LICENCE](LICENSE).
````

#### Bilingual README (for international projects)

Use a `README.md` with main content in one language and a summary in another at the bottom:

```markdown
# Project Name

[English content above]

---

_🇨🇳 中文摘要：这是一个……项目。详见 [docs/zh/](docs/zh/)。_
```

## 4. Per-Repository Git Configuration

### Essential settings

```bash
cd /path/to/repo

git config user.name "Your Name"              # or GitHub username
git config user.email "your.email@example.com" # must match GPG key and GitHub email

git config user.signingkey <key-id>            # from gpg --list-secret-keys
git config commit.gpgsign true
git config tag.gpgsign true

git config pull.ff only                        # prefer fast-forward only
git config push.autoSetupRemote true           # auto-set upstream on first push
git config push.default current                # push current branch to matching remote
```

### Global fallbacks (only for single-identity setups)

```bash
git config --global user.name "..."
git config --global user.email "..."
```

### Credential helper

```bash
# Option A: Git Credential Manager (GCM) — cross-platform UI
git config credential.helper "manager"         # Windows/macOS
git config credential.helper "manager-core"    # Linux with GCM

# Option B: pass (Linux, password-store)
git config credential.helper "store --file ~/.git-credentials"  # simple, plaintext ⚠️
git config credential.helper "!f() { cat ~/.git-credentials; }; f"  # custom

# Option C: GPG + pass on Linux (recommended for headless)
git config credential.helper "!/path/to/git-credential-pass.sh"

# Set default GitHub username (avoids GCM account picker)
git config credential.https://github.com.username <username>
```

## 5. GPG Key Binding

Ensure the GPG key selected matches the git identity:

```bash
# Verify match
echo "GPG email:"
gpg --list-key $(git config user.signingkey) --keyid-format LONG | grep uid
echo "Git email:"
git config user.email

# They MUST match — otherwise GitHub shows "Unverified" on commits
```

## 6. .gitignore

### Language-specific

```bash
# Fetch from GitHub's official templates
curl -sL https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore \
  -o .gitignore
```

Add project-specific entries at the bottom:

```gitignore
# IDE
.idea/
.vscode/
*.swp

# Build output
dist/
build/
*.egg-info/

# Environment
.env
.venv/
```

### Global gitignore (for all repos)

```bash
git config --global core.excludesFile ~/.gitignore_global
cat >> ~/.gitignore_global << 'EOF'
.DS_Store
Thumbs.db
*.log
EOF
```

## 7. Remote Configuration

### Standard setup (single remote)

```bash
git remote add origin https://github.com/owner/repo.git
git branch -M main
git push -u origin main
```

### Dual remote (mirror)

```bash
git remote add origin https://github.com/owner/repo.git
git remote add mirror https://git.example.com/owner/repo.git
git push -u origin main
git push -u mirror main
```

See `astra-vcs-assist-git-sync` for dual-remote push workflow.

## 8. First Commit

```bash
git add .
git commit -S -m "chore: initial project bootstrap

Set up project skeleton with README, LICENSE, gitignore, and
basic git configuration."

# Push (single remote)
git push -u origin main
```

### First commit conventions

| Type | When to use |
|:-----|:------------|
| `chore: initial project bootstrap` | Standard first commit — initial files, no working code yet |
| `feat: initial project scaffold` | If the first commit already includes runnable code |
| `docs: initial documentation` | Documentation-only projects |

## Pitfalls

1. **LICENSE file must be standard text.** GitHub detects licences by matching the exact text. Even a single line of preamble (e.g. "This project uses the MIT licence") causes `NOASSERTION`. Put explanatory notes in `LICENSE.DUAL.md`.

2. **GPG email mismatch.** The email in the GPG key's `uid` must match `git config user.email` exactly. GitHub verifies commits against the email on the GPG key.

3. **`user.signingkey` without `commit.gpgsign true`.** Many users forget the second config. Without it, `git commit` doesn't auto-sign — you have to remember `-S` every time.

4. **First push without `push.autoSetupRemote true`.** Without this setting, `git push` on a new branch fails with "no upstream configured". Either set it or always use `git push -u origin HEAD`.

5. **Credential helper order matters.** Multiple credential helpers run in sequence. If GCM is listed first, it may prompt interactively before falling through to your script. Order them: custom script first, then GCM as fallback.

6. **`pull.ff only` prevents merge commits.** This avoids accidental merge bubbles during `git pull`. Use `git pull --rebase` when you intentionally need to rebase.

7. **Global vs per-repo identity.** If you work on multiple projects (personal, work, OSS), use per-repo config, never global identity. Global `user.name`/`user.email` is a common source of misattributed commits.
