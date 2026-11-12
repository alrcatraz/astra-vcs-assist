# Agreed grouping preferences

Agreed grouping preferences.

## Grouping conventions (user preferences)

- Minimal commit count — merge small commits into theme commits ("C5可以并入C0或C4，C2和C6可以合并").
- Conventional Commits type+scope: `refactor(ui)`, `chore(i18n)`, `chore(ci)`, `docs`.
- Keep the root seed commit untouched (10k+ files can't be re-split).
- Docs in their own commit; docs-purge AFTER the code-removal commit.
- Public repos (GitHub): never track work dirs — `.gitignore` + `git rm --cached`
  for PLAN.md / .codegraph/ / .vscode/ (stay local, dropped from index).
- **Untracked work-dir file can vanish from the worktree** (a work-dir plan file was
  missing entirely after the reorg) — recover from git objects without any commit:
  `git show <last-commit-with-file>:<path> > <path>` (object survives the rewrite);
  stays `.gitignore`d, so the repo stays clean.
- **Post-reorg follow-ups fold into the last UNPUSHED commit**: README sanitisation /
  doc tweaks → `git add <files> && git commit --amend -S -m "..."` (re-signs; safe
  until the push is approved). User prefers minimal commit count — don't stack a
  second commit for a small docs pass.
- Full plan table before executing: commit list, file counts, per-file hunk decisions,
  version/tag decision — user reviews and approves the table first.
- **NO standalone refactor/branding/cleanup commits** (user 2026-08-06): merge renames,
  dead-code removal and locale sync into the related feat/build/docs/chore commits; the
  commit list must NOT surface branding/cleanup detail. User-approved shape:
  `feat(services)` + `build(docker)` + `docs` + `chore: consistency pass across codebase
  (naming, UI cleanup, locale sync)` — NOT `refactor: rebrand X→Y` / `refactor(ui): remove ...`.
- **Private-domain audit BEFORE public push** (2026-08-06): grep whole tree for
  `git01|wrt\.astra|nb\.internal`, and audit AGENTS.md remotes line, `package.json`
  repository/homepage/author (upstream owner survives forks!), Dockerfile OCI labels
  (`org.opencontainers.image.url/source`), `.env.example`. Replace with the public
  GitHub URL in the SAME pass as the renames — not a follow-up commit.
- **A remote's trust level is a per-repo CONTENT measurement — never copy it from
  another skill's example.** The VCS skills quote concrete pairs as illustrations of
  how the clip works (`gitea: L2` in a disclosure row, `gitea: L1 … GitHub L3` in a
  versioning scope note). Those are not declarations about the repo in front of you;
  writing one down as the level produces a wrong push rule that sounds authoritative,
  and because the level drives the pre-push clip, too high ships a leak and too low
  discards content needlessly. Measure the tracker content instead: run the level
  ladder from the repo's own tree (ADAPT values → INFRA files → identifiers) and read
  off the level — e.g. INFRA present + real internal IPs/hostnames kept = **L1, not
  L2**; L2 is defined by INFRA *stripped*. A remote can be self-hosted and private and
  still be L2, or public and still be L1 if its content says so — the platform tells
  you nothing.
- **An intentionally-public remote can still be carrying a leak** — "public is by
  design" answers *whether to publish*, not *what is safe to have published*. After
  confirming a public remote is deliberate, still run the full leak scan on its
  history: a value that is normal for the private end (a LAN IP, an internal forge
  domain) violates the public end's own level and needs the history rewrite, not a
  policy debate.
