# README and the documentation strategy, with both templates

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

_🇨🇳 Chinese summary placeholder — keep this line only if the repo ships a zh README section; otherwise drop._
```
## 8. Determine Documentation Strategy

### First principle: README is mandatory, everything else is optional

**Every project must have a `README.md`** — it's the front page, the first
thing visitors see. The README should be concise and scannable: what the
project is, quick start, badges, and pointers to detailed docs.

GitHub Wiki, MkDocs, and `docs/` folders are **additional layers** for when
the README can't (or shouldn't) cover everything.

### README vs Wiki vs MkDocs — what each is for

| Layer | Purpose | Content | When to use |
|:------|:--------|:--------|:------------|
| **README.md** | Front door, first impression | What/Why, quick start, badges, links | **Every project — mandatory** |
| **GitHub/Gitea Wiki** | Reference library, detailed docs | Install guide, config reference, API, FAQ, troubleshooting | Code/tool projects where README isn't enough |
| **MkDocs Material** | Polished standalone doc site | Tutorials, multi-page guides, versioned docs | Tutorials, projects needing a proper site |
| **docs/ folder** | Docs versioned with code | API refs, changelogs, architecture docs | Projects where docs change in lockstep with code |
| **AGENTS.md** | AI agent instructions (public) | How an AI agent should operate this project — working style, principles, general practices | Hermes ecosystem components (see note below) |
| **AGENTS.local.md** | AI agent instructions (private layer — disclosed only to ≤ L1 remotes) | Machine-local / sensitive facts an agent needs but that must never publish — remotes & topology, credentials, version rules for multi-remote setups | Projects whose agents operate a gitignored local layer (see note below) |

> **Note on the AGENTS pair:** This is a Hermes convention, not a GitHub feature.
> The pair tells AI agents how to operate the project. It is NOT a substitute
> for human-facing docs.
>
> - **`AGENTS.md`** (committed, public): working style, principles, general
>   practices the agent must follow. Only content safe to publish.
> - **`AGENTS.local.md`** (private layer; carried only to ≤ L1 remotes): everything sensitive or machine-local
>   that belongs in the instructions but must never be pushed — remotes &
>   their handling, topology, multi-remote version rules, credential pointers.
>   Anything that would leak in a public projection lives here.
>
> The split is a delivery-vs-record rule, not a folder convention: if a line
> is sensitive it goes in `.local`, never into a public block to be scrubbed
> later. Whether `.local` is *tracked* depends on the remote ladder: it is
> gitignored only when no remote is ≤ L1 (it can never be disclosed); when a
> ≤ L1 remote exists it is committed and clipped per remote trust level
> (tower-model). Always ask the user each remote's level. Both files are **usage documents — write them lean, present-tense,
> forward-looking; history belongs in git log, not in these files** (see
> skill-ecosystem, the skill-ecosystem quality bar Gate 1 — single
> source for this rule).
>
> - Code/tool projects in the Hermes ecosystem (astra-\*): README (human) +
>   AGENTS.md (agent) both required; add AGENTS.local.md when any operating
>   fact is sensitive.
> - Projects NOT in the Hermes ecosystem: AGENTS.md is optional; the local
>   layer applies wherever an agent operates it.

### Decision tree

```text
1. Does this project have a README.md yet?
   └─ No → Write one. This is not optional.

2. Does the README cover everything the user needs?
   ├─ Yes → Stop here. No additional docs needed.
   └─ No → Continue to step 3.

3. What type of project is this?
   ├─ Code / tool / library
   │  ├─ Needs detailed reference docs (config, API, FAQ)?
   │  │  ├─ Yes → GitHub/Gitea Wiki (reference library)
   │  │  │         Keep README as the concise entry point,
   │  │  │         link to Wiki for details
   │  │  └─ No → README + inline comments is enough
   │  └─ Has auto-documented API surface? → also consider
   │       MkDocs + mkdocstrings (alongside or instead of Wiki)
   ├─ Tutorial / guide
   │  └─ → MkDocs Material (standalone site)
   │         Wiki is NOT suitable (no navigation, no search)
   ├─ Creative writing / worldbuilding
   │  └─ → Obsidian vault (authoring) + MkDocs (publishing)
   └─ Simple / one-pager
      └─ → README-only is fine

4. Will an AI agent operate this project?
   ├─ No → stop. The AGENTS pair is unnecessary.
   └─ Yes → create both files now (skeletons in "What each layer
      should contain" below).
      Then ask the user for each remote's TRUST LEVEL (tower-model:
      L0 authority / L1 private / L2 sanitised / L3 public — e.g. a GitHub
      *private* repo may still be L1).
      - If NO remote is ≤ L1 (only sanitised/public): add
        `AGENTS.local.md` to .gitignore — it can never be disclosed.
      - If a remote IS ≤ L1: track it; it is disclosed only to those
        remotes by the clipping ladder.
      Never assume the level — always ask at project or remote creation.
```

### What each layer should contain

**AGENTS.md** (public — working style and principles only, disclosed to every remote):

```markdown
# Agent Instructions

## Scope
Who the agent is acting for, and what it may decide alone.

## Working style
Concise, present-tense, forward-looking. State rules, not history.

## Principles
- <non-negotiable rules the agent must follow>
- Verification: run the change, don't describe it.

