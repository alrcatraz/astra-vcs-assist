---
name: astra-vcs-seed-from-upstream
description: Create an independent git repository seeded from an upstream source (orphan root technique). Not a fork, not a clone — clean git history starting from an upstream codebase.
version: 1.1.0
author: alrcatraz
triggers:
  - "seed from upstream"
  - "orphan root"
  - "独立仓库 上游种子"
  - "非 fork 派生"
  - "upstream seed repo"
  - "history reset new repo"
platforms: [linux]
metadata:
  hermes:
    tags: [vcs, git, upstream, orphan-root, repo-bootstrap]

---
# Seed-from-Upstream: Independent Repo from Upstream Clone

Use this pattern when you want an independent project seeded from an
upstream source — NOT a fork (shared git history), NOT a clone (upstream
remote). The git history starts clean on an orphan root.

## Trigger Conditions

- You have an upstream repo's code and want to start an independent project
- The project is based on upstream but 80%+ will be rewritten
- You want clean git history (no upstream's 1000+ commits in git log)
- You need to dual-publish (Gitea private + GitHub public)

## Upstream Baggage to Prune (read before first commit)

Seeded projects inherit upstream's repo furniture. Prune aggressively
before the first commit — full checklist in
`references/upstream-baggage-pruning.md`. Key rules:

- **CI workflows**: upstream ships 20-30 GitHub Actions; keep only the 5
  generic quality gates (ci / codeql / semgrep / dast-smoke / scorecard).
  Delete upstream-specific publish, deploy, release-branch-lock,
  nightly-matrix, AI-review (claude.yml), sub-package CI and wiki-sync
  workflows.
- **Post-seed cleanup (later phases)**: upstream product/process/user docs
  and configs still linger after the first release. When the user asks
  「彻底/全清」, the deletion + reference-fix workflow (git rm, dangling
  link repair incl. code/tests, fumadocs slug rule, brand → constants,
  commit shape) lives in `references/upstream-residue-cleanup.md`.
- **Retained workflows still need a content audit**: upstream env vars
  (e.g. `<UPSTREAM>_SKIP_SYSTEM_TRUST`), pinned Node versions, and every
  referenced script (e.g. `scripts/quality/classify-pr-changes.mjs`)
  must match the new project — verify each `uses:` and `run:` target.
- **npm scripts deleted at bootstrap break CI later**: if the seed dropped a
  script the retained workflows still call (`npm run build:cli` →
  `prepublish.ts`), restore the upstream script definition rather than
  rewriting workflows. Grep `.github/` for every `npm run X` and diff
  against package.json.
- **Deep stripping (2nd pass)**: removing an upstream ecosystem (desktop
  shell, 42-locale doc mirrors, CI jobs) leaves a long dangling-reference
  chain — `needs:`/summary/PR-check text after job deletion, orphan-script
  checks must include `tests/unit` (tests import release tooling), mirror
  trees reach into scripts/tests/npm-scripts/lint:md/.dockerignore/husky/
  docs-route fallback/i18n keys. Full checklist:
  `references/stripping-reference-chains.md`.
- **Docs mirror mechanisms**: e.g. `docs/i18n/` 42-locale CHANGELOG
  mirror gated by `check:docs-sync` — remove the mirror directory and
  drop the hook line; the check script must not gate commits anymore.
- **Tag policy**: independent public projects use plain SemVer tags
  (`v3.8.50` style) — NOT the 3-layer scheme. Check `git tag -l` (upstream
  tags are usually not cloned) and tag fresh from your own main.

## Workflow

### 1. Clone and quarantine

```bash
cd /tmp && git clone <upstream-url> upstream-source
```

### 2. Create target with orphan root

```bash
cd ~/Projects/<org>/<project-name>
git init
git checkout --orphan main
```

### 3. Import upstream files (watch for .git/)

```bash
cp -r /tmp/upstream-source/* /tmp/upstream-source/.[!.]* ./
```

**IMPORTANT:** `cp -r` from a clone carries `.git/`. If contaminated:

```bash
rm -rf .git
git init
git checkout --orphan main
```

### 4. Set per-repo identity

```bash
git config user.name "Your Name"
git config user.email "your@email.com"
git config user.signingkey <key-id>
git config commit.gpgsign true
git config tag.gpgsign true
git config pull.ff only
git config push.autoSetupRemote true
```

### 5. Preset GPG passphrase (headless Linux)

```bash
/usr/libexec/gpg-preset-passphrase --preset <key-id> <<< "passphrase"
```

Without this step, `git commit -S` hangs waiting for passphrase on headless.

### 6. First commit — skeleton (README, LICENSE, .gitignore)

```bash
git add README.md LICENSE .gitignore
git commit -S -m "chore: initial project skeleton"
```

### 7. Import upstream source code

```bash
cp -r /tmp/upstream-source/<src-dir> ./
cp -r /tmp/upstream-source/<config-files> ./
# Add selectively — don't copy everything blindly
git add .
git commit -S -m "feat: import upstream codebase (vX.Y.Z)"
```
metadata:
  hermes:
    tags: [vcs, git, upstream, orphan-root, repo-bootstrap]

---

## Post-Seed Rename Strategy (Tier 1/2/3)

After seeding, the project has upstream's name everywhere. Rename
systematically — NOT all at once, NOT source-level. Follow tier order:

### 🔴 Tier 1 — User-visible identifiers (rename now)

Done **before the first functional release**. Users and operators see these:

| What | Examples |
|------|----------|
| Environment variables | `UPSTREAM_BUILD_MEMORY_MB=4096` → `PROJECT_BUILD_MEMORY_MB` |
| Docker metadata | OCI labels, image name, container name |
| Config paths | `DATA_DIR=/var/lib/upstream/` |
| Binary entry point | `bin/upstream.mjs` |
| Build config keys | `UPSTREAM_USE_TURBOPACK`, `UPSTREAM_BASE_PATH` |
| `.env.example` vars | All env vars with the upstream prefix |
| File paths in docs | Installation guides, compose files |

**Scope:** ~40+ env vars in env files + a handful of config/build files.

### 🟡 Tier 2 — Internal aliases (rename after Phase 1 works)

Done **after verifying the project builds and runs**. These touch multiple
files but don't affect runtime logic:

| What | Examples |
|------|----------|
| Path aliases | `@upstream/lib` → `@project/lib` in tsconfig, vitest, webpack |
| Workspace names | `@upstream/workspace` in package.json workspaces |
| Transpile packages | `transpilePackages: ["@upstream/lib"]` in next.config |

**Scope:** 2–5 config files, coordinated changes.

### ⚪ Tier 3 — Source internals (leave alone unless rewriting)

**Do NOT rename.** These are the internal implementation — function names,
type names, enum values, module paths inside `src/`, internal comments.
They:
- Are invisible to users and operators
- Touch 100+ files in a typical large project
- Risk introducing regressions in core logic
- Can be renamed naturally as pages/components are rewritten

**Scope:** 100+ source files in a 10K-file project. Rename naturally during
refactoring phases.

### Rename Checklist

```markdown
- [ ] Tier 1: env vars, Docker labels, config paths, binary names
- [ ] Update .env.example to use new prefix
- [ ] Update Dockerfile ARG/ENV names and OCI labels
- [ ] Update next.config.mjs env var references
- [ ] Update all docs (README, compose files, install guides)
- [ ] Tier 2: path aliases, workspace names (after Phase 1 verified)
- [ ] Tier 3: source internals (naturally, during page rewrites)
```

---

## Pitfalls

- **Don't rename env vars in `.env` until you verify the new names work.**
  The running container uses `.env` — break it and the gateway goes down.
  Test with a copy first.
- **No such thing as a "simple" grep-replace on 100+ src/ files.**
- **Never seed with `git checkout -b main <upstream-tag>`**: the branch inherits
  upstream history, so a later `--orphan` squash leaves ~10k "deleted file"
  entries in commit 1 and pushes drag the whole upstream object store to your
  forge. Seed from the tag's TREE: `git checkout --detach <tag>; mkdir /tmp/seed;
  git archive HEAD | tar -x -C /tmp/seed`, then fresh-init on `main` and copy the
  tree in. Pre-push check: `git ls-remote origin | wc -l` = 0 refs AND `du -sh
  .git` sane (tens of MB for code-only drops, not GB). Recovery if already wrong:
  rebuild orphan from `HEAD^{tree}` (`read-tree HEAD^{tree}; checkout-index -a;
  commit --orphan main`) + force-push — safe while no other branches/PRs exist.
  One wrong match in a dynamically-evaluated string causes a hard-to-debug
  runtime failure. Keep Tier 3 untouched.
- **The same trap, worse shape — a sanitised projection onto a private lineage.**
  Publishing a filtered/desensitised clip of a private repo as a commit ON TOP of
  the private history leaves a clean head tree, so every tree-level leak scan
  passes, while each ancestor commit still carries the private tree — private
  notes file, withheld topics, machine names — readable by anyone who clones. Give
  the projection its own root: `git checkout --orphan` + one commit of the
  projected tree, push that. Verify on every push: `git rev-list --count <proj>
  --not <private-ref>` (projection commits only) AND a per-commit path + content
  scan over `git rev-list <proj>`. Tell-tale: `git merge-base <proj>
  <private-ref>` returns a commit instead of nothing. A release tag must not point
  into the private lineage either — delete the remote tag ref, re-point it inside
  the published root; tags whose commits the filter did not touch keep their SHA
  and need no action.
- **Verify a published ref against the REMOTE, never a local tracking ref.**
  After a force-push the local `origin/<branch>` can still hold the old commit
  (or a pre-existing unrelated projection tip), so checks read as "remote is
  dirty" or "remote is clean" at random. Compare with `git ls-remote <url>` or a
  fresh clone into a scratch dir before concluding anything.
- **Build memory for large (10K+ file) Next.js projects:**
  Production `next build` needs >4GB heap for a codebase this size.
  Default V8 limit (~2GB) causes exit 137 even on machines with free RAM.
  Always set `NODE_OPTIONS=--max-old-space-size=4096` in CI/CD and Docker
  builder stages. On machines with <16GB RAM, delegate the build to a
  better-resourced machine (build server, CI runner).
- **`@carbon/react` + Next.js 16 App Router:**
  Carbon v1.112.0 components lack `"use client"` directives. Import them
  through a wrapper file with `"use client"` at the top, then re-export
  the components. Import CSS separately via `@carbon/styles/css/styles.css`.
- **Recreating a tag in a non-interactive shell.** An annotated tag (`-a`/`-f`)
  opens `$EDITOR` and dies when none is available; with `tag.gpgsign` on it also
  blocks on the key passphrase. Recreate as `git tag -d <t>` then
  `git -c tag.gpgsign=false tag -a -m "…" <t> <sha>`, and confirm the object
  actually moved (`git rev-parse <t>`) BEFORE pushing — a failed recreate leaves
  the old tag in place and the push then reports a no-op that reads like success.
  Remove a remote tag with `gh api -X DELETE repos/<o>/<r>/git/refs/tags/<t>`
  (no local checkout or tag needed).
- **A scan loop's exit status is not its result.** `$?` after a grep inside a
  `for`/pipe body reports the status of the last command in the pipeline, so an
  empty match reads as success and "0 hits" can mean "the probe never ran" — the
  false-negative that lets a leak through. Count hits explicitly (`N=$((N+1))`
  per match) or assert on the printed output.

---

## Reference Example

See `references/example-rename-audit.md` for a concrete
rename audit with real file counts. This skill's references/ directory is
at `~/.hermes/skills/astra-vcs-seed-from-upstream/references/`.dapt for new project
### 5. Preset GPG passphrase for headless signing

```bash
/usr/libexec/gpg-preset-passphrase --preset <keygrip> <<< "$GPG_KEY_PASSPHRASE"
```

**Do NOT `gpgconf --kill gpg-agent` first.** It clears any passphrase already
cached, so a signing setup that was working starts failing; and the same agent
backs `pass` (the git credential helper) and GCM, so pushes and vault reads
break with it — three unrelated-looking failures from one command. Deep load
`astra-vcs-assist` → `references/gpg/key-lifecycle/` for the recovery script.

### 6. First commit

```bash
git add -A
git commit -S -m "chore: initial project bootstrap from <upstream>"
```

---

### 7. Post-Import Cleanup — Tiered Rename Strategy

After seeding from upstream, the project carries upstream-specific naming
(env vars, config paths, binary names, internal aliases). Rename
systematically using a three-tier approach:

#### Tier 1 — User-Visible Names (Phase 1)

Rename everything an admin or operator sees:
- Environment variables: `UPSTREAM_*` → `PROJECT_*` prefix
- Docker OCI labels (`title`, `url`, `description`)
- Binary entry point (`bin/upstream.mjs` → `bin/project.mjs`)
- Config paths (`~/.upstream/` → `~/.project/`)
- Env var docs in `.env.example`

Affects: Dockerfile, next.config.mjs, .env.example, package.json, bin/

#### Tier 2 — Internal Aliases (Phase 2)

Rename path aliases and workspace names:
- `@upstream/workspace` → `@project/workspace`
- Update `tsconfig.json`, `vitest.config.ts`, `next.config.mjs` aliases

These are tied to the build config and should be done when touching
those files (e.g. alongside UI / dependency changes).

#### Tier 3 — Source-Code Internals (Never)

Type/interface/function/enum names inherited from upstream are
**evidence of provenance** and should be kept per open-source
conventions. Renaming them provides no user benefit and introduces
risk of bugs.

---

## Pitfalls

- **Large-project OOM during `next build`:** Projects with 10,000+ files
  (especially with Carbon + Tailwind) exceed V8's default ~2 GB heap.
  Set `NODE_OPTIONS=--max-old-space-size=4096` in build environment.
  This is correct configuration, not a workaround — the builder stage in
  a multi-stage Dockerfile has more memory than the runner stage.

- **GPG passphrase in headless CI:** Use `gpg-preset-passphrase` with
  the key's keygrip. Keygrip = `gpg -K --with-keygrip | grep Keygrip`.
  See `skill astra-vcs-assist → `references/gpg/key-lifecycle/` for full GPG lifecycle.

---

## Example

See `references/example-rename-audit.md` for a concrete
application of the tiered rename strategy (<UpstreamName> → <our-project>).

Verify: `git log --oneline` should show exactly one commit.

### 8. Create remote and push

**Gitea** (if push-to-create is disabled):

```bash
curl -s -u "user:token" -X POST \
  https://git.example.com/api/v1/user/repos \
  -H "Content-Type: application/json" \
  -d '{"name":"<repo>","private":true,"auto_init":false}'
```

**Then push:**

```bash
git remote add origin <remote-url>
git push -u origin main
```

## Verification

```bash
git log --oneline         # Should show only YOUR commits
git ls-files | wc -l      # Staged file count
find . -not -path './.git/*' -type f | wc -l  # On-disk file count
# Difference = .gitignore filtering; check with:
git status --ignored | head -20
```

## Pitfalls

1. **`.git/` contamination** — `cp -r` from a git clone always carries
   `.git/`. Always verify with `git log --oneline`. Fix: `rm -rf .git`
   then `git init && git checkout --orphan main`.

2. **GPG on headless** — Call `gpg-preset-passphrase` BEFORE `git commit -S`.
   The passphrase cache timeout is configurable in `gpg-agent.conf`.

3. **Gitea push-to-create disabled** — If `git push` returns 403, the
   repository doesn't exist. Create it via API or web UI first.

4. **Dual copyright** — Retain upstream's copyright line and add yours.
   Both live in the same MIT/Apache/BSD file.

5. **File count mismatch** — `git ls-files` vs `find` counts differ when
   `.gitignore` is actively filtering (common with large upstreams).
   Not necessarily a problem, but worth verifying the ignored files.

