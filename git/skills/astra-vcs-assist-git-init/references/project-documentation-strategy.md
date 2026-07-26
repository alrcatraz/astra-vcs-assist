# Project Documentation Strategy

> Reference for `astra-vcs-assist-git-init` section 8.
> Updated 2026-07-25 — added README vs Wiki distinction.

Decide what documentation approach fits a project **before** the first
commit. This document covers the decision framework and setup instructions
for each approach.

---

## Core Principle

**README is mandatory. Everything else is optional.**

Every project must have a `README.md`. Wiki, MkDocs, and `docs/` folders
are additional layers for when the README can't (or shouldn't) cover
everything.

---

## README vs Wiki — When to Use What

### README is the front door

The README is the first thing visitors see. It should be **concise and
scannable** — answer three questions: what is this, why should I care,
how do I start.

**What belongs in README:**

| Element | Required? | Length |
|:--------|:---------:|:-------|
| Title + one-liner | ✅ Always | 1 line |
| Badge bar (license, stars, last commit) | ✅ Always | 3-4 lines |
| Quick start (install + hello world) | ✅ Always | 3-5 lines |
| Basic usage example | ✅ Always | 5-10 lines |
| Link to Wiki/MkDocs for full docs | If Wiki exists | 1 line |
| Full configuration reference | ❌ No → belongs in Wiki | — |
| Full API reference | ❌ No → belongs in Wiki | — |
| Troubleshooting guide | ❌ No → belongs in Wiki | — |
| Architecture deep dive | ❌ No → belongs in Wiki | — |

### Wiki is the reference library

The GitHub/Gitea Wiki is a **multi-page documentation space** for projects
where README isn't enough. It lives as a separate git repo alongside the
code repo.

**What belongs in Wiki:**

| Page | Content |
|:-----|:--------|
| **Home** | Project overview, table of contents |
| **Installation** | Full setup guide, prerequisites, dependencies, platform notes |
| **Configuration** | All config options, env vars, examples, defaults |
| **Usage** | Detailed examples, common patterns, advanced usage |
| **Architecture** | How it works, code map, design decisions |
| **API Reference** | Endpoints, functions, parameters, return values |
| **Troubleshooting** | Common issues, error messages, fixes |
| **FAQ** | Frequently asked questions |
| **Contributing** | How to contribute, coding standards, PR workflow |

### When to add a Wiki

A Wiki is worth adding when ALL of these are true:

1. ✅ It's a **code / tool / library** project (not a tutorial, not creative writing)
2. ✅ The README **cannot reasonably fit** all the documentation
3. ✅ The project has **users who need reference docs** beyond the README

### When NOT to add a Wiki

| Project type | Use instead | Why |
|:-------------|:------------|:----|
| Tutorial / guide | MkDocs Material | Wiki has no navigation tree, no search, no versioning |
| Creative writing / worldbuilding | Obsidian + MkDocs | Wiki has no cross-link graph, no asset management |
| Simple one-pager tool | README only | Wiki is overkill |
| Meta-repo / portal | README + docs/ folder | Wiki would duplicate what's in docs/ |
| API library with docstrings | MkDocs + mkdocstrings | Auto-generated from code, Wiki would need manual sync |

---

## Decision Tree

```
1. Does this project have a README.md yet?
   └─ No → Write one. This is not optional.

2. Does the README cover everything the user needs?
   ├─ Yes → Stop here. Close the Wiki feature if enabled.
   ├─ "Mostly, but needs a few reference pages"
   │  └─ → Consider docs/ folder (versioned with code)
   └─ No → Continue to step 3.

3. What type of project is this?
   ├─ Code / tool / library
   │  ├─ Needs detailed reference docs?
   │  │  ├─ Yes → Enable GitHub/Gitea Wiki
   │  │  │         → Keep README concise, link to Wiki
   │  │  │         → Write at minimum: Home, Installation, Configuration
   │  │  └─ No → README + inline comments is enough
   │  └─ Has auto-documented API? → also consider MkDocs + mkdocstrings
   ├─ Tutorial / guide
   │  └─ → MkDocs Material (standalone site)
   ├─ Creative writing / worldbuilding
   │  └─ → Obsidian vault (authoring) + MkDocs (publishing)
   └─ Simple / one-pager
      └─ → README-only is fine
```

---

## Approach Matrix

| Approach | Best for | Effort | README needed? |
|:---------|:---------|:-------|:---------------|
| **README only** | Simple tools, cheatsheets, small scripts | Low | ✅ Mandatory |
| **README + GitHub/Gitea Wiki** | Code/tool projects needing detailed docs | Medium | ✅ Mandatory |
| **README + MkDocs Material** | Tutorials, multi-page guides | Medium-High | ✅ Mandatory |
| **README + Obsidian + MkDocs** | Creative writing, worldbuilding | High | ✅ Mandatory |
| **README + MkDocs + mkdocstrings** | API / library reference | Medium | ✅ Mandatory |

---

## Approach 1: README Only

No additional setup needed. All documentation fits in `README.md`.

**Good for:** scripts, single-purpose tools, personal notes, projects where
the README genuinely covers everything.

```bash
# If the README is getting long, consider docs/ or Wiki instead
# One-pager: keep in README.md with ## subsections
# Slightly longer: add a single docs/ page
mkdir docs/
touch docs/usage.md
```

---

## Approach 2: README + GitHub/Gitea Wiki

**README** is the concise entry point. **Wiki** is the reference library.

### GitHub Wiki

```bash
# Check if wiki is enabled for the repo
gh api repos/:owner/:repo --jq '.has_wiki'

# If false, enable it:
gh api repos/:owner/:repo -X PATCH -f has_wiki=true

# Clone the wiki repo to populate it
git clone https://github.com/:owner/:repo.wiki.git
cd repo.wiki
```

