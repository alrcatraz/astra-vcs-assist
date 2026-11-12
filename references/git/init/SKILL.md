---
name: astra-vcs-assist-git-init
description: "Git repository bootstrap — project initialisation, README conventions, licence selection and analysis, gitignore strategy, per-repo identity, GPG binding, remote setup, documentation strategy, and first commit."
version: 1.4.3
author: <owner>
triggers:
  - "新建仓库"
  - "初始化仓库"
  - "git init"
  - "项目脚手架"
  - "README 规范"
  - ".gitignore"
platforms: [linux]
metadata:
  hermes:
    tags: [git, bootstrap, project-initialisation, readme, gitignore]

---

# `references/git/init` — Repository Bootstrap

## Trigger Conditions

Load this sub-skill when:

- Initialising a new git repository (`git init` or `git clone`)
- Creating a new project from scratch (needs README, LICENSE, .gitignore)
- Setting up an existing repository with GPG signing and per-repo identity
- Unsure which licence to choose for a new project
- Configuring remote (origin) and credential helpers
- Making the very first commit of a project
- Need to decide what documentation approach fits the project type

## Overview

A well-initialised repository is the foundation of disciplined version control. This sub-skill walks through the full bootstrap:

```text
Plan repo purpose → Pick licence → Write README →
Set up gitconfig → Bind GPG key → Create .gitignore →
Set remote → Determine documentation strategy →
First commit
```

## Where each subject lives

| Subject | File |
|:--|:--|
| Repository planning and licence selection | `planning-and-licence.md` |
| README and the documentation strategy, with both templates | `readme-and-docs.md` |
| Per-repo git configuration, GPG binding, ignore rules, remotes | `repo-config-and-signing.md` |
| The first commit and what it must contain | `first-commit.md` |
| Failure modes at initialisation | `pitfalls.md` |

`references/INDEX.md` registers the case files under `references/`.
