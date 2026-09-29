# Three-Tier Branch Model (main / development / feature) + Protection & CI Requirements

Applies to: all astra-ecosystem repositories under normal development. The main
branch is always `main` (or legacy `master`); a few repos use another name for
their own historical reasons (e.g. the camofox fork's `astra`) — that is a
per-repo fact and does not alter this model's general rules.

## Topology

```text
feat/* · fix/* · chore/* ──PR──▶ development ──PR──▶ main ──tag──▶ release/build machines
   (short-lived, delete after merge)  integration      release line   only main is trusted
```

| Tier | Function | Who may push | Protection |
|---|---|---|---|
| `main` | release line: releasable and pullable by build machines at any moment | PR merges only (development→main) | direct push forbidden, force-push forbidden; PRs need green CI + (when multi-person) review |
| `development` | integration branch: features converge and are validated here | PR merges only (feature→develop); solo repos allow maintainer direct pushes of small fixes | force-push forbidden; CI must run and stay green |
| `feat/*` etc. | single-task workspace | task author freely | none (delete when done) |

Hard rules:
1. Feature branches are **cut from development and merged back to development**;
   main never receives feature commits directly. The merge into `development`
   may be a plain `git merge` (solo repos; PR optional) — squash/rebase-merge
   is a tidiness preference, not a gate. The PR-only rule binds
   `development → main`.
2. Build/deploy machines track main only — anything not on main does not exist.
3. Version bumps and tags happen on main only (release actions concentrate on
   the release line).
4. Merge via squash-merge or rebase-merge to keep the integration line linear;
   inside a feature branch, commit freely.
5. Never force-push a shared branch that has been pushed; personal unpushed
   branches may use `--force-with-lease`.
6. Small single-trunk repos (prototypes/docs) may have only main; the moment
   parallel work starts, add development:
   `git checkout -b development main && git push -u <every-remote> development`.

## CI requirements (per tier)

| Trigger | What runs | Gate |
|---|---|---|
| push to feat/* | test job (fast feedback suffices) | not enforced |
| PR → development | full test + build/smoke chain | all green before merge |
| PR → main | same as above + release pre-check (version/tag consistency) | all green before merge |
| tag v* on main | release pipeline (build→smoke→publish) | failure alerts immediately |

Gitea side: Settings → Branches, add protected branches (main, development),
tick Require approvals + Status checks (list the mandatory jobs); GitHub uses
branch protection rules likewise. In workflow files match the table above with
`on: pull_request` + `on: push: branches:`.

## Dual-forge (private Gitea + public GitHub mirror) push model

The established divergence-handling convention, formalised:

- **Levels first**: per remote assign a trust level (tower-model §1.1) —
  e.g. `gitea: L2`, `github: L3`. The classic private-Gitea/public-GitHub pair
  is the *disclosure* shorthand (L1/L2 → L3 clip). A repo declared clean at
  source may collapse both to the same level with zero pre-push work; read the
  repo's AGENTS.md declaration, never infer from forge brand.
- **Order**: everything goes to Gitea first (private machine room, source of
  truth), then to GitHub (public mirror).
  `git push gitea <branch> && git push github <branch>`.
- **Protection on both sides**: set branch protection on Gitea AND GitHub —
  GitHub is the public face, missing config means running naked; Gitea is the
  work surface, missing config means the setting was pointless.
- **Secrets stay home**: secrets used by Gitea CI live in Gitea repo secrets,
  those used by GitHub CI live in GitHub; never cross them (the one legitimate
  exception: a read-only anonymous PAT when Gitea CI pulls public flake inputs
  from GitHub). Forbid CI-to-CI push loops (a Gitea run pushing GitHub while a
  GitHub run pushes Gitea).
- **Fork upstream sync**: the upstream remote is fetch-only, never push; sync
  merges into development, never merge upstream directly onto main.
- Detailed push/credential-injection recipes: see astra-vcs-assist-git-sync.

### Protection enforcement: configure ≠ enforced (must probe, not trust readback)

Branch protection API calls return 201/200 and a successful readback, yet
still let a direct push through. Two-forge rules that were only *configured*
got bypassed on first real push. Before declaring a branch protected, run the
**probe push** (a throwaway commit, then discard):

```bash
git checkout main
git commit -q --allow-empty -m 'chore: protection probe (discard)'
git push gitea main    # MUST be rejected
git push github main   # MUST be rejected
git reset -q --hard main~1 && git checkout development   # discard probe
# then confirm both remotes' main still at the pre-probe SHA via ls-remote
```

Both remotes must reject AND both `ls-remote` heads must be unchanged. A probe
that "succeeds" means the config is wrong — fix and re-probe until it rejects.

Three-forge gotchas the probe exposes:

- **Gitea `rule_name` IS the branch glob.** On Gitea ≥ the version in use,
  `POST /branch_protections` takes `rule_name` as the pattern matching branch
  names (not a free-form label). Naming it `main-protected` while intending
  `main` creates a rule that matches nothing and silently protects nothing —
  the probe passes. Set `rule_name: "main"` (and `"development"`) exactly.
- **GitHub `enforce_admins: false` = admin self-bypass.** With the flag off,
  a repo owner's direct push prints `Bypassed rule violations` and lands on
  `main` even though `required_pull_request_reviews` is set. Set
  `enforce_admins: true` so the owner is bound too; the probe then rejects.
- **`Everything up-to-date` is a false PASS.** `git push` exiting 0 when the
  remote already equals local attempts no transfer and triggers no hook — it
  proves nothing. The probe must create a genuinely new commit so the push is
  real.

Settings both sides must carry (the pair that makes the probe reject):

| Setting | Gitea `POST /branch_protections` | GitHub `PUT .../branches/main/protection` |
|---|---|---|
| direct push blocked | `enable_push: false` | (implied by `required_pull_request_reviews`) |
| force-push blocked | `enable_force_push: false` | `allow_force_pushes: false` |
| PR required | `enable_pull_request: true` + `required_approvals: 1` | `required_pull_request_reviews.required_approving_review_count: 1` |
| admin bound | (Gitea rule applies to owner too) | `enforce_admins: true` |

`enforce_admins: true` and force-push blocks are deliberate: they are what an
emergency has to consciously remove (below), not accidentally ride through.

### Emergency override — the ONLY sanctioned reason to unlock protection

Protection is locked by default. Two-forge branch protection may be
**temporarily lifted** only for a genuine history-rewrite incident — sensitive
data reached a remote (real hostname/IP/credential committed) and the fix
requires rewriting `main`. Never lift it for convenience (skipping a PR,
batch-pushing, "it's faster").

Procedure (identical shape on both forges; do the history rewrite, verify,
then restore before doing anything else):

```bash
# Gitea — remove rule, rewrite, recreate with the SAME enforcement flags
curl -s -X DELETE -u "<owner>:$PW" \
  "$GITEA_API/repos/<owner>/<repo>/branch_protections/main"
git push gitea +<clean-sha>:refs/heads/main --force   # or filter-repo output
curl -s -X POST -u "<owner>:$PW" -H 'Content-Type: application/json' \
  -d '{"rule_name":"main","enable_push":false,"enable_force_push":false,
       "enable_pull_request":true,"required_approvals":1}' \
  "$GITEA_API/repos/<owner>/<repo>/branch_protections"

# GitHub — delete rule, rewrite, PUT it back with enforce_admins true
gh api repos/<owner>/<repo>/branches/main/protection --method DELETE
git push github +<clean-sha>:refs/heads/main --force
gh api repos/<owner>/<repo>/branches/main/protection --method PUT --input - <<'JSON'
{"enforce_admins": true, "allow_force_pushes": false, "allow_deletions": false,
 "required_pull_request_reviews": {"required_approving_review_count": 1},
 "restrictions": null, "required_status_checks": null}
JSON
```

Immediately after restoring: re-run the probe push (must reject) and
`ls-remote` both remotes (must show the rewritten SHA). An override that ends
without a passing probe is an unprotected branch. Full history-rewrite recipe
(filter-repo, leak grep, GitHub cache purge) lives in
`references/tower-model.md` §Disclosure and `safe-force-push.md`.

For which *slice* each audience may see (layering and clipping decisions), see `references/tower-model.md`.

## Daily operation sequence (quick reference)

```bash
# start a task
git checkout development && git pull --rebase
git checkout -b feat/<topic>
# …work, commit in small steps…
git push -u gitea feat/<topic>          # (also push github if publication is needed)
# PR: feat/<topic> → development (Gitea web / tea CLI); squash-merge once CI is green
git checkout development && git pull --rebase
git branch -d feat/<topic> && git push gitea --delete feat/<topic>
# end-of-phase release: PR development → main, merge after green CI, tag v<X.Y.Z> on main
```
