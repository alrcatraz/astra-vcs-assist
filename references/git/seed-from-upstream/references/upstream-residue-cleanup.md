# Upstream Residue Cleanup (post-seed, later phase)

Follow-on to seeding: when the user says 「彻底 / 全清」about upstream info
(after the project has diverged for phases), delete the remaining upstream
product/process/user-facing docs and fix every dangling reference.
Measured 2026-08-02 on <our-project> (<UpstreamName> seed).

## Judgement criterion (user-endorsed, ask when unsure)

- **删**「上游产品/流程/用户信息」: marketing, user guides, release
  processes, deployment walkthroughs, roadmap, comparisons, upstream CI
  config (`.mergify.yml`), assistant rules (`GEMINI.md`), nav index files
  (`docs/README.md`, `docs/meta.json`).
- **留**「描述本项目保留源码机制的技术文档」: architecture, compression,
  routing, reference, security, sessions, frameworks — even if they carry
  upstream version numbers, they describe mechanisms the codebase still has.
- Confirm deletion depth with the user via clarify (「全清」vs partial) —
  do not guess once the scope is ambiguous.

## Deletion + reference-fix sequence (measured)

1. `git rm -r -q` the whole class (e.g. `docs/ops docs/getting-started
   docs/comparison docs/README.md docs/meta.json .mergify.yml GEMINI.md` +
   per-file `git rm` for guide lists). One stage = one commit later.
2. Grep whole repo for dangling references, **excluding
   `.git .source node_modules .build`** — `.source/` is Next.js/fumadocs
   build output (gitignored), its stale `meta.json` strings are NOT real
   references.
3. Fix in this order: central maps first (e.g. `REPOSITORY_MAP.md` — counts
   "44 files + 4 subdirs" must become the new "91 files + 12 subdirs",
   drop whole sections that only referenced deleted files, rewrite
   navigation tips), then per-file links (self-reference the file instead
   of pointing at a deleted guide), then **code**: `src/app/docs/page.tsx`
   featuredLinks and section folders must point at surviving docs; brand
   residue (`h1 "<UpstreamName> Documentation"`, openGraph `<upstream>.online`)
   must be replaced by the single source of truth constant
   (`APP_CONFIG.name`) — hardcoded brand/ports/hostnames always go through
   constants per user convention.
4. **Tests that assert deleted files will fail** — grep `tests/` for the
   deleted paths: `REQUIRED_DOCS` lists (drop deleted entries, keep
   surviving), and doc-content assertions (delete the now-meaningless
   test). Run `node --test tests/unit/<affected>` to confirm green.
5. TSC verify only the files you changed (see <our-project>
   `<upstream-checkout>/_references/tsc-dual-config-and-scheme-b.md`) — pre-existing error noise
   is large, grep-filter your touched paths, never count all errors.

## fumadocs URL rule (needed to fix featured links)

fumadocs slug = **kebab-case of the filename**:
`docs/architecture/ARCHITECTURE.md` → `/docs/architecture/architecture`;
`docs/reference/API_REFERENCE.md` → `/docs/reference/api-reference`.

## Commit shape

One `chore(docs):` commit carries: deletions + doc reference fixes + code
fallout (page.tsx) + test fixes — they are one concern (the deletion's
integrity). Count deletions explicitly in the message ("49 files: A3 + B25
+ ②21"). Never mix in unrelated feature commits. GPG-sign, do not push
until user approves (see <our-project> `<upstream-checkout>/_references/phase-closure-and-commits.md`).

## Pitfall: lint-staged backup stash

Husky lint-staged leaves `stash@{0}: lint-staged automatic backup`. NEVER
`git stash pop` in this repo to compare baselines — it resurrects that old
backup (stale code) as UU conflicts. Recovery: `git reset --hard HEAD` +
`git stash drop stash@{0}` after confirming it's the worthless backup.
Baseline comparisons: `git show <commit>:<file>` or a temp worktree, not
stash.
