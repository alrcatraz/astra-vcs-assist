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

### 1.1 Trust levels are truncation points on the ladder

Trust level is **not** a label glued onto a remote; it is a cut point through
the four-layer ladder, defined by *which layers the level discloses*. Higher
disclosure ⊇ lower disclosure — you may only clip downward, never publish
content upward. This makes every per-remote policy a single number, so
multi-remote topologies of any size fall out of one rule instead of needing
enumerated cases.

```
L0  authority    BASE + PATCH + ADAPT + INFRA   (dev copy — full tower; real values intact)
L1  private      BASE + PATCH + ADAPT + INFRA   (the private trust tier: INFRA intact,
                  ADAPT left concrete so a fleet consumer pulls and fills in only its
                  own machine's values; neutralising ADAPT is the repo's content choice,
                  not the level's requirement — see trust-level-verification §3)
L2  sanitised    BASE + PATCH (+ ADAPT as the repo neutralised it at L1, or none)
                  (INFRA stripped — internal-exchange version, no CI/deploy config;
                  if the repo kept ADAPT concrete at L1, neutralise it here before
                  any cross-org exchange)
L3  public       BASE + PATCH (+ approved ADAPT)    (zero private identifiers:
                  no forge brands/domains/machine names; full-tree leak grep)
```

**What separates each level:**
- L0 → L1: no clip (both are the full tower) — L0 is reserved for the authority/dev copy; a remote declaring the same tower takes L1. Neutralise ADAPT here only if the remote's consumers do not need it concrete
- L1 → L2: strip INFRA (CI/container/deploy config — the "config-generality" layer)
- L2 → L3: neutralise remaining private identifiers (forge brands, domain names, machine names)

**Why this order:** ADAPT concrete values are the most sensitive item — they leak
reader-specific topology and can carry secrets — so neutralising them comes before
stripping INFRA. The INFRA strip is safe last because its config files are portable
(they say *what* is run, not *where*), once any embedded credential references are
removed.

Each remote declares `L<n>` plus optional pins:

```
<remote> : L<n> [mirror-of <other>] [fetch-only]
```

- **Ask for every level — never infer one.** A level is a content decision, not a
  platform fact: self-hosted may sit anywhere (L0 when it holds real values the
  fleet consumes as-is, L2 when cleaned), and a GitHub *private* repo may qualify
  as L1. At project creation and at every added remote, ask which level that remote
  takes — and before relabelling an existing remote, measure its content first
  (hostnames, machine paths, private IPs, credential refs), state the inventory,
  and let the owner decide. The published declaration must match what is actually
  pushed, not what sounds tidy. Full method:
  `references/trust-level-verification.md` (this repo).
- **Monotonicity**: any remote may sit at any level ≤ L0; skipping levels is
  fine (a public GitHub at L3 while Gitea sits at L2).
- **Superset invariant**: content published to L<i+1> must already exist at
  L<i>. A more-disclosed remote must NEVER carry what a less-disclosed one
  lacks. Verify per release with a tree diff whose allowed deltas are exactly
  the clip between the two levels.
- **Mirror pin**: `mirror-of` binds a remote to another's content ref-by-ref
  (or byte-for-byte); it inherits the target's level and adds no projection
  work. Unpinned same-level remotes are independent editors, not mirrors —
  do not infer equality from shared ownership or shared platform type.
- **Per-ref scope**: the level applies to every pushed ref (branches, tags,
  PR branches), not just the release line.
- **One-way derivation**: projections are produced downward at release time,
  human-triggered, by cherry-pick/replay/sanitise — never by merge, and never
  automatically synchronised upward.

Pre-push procedure follows directly from the level: **L0 push as-is; L1 —
check ADAPT against the intent test** (`references/trust-level-verification.md` §3):
keep concrete values when the remote's consumers pull the repo and fill in only
their own machine's differences, neutralise them when the remote's audience must
not learn reader-specific topology — L1's definition itself mandates no clip; **L2
strip INFRA** (CI/container/deploy config) and neutralise ADAPT if it is still
concrete; **L3 additionally** neutralise private identifiers and run a full-tree
leak grep. A repo whose dev copy is already clean collapses the ladder (all
remotes land at L2/L3 with zero pre-push work) — the model degenerating
naturally, not a special case bolted onto it.

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

#### The same-name trap (recurring misreasoning — settle the base before proposing it)

When our integration branch shares a *name* with an upstream branch — both called
`development`, say — the argument presents itself that "our work branches already sit on
the upstream development line, so we can open upstream PRs straight from them and save the
rebase". That reasoning is wrong, more than once voiced out loud:

- A shared name does not make two branches one lineage. Our integration branch carries our
  history, our INFRA and unrelated work; upstream's carries theirs. This is §1.1 pitfall 1
  generalised from remotes to branch names: equality is declared by pins, never inferred
  from a label.
- Using an integration branch as the PR carrier hands upstream precisely what the projection
  exists to clip away, which §4 fuse trio 3 forbids outright.
- "Saves a rebase" is a false economy. Cutting `up/<topic>-pr` from `up/main` and
  cherry-picking one PATCH segment costs minutes; a dirty PR gets closed, or forces a
  head-branch rewrite mid-review and burns the reviewer's trust along with it.

Tracking upstream's release cadence is a *scheduling* convenience. It never licenses sharing
a branch across the projection boundary: the carrier is always a short-lived `up/<topic>-pr`
cut from `up/main`, whatever the integration branch happens to be named.

### Projection B — towards remotes