## Completion discipline
Before declaring work done: check the change's blast radius (did it affect
other parts of the project?), and update every affected project document —
README, this file, VERSION/CHANGELOG, CONTRIBUTING.
```

**AGENTS.local.md** (private layer — sensitive operating facts; disclosed only to ≤ L1 remotes):

```markdown
# Local Instructions (private layer — only ≤ L1 remotes)

## Remotes
- <name> → <role> (e.g. our forge = primary; mirror = public projection)
- How each remote is treated: what may be pushed where.

## Identity and signing
- Commit identity: <name> <email> — pinned repo-locally (`user.name` /
  `user.email`), never inherited from the global config.
- GPG key: <key-id>; its `uid` must carry the same email — that match is the
  condition for a forge to show `Verified`. `commit.gpgsign` and
  `tag.gpgsign` are both `true`.
- Why it is written down: the repo-local config is not versioned and not
  visible in the remote, so without this line the next reader (or agent)
  cannot tell which identity this repository is supposed to carry, and a
  silent global change re-attributes every future commit.

## Versioning (multi-remote)
- Which remote carries which version line; how they diverge.

## Topology / machines
- Only what an agent must know that must not leak.

## Credentials
- Pointers to the credential store — names, never values.

## Layer attribution
- Allowlist — artefacts permitted to carry instance facts: <paths/patterns>
- Exclusion — artefacts that never enter a ≥ L2 projection: <paths>
- Default: anything not listed must be clean before any public push.
- Only settle the whole-file cases here; a mixed file is judged per segment
  at clip time (see the VCS reference «Prose Artefact Layer Attribution»).
```

**README.md** (the gateaway — concise, scannable):

```
- Title + one-liner description
- Badge bar (license, stars, last commit)
- Quick start (install + hello world, 3 lines max)
- Basic usage example
- Link to Wiki/MkDocs for full docs
- Link to contributing guide (if applicable)
- License note
```

**GitHub Wiki** (the reference — detailed, structured):

```
- Home — project overview and navigation
- Installation — full setup guide, prerequisites, dependencies
- Configuration — all options, env vars, examples
- Usage — detailed examples, common patterns
- Architecture — how it works, code map
- API Reference — endpoints, functions, parameters
- Troubleshooting — common issues and fixes
- FAQ — frequently asked questions
```

### Projects that do NOT need a Wiki

- **Tutorials** — use MkDocs instead (Wiki has no navigation/search)
- **Creative writing / worldbuilding** — use Obsidian + MkDocs
- **Simple one-pagers** — README is enough
- **Meta-repos** (portal/governance repos) — README + docs/ is enough

See `references/project-documentation-strategy.md` for detailed setup
instructions per approach.

### The AGENTS pair across the git lifecycle

The pair is not created at init and forgotten — each lifecycle stage must
keep it coherent with the repo's projection state. The second column governs
the pair itself; the third governs **every other artefact in the repo** — which
of its content belongs at the target level (method: the VCS reference «Prose
Artefact Layer Attribution»).

| Stage | What to do with the AGENTS pair | Content attribution (all other artefacts) |
|:------|:---------------------------------|:------------------------------------------|
| **Init** | Create both files (skeletons above) + `.gitignore` entry for `.local`. | First pass over every prose artefact: judge each segment's level; settle the whole-file cases into the local `Layer attribution` list; handle anything out-of-level before the first push. |
| **Dev** | After any change: run the completion discipline in AGENTS.md — check blast radius, update every affected project document (README, this file, VERSION/CHANGELOG, CONTRIBUTING). | Adding or editing a passage that carries instance facts: it never enters a ≥ L2-bound artefact — write it in the local layer or generalise the value, never commit-then-scrub. A file declared clean that grows a fleet-bound paragraph must be re-judged. |
| **Fork** | Carry the public AGENTS.md forward as project operating instructions; move branch-map / remote / sensitive adaptation facts into AGENTS.local.md. | Adaptation/upstream facts belong to the local layer; the public projection keeps only PATCH-shaped content. |
| **Release / publish** | Before pushing to a **≥ L2** remote: grep the public AGENTS.md for secrets/topology — as clean as the code — and confirm AGENTS.local.md is absent from that tree (`git show <remote>:AGENTS.local.md` must fail **for every ≥ L2 remote**; ≤ L1 remotes may carry it). | Run `scripts/scan-tracked-values.py` over the **projected tree** (not the source tree), then re-read each hit in context and apply the verdict — remove / generalise / keep. A value-level sweep alone cannot remove an out-of-level passage. |
| **Sync / projection** | When clipping a branch for a remote, disclose the local layer only to remotes at **≤ L1** (tower-model). At ≥ L2 (sanitised/public) it must be stripped by the clip. Verify: `git ls-tree -r --name-only <remote>/main \| grep AGENTS.local` must be empty for every ≥ L2 remote, and may be present only for ≤ L1 ones. | Clip per segment, not per file; a content edit that reaches a tag/PR ref or a merge-introduced blob survives a branch-only clip. |
| **History reorg / archive** | Rewriting history rewrites what was public. If a secret ever touched a public commit, the AGENTS pair must record only the current clean state — no "was leaked" narration, just the working rule. | **Removing or archiving a file does NOT remove it from history.** The blob stays reachable through tags, PR refs, merge-introduced content and old branch tips; archive-time is when that history must be swept (all refs + every reachable object — `git log -S` misses merge-introduced content). |
