# The Tower Model — Universal Repo-Topology Governance

Applies to **every project**, not forks only. Remote count, presence of an
upstream, and disclosure differences are parameters; they never change the
model itself. Day-to-day mechanics (how to push, how to set protection) live in
git-sync / branch-protection-model / versioning. This file governs exactly one
question: **which layer content is stacked in, and which slice each audience
is allowed to see.**

## 1. Axiom

Stack content by role into **one linear tower**; satisfy every "who sees which
slice" need by **truncating a projection**, never by maintaining parallel
branches. Maintenance cost stays O(1), independent of audience/remote count.

```
INFRA   environment-bound plumbing: CI/nix/packaging/deploy  → never leaves the trust domain
ADAPT   localisation: branding, domains, LICENSE addenda, distribution notices → judged item by item
PATCH   substantive changes: fixes, features                 → the payload most valuable outward
BASE    upstream snapshot (empty when there is no upstream)  → rebase anchor
```

A first-party project (no upstream) stacks identically from its initial commit
— its typical projection is the "open-source release view = BASE+PATCH(+ADAPT
as appropriate), INFRA stripped bare". A fork is merely the special case where
BASE is non-empty and backflow is desired.

## 2. Two projection classes

### Projection A — towards upstream

- **Carrier**: the upstream-tracking mirror lives in the `up/` namespace
  (reserved name `up/main`) = pure fast-forward image of BASE, zero private
  content, fetch-only. It never shares a name with `<dist>`, so no forge-side
  confusion is possible. PR bases are cut from it as short-lived
  `up/<topic>-pr` branches.
- **Payload**: the PATCH segment only (cherry-picked; a purely technical fix
  inside ADAPT may ride along, anything carrying private identifiers must not).
- **Backflow**: once upstream merges an equivalent change, the next rebase
  skips it automatically via patch-id → the patch retires.
- **Following upstream**: `git rebase --onto upstream/vNEW upstream/vOLD <dist>`;
  INFRA lands back on top by itself, conflicts surface only in the PATCH layer.
- Platform-side PR mechanics: see `astra-vcs-assist-git-fork` and its
  `references/upstream-pr-from-selfhosted-git.md`.

### Projection B — towards remotes

Every remote has two attributes: **trust domain** (private forge / public
forge / upstream) × **sync role** (authority / fast-forward mirror / projection
target). Classify each remote pair into one of three states first:

| State | Test | What gets pushed | Detail owner |
|:------|:-----|:-----------------|:-------------|
| **identical** (mirror/DR) | same trust domain, byte-for-byte required | whole tower, ref-by-ref (branches + tags follow in full); divergence between the two is an incident | git-sync §2 |
| **divergent** (separate edit rights or different roles) | e.g. private authority + public cold backup allowed to lag | only `<dist>` plus release tags; never push the other side's local-only branches | git-sync §0 decision table |
| **disclosure** (cross-trust-domain publication) | private → public release repo | **strip INFRA + sanitise ADAPT** (domains/hostnames/credential paths → neutral words); human-triggered at release time, never automatic; when history contains unclippable private traces, rebuild the projection history via squash/filter-repo — pushing the raw tower is forbidden | versioning «Three-Layer Content Architecture» + «Content classification for public» (its sanitisation checklist and diff-verification method are authoritative) |

One project may carry several pair-states simultaneously (e.g. Gitea↔GitHub
backup = identical, Gitea↔upstream = Projection A, public release repo =
disclosure) — **judge each pair independently, stack the rules**.

**Conflict arbitration**: if some public repo is declared both "mirror
(identical)" and "sanitised (disclosure)", the definition is contradictory —
demote one state first. An automatically-synchronised public projection is
never allowed (it bets that INFRA never errs).

## 3. Namespace conventions

**Naming rule (reconciled with the three-tier branch model):** `<dist>` is a
*role*, not a name — its default landing name is `main` (or legacy `master`),
exactly as branch-protection-model.md requires for every astra-ecosystem repo.
A fork may give `<dist>` an alternative name (fleet instances: `astra`) only to
disambiguate it from an upstream `main` that also lives in the same repo; such
a rename is a per-repo fact and must be declared in that repo's AGENTS.md.
Repos without an upstream have no reason to deviate from `main`.

| Role | Kind | Rules |
|:-----|:-----|:------|
| `<dist>` | branch, default on the primary forge; **named `main` unless a fork collision forces otherwise** | production release line = the complete tower; release tags land here |
| `up/main` | branch, **primary forge only**, forks with an upstream | the upstream-tracking mirror: pure fast-forward of upstream, fetch-only, PR base; kept inside `up/` so it can never collide with `<dist>`/`main` |
| `up/<topic>` | short-lived branches | projection workspaces, discarded after use: `up/<topic>-pr` for upstream PRs; `up/public` = sanitised disclosure workspace derived from `<dist>`, pushed as the public remote's `main` |
| `upstream/v*` | **tag** (not a branch) | upstream snapshot anchor: resists accidental pushes and fetch-name collisions, and reads cleanly as `--onto` argument |

Relation to the three-tier branch model (branch-protection-model.md): that one
governs `main/development/feat/*` — the **internal development flow** of the
tower; this model governs `<dist>`/`up/*`/`upstream/v*` — the **cross-audience
projection surface**. They are orthogonal: `<dist>` *is* that very `main` in
non-fork repos, and merging `feat/*` into `<dist>` follows the other document.

## 4. The fuse trio

1. INFRA commits always carry a `ci(<tool>):` prefix, everything else uses
   conventional commits — layer membership is recognisable at a glance.
2. INFRA files live only at paths the projection target does not have
   (`ci/`, `.gitea/`, `packaging/`…) — contamination becomes visible instantly.
3. Projections are always cherry-pick/replay, **never merge** (merge drags
   ancestral INFRA across the boundary).

## 5. Repository bootstrap procedure (four questions fix the shape)

① Is there an upstream? → decides whether BASE is empty and whether
Projection A exists
② Which trust domain does each remote belong to? → cross-domain pairs are
Projection-B disclosure candidates
③ Must same-domain remotes be byte-identical? → yes = identical; no = divergent
(must state the reason, otherwise treat it as debt)
④ Which layers may the public side see? → record a one-line table (layer ×
visibility) in the project's AGENTS.md; projections clip accordingly

## 6. Cadence

Schedule rebases between releases; after a rebase run the full build
verification before tagging a release; chasing novelty is optional — security
fixes outrank version freshness.
