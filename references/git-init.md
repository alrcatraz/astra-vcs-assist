# astra-vcs-assist-git-init — Repository Bootstrap

*This reference was migrated from the `astra-vcs-assist-git-init` sub-skill.*

## Trigger Conditions

- Initialising a new git repository (`git init` or `git clone`)
- Creating a new project from scratch (needs README, LICENSE, .gitignore)
- Setting up GPG signing and per-repo identity
- Unsure which licence to choose
- Configuring remote and credential helpers
- Making the very first commit

## Overview

```
Plan repo purpose → Pick licence → Write README →
Set up gitconfig → Bind GPG key → Create .gitignore →
Set remote → First commit
```

## 1. Repository Planning

| Question | Why it matters |
|:---------|:---------------|
| Public or private? | Public → open-source licence, CI |
| Single developer or team? | Commit convention strictness |
| Language / framework? | Gitignore, CI config |
| Primary author identity? | Which GPG key, which git identity |

## 2. Licence Selection

Three-step workflow: **Analyse → Recommend → Execute**.

### Decision matrix

| Want this? | Choose | Notes |
|:-----------|:-------|:------|
| Maximum adoption, permissive | **MIT** | Industry standard |
| Share alike, copyleft | **GPL-3.0** | Derivative works must be GPL |
| Weak copyleft (libraries) | **LGPL-3.0** | Can link from proprietary code |
| Patents protection | **Apache-2.0** | Express patent grant |
| Documentation only | **CC BY-SA 4.0** | Creative Commons for docs |
| No licence | All rights reserved | Private projects |

### Practical steps

```bash
curl -sL https://raw.githubusercontent.com/licenses/license-templates/master/templates/mit.txt -o LICENSE
```

### Verification

```bash
# After push to GitHub
curl -s https://api.github.com/repos/<owner>/<repo>/license | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('license',{}).get('spdx_id','NOT DETECTED'))"
```

## 3. README

### Badge bar

```markdown
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/owner/repo)](https://github.com/owner/repo)
[![GitHub last commit](https://img.shields.io/github/last-commit/owner/repo)](https://github.com/owner/repo)
[![Star history](https://api.star-history.com/svg?repos=owner/repo&type=Date)](https://star-history.com/#owner/repo&Date)
```

### Standard README sections

Description → Quick Start → Usage → Development → Contributing → Licence

## 4. Per-Repository Git Configuration

```bash
cd /path/to/repo
git config user.name "Your Name"
git config user.email "your.email@example.com"
git config user.signingkey <key-id>
git config commit.gpgsign true
git config tag.gpgsign true
git config pull.ff only
git config push.autoSetupRemote true
git config push.default current
```

### Credential helper

```bash
# GPG + pass (recommended for headless)
git config credential.helper "!/path/to/git-credential-pass.sh"
# Or SSH:
git remote set-url origin git@github.com:owner/repo.git
```

## 5. .gitignore

```bash
curl -sL https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore -o .gitignore
```

Add project-specific entries at bottom (`.env`, `.venv/`, IDE files).

## 6. Remote Configuration

```bash
git remote add origin https://github.com/owner/repo.git
git branch -M main
git push -u origin main
```

## 7. First Commit

```bash
git add .
git commit -S -m "chore: initial project bootstrap"
git push -u origin main
```

## Pitfalls

1. **LICENSE file must be standard text** — no preamble.
2. **GPG email must match `git config user.email`** exactly.
3. **`user.signingkey` without `commit.gpgsign true`** — commits won't auto-sign.
4. **Global vs per-repo identity** — use per-repo, never global for multi-identity setups.
