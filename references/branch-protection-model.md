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
   main never receives feature commits directly.
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

- **Order**: everything goes to Gitea first (private machine room, source of
  truth), then to GitHub (public mirror).`git push gitea <branch> && git push github <branch>`。
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
