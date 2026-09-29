# AGENTS.md — astra-vcs-assist (repo-local binding rules)

Every agent working in this repository MUST follow these rules. They override
convenience and precedent. Enforcement note: this file is force-injected into
agent context for the repo; keep it current with `references/tower-model.md`.

## 1. Language and tone (hard rule)

- All tracked content is **English, British spelling** (`-ise`, `-our`,
  `-ence`, `-re`). Applies to SKILL.md bodies, references, comments, commit
  messages. Sole exception: README may carry a Chinese summary section.
- Allowed non-English remnants: frontmatter `triggers:` entries (Chinese
  trigger words are a fleet convention for matching), and functional strings
  inside code/grep patterns. Nothing else.
- **Usage document, never changelog.** AGENTS files, skill bodies and references
  state the *current* correct procedure only. Never carry verification dates,
  incident timelines, before/after archaeology, renaming or retirement notes,
  meta markers, or quoted decision narration. Change history lives in git log.
- One-line test per passage: does reading it change how a future edit is
  *executed*? No → delete it.

## 2. Trust-domain layering (tower model, see references/tower-model.md)

- Remote level declarations (tower-model §1.1 ladder):
  - `gitea : L1` — private authority: the full tower, with ADAPT values left
    concrete because a fleet agent pulls this repo and fills in only its own
    machine's differences (the instance facts are `allowlist`ed, not neutralised).
    This repo carries no INFRA files, so L0 and L1 are content-identical here —
    L1 names the intent: real values delivered as-is.
  - `github : L3` — public sanitised projection (disclosure clip of Gitea main)
- **GitHub must never contain what Gitea lacks.** Direction is one-way for
  content; verify per release with `git diff main public` — allowed diffs are
  only: `gitea/` dir, instance-specific domain lines, version suffixes,
  private-architecture docs. Any other diff is a leak — stop and fix.
- Instance facts (private forge domains like `your-forge.example.com`,
  machine names, credential paths) live ONLY in files listed under
  `.publications.allowlist` (below §4). New files default to "must be clean
  before public push".
- INFRA commits carry `ci(<tool>):` prefixes; projections are cherry-pick /
  replay, never merge across the boundary.

## 3. Sub-skill lifecycle

- Sub-skills are stored **in this repo** and symlinked into
  `~/.hermes/skills/vcs/`. A sub-skill that exists only as a real directory in
  `~/.hermes/skills` is an orphan — migrate it (move into repo, replace with
  symlink) on sight.
- Every new/renamed sub-skill must be registered in THREE places or the change
  is incomplete: umbrella `SKILL.md` (architecture tree + routing summary +
  frontmatter `related_skills`), `routing.yaml`, and the symlink.
- Editing goes to the dev repo `~/Projects/astra/astra-vcs-assist/`; the
  production copy `~/.astra/repos/astra-vcs-assist/` is synchronised by
  fetch/reset only, never edited.

## 4. Release discipline (see versioning sub-skill for full flow)

- Layers are nested subsets: GitHub(public) ⊂ Gitea(main) ⊂ instance copy.
  Content is added upward; version suffixes strip downward.
- Release advances **both remotes' `main` via PR**; pushing a branch + tagging
  alone is not a release.
- Before any public push: run the leak check (§2) and the language check (§1).

## 5. Publication allowlist (files permitted to carry instance facts)

```
README.md                      # "This instance" sections (EN + ZH summary)
gitea/**                       # platform skill, private-forge by nature
versioning/**                  # documents this repo's own dual-branch layout
references/git-credentials.md  # example URLs incl. private forge host — REVIEW BEFORE PUBLIC PUSH;
                               # prefer generic placeholders in the public projection
```

Anything not listed must contain zero instance identifiers.

## 6. .gitignore discipline

- Generated/local artefacts stay out: `.codegraph/`, `.env`, IDE dirs,
  `config/devices.yaml` (machine-local overrides). Already covered.
- Add here immediately when a tool starts writing local files (caches, lock
  drift, scratch exports) — never commit them "temporarily".
- Symlink targets under `~/.hermes/skills` are NOT repo content; never add
  resolved copies back into the tree.