Projection B is driven by the trust-level ladder of §1.1: **assign every
remote a level (and optional pins), then derive its content by clipping** —
there are no remote *types* to classify first. The legacy three-state names
(`identical` / `divergent` / `disclosure`) survive only as shorthand for the
relationship between two assigned levels; they are not properties of remotes:

| Shorthand | In level terms | What gets pushed | Detail owner |
|:----------|:---------------|:-----------------|:-------------|
| identical (mirror/DR) | same level + explicit `mirror-of` pin | whole slice, ref-by-ref (branches + tags follow in full); divergence is an incident | git-sync §2 |
| divergent | same or different level, **no** mirror pin | independent edit rights; push only what that remote's level discloses | git-sync §0 decision table |
| disclosure | adjacent levels across a public boundary (typically L1/L2 → L3) | clip per the level definition: neutralise ADAPT, then strip INFRA (the §1.1 ladder order — values first, config second); human-triggered at release time, never automatic; when history contains unclippable private traces, rebuild the projection history via squash/filter-repo — pushing the raw tower is forbidden | versioning «Three-Layer Content Architecture» + «Content classification for public» (its sanitisation checklist and diff-verification method are authoritative) |

Two assignment pitfalls that produced real misclassifications:

1. **Shared ownership ≠ same level.** Two remotes under one account can sit at
   different levels (one internal-mirror, one public-facing). Equality exists
   only when declared via `mirror-of`.
2. **A platform's usual role ≠ this repo's level.** "GitHub is always the
   public projection" is folklore, not a rule; some repos genuinely publish the
   identical slice everywhere (the collapsed-ladder case of §1.1 — zero pre-push
   work). Read the repo's AGENTS.md declaration, never infer from forge brand.

One project may carry several relationships simultaneously (e.g. Gitea↔GitHub
backup = mirror-pinned, Gitea↔upstream = Projection A, public release repo =
L3 clip) — **judge each pair independently, stack the rules**.

**Conflict arbitration**: if a remote is declared both `mirror-of X` and at a
level different from X, the definition is contradictory — resolve before
pushing. An automatically-synchronised public projection is never allowed (it
bets that INFRA never errs).

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
| `feat/*` and `fix/*` | work branches, cut from the branch they merge into, stackable | both sit in the PATCH layer and follow one promotion order — the prefix is a Conventional-Commits *type*, describing what the change does, not a topology. Reserve `fix/*` for defects and compatibility repairs that are plausible upstream backflow candidates, since those are exactly what Projection A carries; new capabilities stay `feat/*`. |
| `up/main` | branch, **primary forge only**, forks with an upstream | the upstream-tracking mirror: pure fast-forward of upstream, fetch-only, PR base; kept inside `up/` so it can never collide with `<dist>`/`main` |
| `up/<topic>` | short-lived branches | projection workspaces, discarded after use: `up/<topic>-pr` for upstream PRs; `up/public` = sanitised disclosure workspace derived from `<dist>`, pushed as the public remote's `main` |
| `upstream/v*` | **tag** (not a branch) | upstream snapshot anchor: resists accidental pushes and fetch-name collisions, and reads cleanly as `--onto` argument |

Relation to the three-tier branch model (branch-protection-model.md): that one
governs `main/development/feat/*` — the **internal development flow** of the
tower; this model governs `<dist>`/`up/*`/`upstream/v*` — the **cross-audience
projection surface**. They are orthogonal: `<dist>` *is* that very `main` in
non-fork repos, and merging `feat/*` into `<dist>` follows the other document.

**Work-branch prefixes follow Conventional Commits types** — the prefix names
what the change does, not a new topology. `feat/*`, `fix/*` and `refactor/*`
cover the common cases (a refactor is a PATCH-layer change with no release-line
impact of its own); other types (`chore/*`, `docs/*`, `ci/*`, `perf/*`) are
available for the same purpose. Any prefix the team uses rides the same
cut-from-and-merge-back-into rule — the two-branch skeleton does not grow a new
tier per prefix.

**Two PR-branch namespaces, two roles — do not merge them.** `up/<topic>-pr`
is *our* carrier, cut from `up/main` inside this repo and pushed for an upstream
PR. `pr/<topic>` (as in `git fetch fork pr/foo`) names a branch living on
someone *else's* fork, read-only from here — a fetch-side convention used when
adapting a community PR. The prefix tells you whose repo the branch is in:
`up/` = ours (push), `pr/` = theirs (fetch).

**A projection is a branch, never a directory.** Multi-remote and upstream
content differences are expressed by *clipping a branch* (§1.1) and pushing it
to the target remote — not by maintaining a `github/` vs `gitea/` copy of the
tree. Per-remote *directories* (as in `gitea/` or `github/` folders holding
platform skills) are unrelated: those are skill/tool organisation, not
projection artefacts, and must never be mistaken for where a remote's content
lives.

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
② What level does each remote sit at (L0–L3, §1.1)? → record per-remote
declarations `gitea: L2`, `github: L3 mirror-of gitea` etc. in AGENTS.md;
adjacent levels across a public boundary are Projection-B clip candidates
③ Must two remotes be byte-identical? → yes = declare the `mirror-of` pin;
no = independent editors (must state the reason, otherwise treat it as debt)
④ Which layers may the most-disclosed audience see? → the one-line layer ×
visibility table in AGENTS.md *is* the level assignment; clips follow it

## 6. Cadence

Schedule rebases between releases; after a rebase run the full build
verification before tagging a release; chasing novelty is optional — security
fixes outrank version freshness.
