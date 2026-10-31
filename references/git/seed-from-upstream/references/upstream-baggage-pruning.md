# Upstream Baggage Pruning Checklist (<our-project> Phase 1 experience)

Concrete checklist distilled from pruning <UpstreamName> → <our-project>.
Apply after seeding, before the first release commit.

## 1. GitHub Actions workflows (upstream shipped 25)

KEEP only the 5 generic quality gates (free on public GitHub, no secrets):

| Workflow | Role |
|----------|------|
| `ci.yml` | main CI: lint / test / build (Node matrix) |
| `codeql.yml` | GitHub code scanning |
| `semgrep.yml` | PR semantic security scan |
| `dast-smoke.yml` | PR dynamic security smoke tests |
| `scorecard.yml` | OpenSSF supply-chain score |

DELETE upstream-specific classes (observed names in <UpstreamName>):

- Publish/deploy: `npm-publish.yml`, `docker-publish.yml`,
  `electron-release.yml` (no desktop app), `build-fork.yml`,
  `build-rinseaid-image.yml` (other project), `deploy-vps.yml`
  (we deploy via Podman manually)
- Release flow: `lock-released-branch.yml`, `quality.yml` (only fires on
  `release/**` — project has no release branches)
- Nightly matrices: `nightly-*` (7 files: compat / llm-security /
  mutation / property / release-green / resilience / schemathesis) +
  `mutation-redundancy.yml` — upstream heavy-CI culture; local regression
  suite covers core paths
- AI review / ecosystem: `claude.yml` (needs CLAUDE_CODE_OAUTH_TOKEN
  secret), `opencode-provider-ci.yml`, `opencode-plugin-ci.yml`
- Wiki: `wiki-sync.yml` (no wiki; docs strategy is README-first)

## 2. Retained workflows: content audit (not just keep)

Each kept workflow must be re-read against the new project:

- Env vars referencing upstream (e.g. `<UPSTREAM>_SKIP_SYSTEM_TRUST`,
  `CI_NODE_VERSION: "24"`) → rename / bump to project reality
  (<our-project> uses Node 26)
- Every `run:` script must exist in the new repo
  (e.g. `scripts/quality/classify-pr-changes.mjs` referenced by
  ci.yml AND quality.yml)
- `actions/checkout@v7` etc. pinning is fine to keep

## 3. Docs mirror mechanisms (42-locale i18n mirror)

Upstream gate `check:docs-sync` forces every CHANGELOG edit to sync
`docs/i18n/` — 42 language mirrors of CHANGELOG/SECURITY/README.
For an independent project this is dead weight (real app i18n lives in
`src/i18n/messages/`, unrelated):

```bash
git rm -r docs/i18n/
# drop the docs-sync line from .husky/pre-commit
```

Keep the check script file on disk if you like — just stop hooking it.

## 4. Tag policy (independent public project)

- `git tag -l` — upstream tags are usually NOT cloned by the seed
  (<our-project> had 0)
- Tag fresh with plain SemVer: `v3.8.50` (inherited baseline) — no
  3-layer owner segments (see astra-vcs-assist-versioning)
- Do NOT inherit upstream's version history or tag names

## 5. README credits / acknowledgements section (user-mandated)

Per open-source convention the README must carry a
`## Credits / 引用·参考·致谢` section listing everything the project
is derived from or references:

- Seed upstream (e.g. <UpstreamName>, MIT) — always
- Design-system sources: DESIGN.md may come from the Hermes
  `popular-web-designs` skill / `nicolesaidy/awesome-web-design` repo —
  list the actual URL; if DESIGN.md has no recorded source, ASK the user
  rather than guessing (session lesson: DESIGN.md contained no source URL
  and the source had to be confirmed by the user)
- Any fonts/CDN/assets referenced in the codebase

Verify each credit with the user before publishing — fabricating an
attribution is worse than leaving it out.

## 6. Commit compression before first push (user-corrected behaviour)

User feedback on the first history: "commit太多太杂了。整个Phase1不需要
搞那么复杂吧？" — a phased rewrite must NOT produce one commit per
sub-step. Rules from <our-project> Phase 1:

- Design-system iterations collapse to ONE commit per design language
  (Carbon: integrate + client-boundary + DESIGN.md fix = 1 commit)
- A fix batch verified as one unit (17/17 regression) = 1 commit
- Target 6-8 commits per phase: bootstrap / design adoption / refactor /
  fix(ui) batch / docs / chore(ci)
- Compress with `git rebase -i --root`, then re-sign every commit with
  GPG (hash rewrite is fine while unpushed)

## 7. Review gate: full commit manifest before any push

User: "你还没告诉我你完整的commit整理结果，必须先让我审核过才能规范地
进行后续的推送" — present a complete per-commit manifest (hash, GPG
status `%G?`, date, subject, file count, +N/-M) grouped by phase and
flag every rewriting action; push ONLY after explicit approval.
"先更新内容，不要推送" is the standing rule until final sign-off.