**Minimum wiki pages to start with:**

```markdown
# Home.md
## Overview
[2-3 sentence project description]

## Quick Links
- [Installation](Installation)
- [Configuration](Configuration)
- [Usage](Usage)

## Support
- [FAQ](FAQ)
- [Troubleshooting](Troubleshooting)
```

```markdown
# Installation.md
## Prerequisites
- Dependency A (version X+)
- Dependency B

## Setup
```bash
# Commands here
```

## Verification
```bash
# Test command here
```
```

```markdown
# Configuration.md
| Variable | Default | Description |
|----------|---------|-------------|
| `VAR_NAME` | `default` | What it does |
```

**Limitations:**
- No custom theming (GitHub wiki uses lightweight markup)
- No cross-repo search
- Sidebar and footer via `_Sidebar.md` and `_Footer.md`
- No multi-language / versioned docs

### Gitea Wiki

```bash
git clone https://git.example.com/:owner/:repo.git/wiki
cd wiki
```

Gitea wiki supports Markdown, ReStructuredText, and AsciiDoc.
Same page structure as GitHub Wiki above.

---

## Approach 3: README + MkDocs Material (Standalone Site)

Best for multi-page tutorials and documentation sites where navigation
and search matter.

### Quick setup

```bash
# Create docs directory
mkdir docs/
cat > docs/index.md << 'EOF'
# Project Name

Documentation site.
EOF

# Create mkdocs.yml
cat > mkdocs.yml << 'EOF'
site_name: Project Name
theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - search.highlight
EOF

# Build
uv tool install mkdocs-material
mkdocs build
```

### LLM Wiki pattern (for tutorials)

For tutorial content that feeds into the Astra Knowledge Base:

```
docs/
├── index.md              # Home page
├── entities/             # One file per entity/concept
│   ├── intro.md
│   └── setup.md
├── references/           # External links, further reading
└── assets/               # Images, diagrams
```

### MkDocs + mike (versioned docs)

```bash
uv tool install mike
mike deploy --push --update-aliases 1.0 latest
mike set-default --push latest
```

See `mkdocs-documentation` skill for full setup details.

---

## Approach 4: README + Obsidian Vault + MkDocs Export

For creative writing and worldbuilding projects. Author in Obsidian,
publish via MkDocs. README links to the published site.

### Structure

```
Novels/<世界观名称>/
├── wiki/                   # Obsidian vault (source)
│   ├── .obsidian/
│   ├── entities/
│   ├── references/
│   └── assets/
├── publish/                # MkDocs site (generated)
│   ├── docs/
│   ├── mkdocs.yml
│   └── gen-mkdocs.py       # Conversion script
└── README.md               # Points to the published site
```

### Key rules (from existing convention)

- Wiki frontmatter uses English keys, documents in project language
- MkDocs / PDF output is 100% content language
- `gen-mkdocs.py` copies wiki, strips frontmatter, converts `[[wikilinks]]`
  to relative markdown links with cross-directory resolution
- PDF via Pandoc + lualatex + Noto font

See `knowledge-base-interop` skill for the full export workflow.

---

## Approach 5: README + MkDocs + mkdocstrings (API Reference)

For libraries and MCP servers. Document source code with docstrings,
auto-generate the API reference site.

```bash
# Install
uv tool install mkdocs-material
pip install mkdocstrings[python]

# mkdocs.yml
cat >> mkdocs.yml << 'EOF'
plugins:
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
EOF
```

Then in docs pages reference source code directly:

```markdown
::: my_module.MyClass
    handler: python
```

---

## Verification

| Approach | What to verify |
|:---------|:---------------|
| README only | `cat README.md | head -5` — renders correctly, concise |
| README + Wiki | Wiki Home page exists, not empty. README links to Wiki |
| README + MkDocs | `mkdocs build --strict` — exits 0 |
| README + MkDocs + mike | `mike list` — versions listed |
| README + Obsidian + MkDocs | `gen-mkdocs.py && mkdocs build --strict` |
| README + mkdocstrings | `mkdocs build 2>&1 | grep -i "No module"` — no import errors |

**Wiki content check:**

```bash
# Check wiki has actual content (not just enabled-but-empty)
gh api "repos/:owner/:repo/contents/Home.md?ref=wiki" 2>&1 | grep -q '"sha":' \
  && echo "✅ Wiki has content" \
  || echo "❌ Wiki is empty"
```

---

## Pitfalls

1. **README-as-Wiki anti-pattern** — Don't dump everything into README.
   If README exceeds ~200 lines and has deep subsections (### #### #####),
   the content should be in a Wiki or MkDocs site instead. README should
   be scannable in 30 seconds.

2. **Wiki-as-sole-docs anti-pattern** — Don't rely on Wiki alone. Wikis
   can be disabled, the wiki repo can be deleted, and first-time visitors
   land on the README first. Always link from README to Wiki.

3. **GitHub Wiki can't be disabled for org repos** — Some org settings
   force wikis on or off regardless of per-repo settings.

4. **Gitea Wiki requires repo admin** — Only repo owners/admins can enable
   the wiki feature in repo settings.

5. **MkDocs site != repo wiki** — A MkDocs site is a separate build output
   (usually in `site/` or published to GitHub Pages). It is NOT the same
   as GitHub's built-in wiki.

6. **Obsidian vault path matters** — The `gen-mkdocs.py` script relies on
   the vault being under `<project>/wiki/`. Moving it breaks relative
   wikilink resolution.

7. **Wiki enabled but empty is worse than Wiki disabled** — An empty Wiki
   (has_wiki=true but no pages) looks abandoned. If you enable the Wiki
   feature, write at least the Home page. If you don't plan to use it,
   disable the feature.
