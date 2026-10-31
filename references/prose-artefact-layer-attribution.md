# Prose Artefact Layer Attribution — deciding what belongs at the target level

The ladder (§1.1 of `tower-model.md`) assigns each **remote** a level. This
file answers the complementary question the ladder presupposes but does not
settle: given the content itself, **which of it belongs at that level?** It is
the working method for the disclosure clip (Projection B), and it governs any
**prose artefact** — a skill, a README, an AGENTS file, a docs/ page. Structured
config (CI files, compose manifests) needs no such method: layer membership is
already legible from its path and shape, which the fuse trio relies on.

## 1. The question, stated precisely

Do not ask *"is this suitable for the public?"* — that presumes L3 and answers
only one level. Ask, per piece of content:

> **Should this information be present at the target trust level?**

The same sentence gets different answers per level, and that is the point:

| Content | L0 · L1 (authority / private) | L3 (public) |
|:--|:--|:--|
| Fleet deployment specifics (own subnets, node names, service ports) | belongs — the team consumes it | does not belong — meaningless to a generic reader |
| A commit signature / author field | belongs — provenance metadata | belongs — provenance metadata |
| A concrete value inside a generic example (a sample IP in a YAML template) | belongs as a concrete value | belongs, but **generalised** to a placeholder |

Two consequences follow. First, a signal that reads private is not by itself a
leak — a signature belongs at every level, so replacing it with a placeholder
*corrupts* the artefact rather than sanitising it. Second, a value absent from
any "sensitive pattern" list can still be a leak, because the test is
membership in the level, not resemblance to a pattern.

## 2. Three verdicts, and the one that is usually missed

For each piece of content, exactly one of:

- **Remove** — it does not belong at the target level. Delete it outright.
- **Generalise** — it belongs, but its *concrete value* is level-specific.
  Replace the value, keep the structure.
- **Keep** — it belongs as it stands. No edit (signatures, generic prose).

**Removal is the verdict this method exists to produce.** Value-level search
and replace only ever reaches the second verdict; it cannot remove a passage,
so a clip driven by a pattern list leaves the *skeleton* of out-of-level content
in place — a deployment log with its values blanked is still a deployment log,
still disclosing what we run and how, in a form no placeholder can neutralise.
When a passage as a whole is out-of-level, the verdict is Remove, not Generalise
repeatedly until little is left.

## 3. Method — read the record, then judge

The unit of judgement is the **record**, not the matched string. A clip
performed by scanning for values and editing each hit in isolation produces two
failures: it generalises content that should have been removed, and it generalises
metadata that should have been kept.

Procedure:

1. **Read the whole record first** — the entire file, or for a commit the entire
   message (subject *and* body), before deciding anything. A grep hit is a
   pointer to a passage, never a unit of work.
2. **Walk the passage and ask of each segment**: should this be at the target
   level? A file is usually **mixed** — generic method in one section,
   team-bound specifics in another — so the verdict is taken per segment, not
   per file.
3. **Apply the verdict** — remove / generalise / keep, per §2.
4. **Re-read the result as a reader at the target level**: does it still read
   as a coherent document, and does any sentence now presuppose something that
   was removed? Removing a passage whose removal leaves a dangling reference is
   an incomplete clip.
5. **Sweep, don't spot-check** — after editing, run the whole-tree scan
   (`scripts/scan-tracked-values.py`) over the **projected tree**, not just the
   files you touched: generalisation is per-value, so a value you fixed in one
   file can survive in another. See §6.

### When in the lifecycle this runs

The pass is not a release-only activity — content that enters out-of-level is
easier to stop at the point of writing than to clip later. It applies at every
stage of the artefact lifecycle (create / maintain / release / archive); the
stage-by-stage hooks are listed in `this repository` → `references/git/init/` («The AGENTS pair
across the git lifecycle») and, for skills, in `skill-ecosystem` (its
create/update/archive gates).

## 4. File-level declaration vs per-segment judgement

Two mechanisms, different scopes — do not reach for the wrong one:

- **Per-segment judgement (§3) is the general case.** Most artefacts are mixed;
  the verdict is taken passage by passage. There is no file-level label that can
  express "this file is generic except for one deployment paragraph", so the
  per-segment pass is not optional.
- **File-level declaration is the exception**, for the minority of artefacts
  that are *entirely* of one level: a pure internal decision draft that should
  never be projected at all, or a config that is generic throughout. Declare
  these once rather than re-deriving them every release. The carrier is
  **`AGENTS.local.md`** — the private local layer, disclosed only to ≤ L1 remotes
  (git-sync §0 keys the push on this file's presence/absence per level; it must
  be absent from every ≥ L2 tree). A *public* `AGENTS.md` may carry at most a
  general path-pattern allowlist (e.g. "platform skills may name their own
  forge"); it must never enumerate the concrete files that are held back, since
  that enumeration is itself the disclosure it exists to prevent.

  A file-level declaration is a *shortcut for a settled case*, never a
  substitute for reading: a file declared generic that later grows an
  out-of-level paragraph is a leak the declaration hides.

## 5. Where the layer boundaries fall on prose

`tower-model.md` §1 defines the four layers structurally (BASE/PATCH/ADAPT/INFRA).
Prose has no such structure, so map each passage onto the layer whose *clip
rule* it follows:

- **ADAPT-shaped** — localisation that varies per deployment: hostnames, private
  addresses and subnets, service ports, machine names, credential references or
  entry names. These leak reader-specific topology. At L3 they are either
  generalised (when the surrounding text is a generic example) or removed (when
  the surrounding text is team-bound narrative).
- **INFRA-shaped** — environment-bound plumbing described in prose: how *our*
  CI runs, *our* deploy layout, *our* service inventory, maintenance history.
  Stripped at L2, removed at L3.
- **PATCH-shaped** — the substantive, portable content: the method, the
  mechanism, the fix. This is what the artefact exists to deliver and survives
  at every level.
- **Provenance** — signatures, author fields, licence notices. Not clipped at
  any level; treat an edit to these as a defect.

When a passage resists this mapping, the tension is real and belongs to the
owner: per `trust-level-verification.md` §4, state the affected
definitions and let the owner correct the model rather than forcing a fit
mid-task.

## 6. Verification — the whole projected tree, by object

After clipping, verify from **artefact objects**, not from the files you
remember editing:

- **Sweep the projected tree**: `scripts/scan-tracked-values.py` walks tracked
  files and reports file:line per pattern. Run it on the tree about to be
  pushed, not on the source.
- **History and side refs carry the same content.** A tag, an unmerged PR ref,
  or a branch tip from before the clip still serves the old bytes; a project
  whose *tip* is clean can still disclose through `refs/tags/*` and
  `refs/pull/*`. Enumerate **all** refs, and for a real history rewrite scan
  every reachable object (`git rev-list --objects --all` → `cat-file --batch`),
  because content introduced inside a merge commit is invisible to
  `git log -S`.
- **Commit messages are part of the record** (§3.1). A clip that edits file
  content but leaves the message untouched leaves the leak in the message.
- **Confirm both directions** — the projected tree carries no out-of-level
  content, *and* no in-level content was lost to an over-eager clip (a
  generalised signature or a blanked generic example).

## 7. Pitfalls

1. **Generalising instead of removing.** The dominant failure: a pattern-driven
   clip cannot delete, so out-of-level passages survive as skeleton. Ask the §2
   verdict explicitly; do not let "what placeholder fits here?" stand in for it.
2. **Editing values without reading the record.** A hit is a pointer. Judging
   it in isolation generalises what should have been removed and mangles what
   should have been kept.
3. **Clipping metadata.** Signatures, author fields, notices — a clip that
   reaches these has misread "sounds private" for "is out-of-level".
4. **Treating a pattern list as the definition of private.** Any list is
   incomplete by construction; the test is level membership (§1), and the
   list only accelerates the common hits.
5. **Clipping the tip only.** Tags, PR refs and merge-introduced content
   survive a branch-only clip (§6).
6. **Assuming a file-level declaration covers its later growth.** A declared
   generic file that gains a team-bound paragraph is a leak the declaration
   conceals; the per-segment pass is what catches it.

## The disclosure judgement pass (folded in from the reorg block)

Before any rewrite rules are written, decide **what to do with each passage**. Token-level
replacement is the last step, not the method: a value-level search can only ever rewrite, so
it can neither delete an out-of-level passage nor tell you that it should have been deleted.
Choosing the wrong verdict is how a "cleaned" repo still discloses what we run and how.

Applies to any **prose artefact** — skill, README, AGENTS file, docs page. Structured config
(CI files, compose manifests) is decided by path and shape instead, which the tower model's
fuse trio relies on.


Do not ask *"is this suitable for the public?"*. That presumes the target is L3 and answers
only one level. Ask, per passage:



| Content | L0 / L1 (authority / private) | L3 (public) |
|:--|:--|:--|
| Signature / author / committer field | belongs — provenance metadata | belongs — provenance metadata |
| A concrete value inside a generic example (a sample IP in a YAML template) | belongs as the concrete value | belongs, **generalised** to a placeholder |

Two consequences:

- **A signal that reads private is not by itself a leak.** A signature belongs at every level,
  so replacing it with a placeholder *corrupts* the artefact rather than sanitising it.
- **A value absent from any "sensitive pattern" list can still be a leak.** The test is
  membership in the level, not resemblance to a pattern; every list is incomplete by
  construction and only accelerates the common hits.

## 2. Three verdicts — exactly one per passage

| Verdict | When | Action |
|:--|:--|:--|
| **Remove** | It does not belong at the target level | Delete the passage outright |
| **Generalise** | It belongs, but its concrete value is level-specific | Replace the value, keep the structure |
| **Keep** | It belongs as it stands | No edit |

**Removal is the verdict this method exists to produce.** A pattern-driven clip reaches only
the second row, so an out-of-level passage survives as a **skeleton** — a deployment log with
its IPs blanked is still a deployment log, still disclosing what we run and how, in a form no
placeholder neutralises. When a passage as a whole is out-of-level, the verdict is Remove,
not repeated Generalise until little is left.


The unit of judgement is the **record**, not the matched string. Scanning for values and
editing each hit in isolation produces both failure shapes at once: it generalises content
that should have been removed, and it generalises metadata that should have been kept.

1. **Read the whole record first** — the entire file; for a commit, subject *and* body,
   before deciding anything. A grep hit is a pointer to a passage, never a unit of work.
2. **Walk it passage by passage.** A file is usually **mixed** — generic method in one
   section, team-bound specifics in another — so the verdict is per segment, never per file.
3. **Apply the verdict** (remove / generalise / keep).
4. **Re-read as a reader at the target level.** Does it still read as a coherent document,
   and does any surviving sentence presuppose something now removed? A removal that leaves a
   dangling reference is an incomplete clip.
5. **Sweep, do not spot-check** — after editing, scan the **whole projected tree**, not just
   the files touched: generalisation is per-value, so a value fixed in one file can survive
   in another.


- **Per-segment judgement (§3) is the general case.** Most artefacts are mixed, and no
  file-level label can express "generic except for one deployment paragraph" — so the
- **File-level declaration is the exception**, for the minority of artefacts that are
  *entirely* of one level: a pure internal memo that should never be projected at all, or a
  config that is generic throughout. The carrier is **`AGENTS.local.md`** — the private local
  layer, disclosed only to ≤ L1 remotes (git-sync keys the push on this file's
  presence/absence per level; it must be absent from every ≥ L2 tree).

  **A public `AGENTS.md` must not enumerate the withheld files.** Listing "these paths may
  carry instance facts" on the public side *is itself* the disclosure the list exists to
  prevent — it tells every reader that a private face exists and roughly where. A public
  AGENTS file may carry at most a generic standing rule ("anything not listed must be clean
  before public push") and generic path *patterns*; the concrete names, exemptions and
  exclusion lists live in `AGENTS.local.md`. Both files are auto-injected, so a rule placed
  in the local half still reaches the agent — there is no reason to publish the list.

  A file-level declaration is a shortcut for a settled case, **never a substitute for
  reading**: a file declared generic that later grows an out-of-level paragraph is a leak the
  declaration hides.


The tower model's four layers are defined structurally (BASE / PATCH / ADAPT / INFRA). Prose
has no such structure, so map each passage onto the layer whose *clip rule* it follows:

| Shape | Content | Treatment |
|:--|:--|:--|
| **ADAPT** | Localisation that varies per deployment: hostnames, private addresses and subnets, service ports, machine names, credential references and vault entry names | L3: generalise when the surrounding text is a generic example; **remove** when it is team-bound narrative |
| **INFRA** | Environment-bound plumbing described in prose: how *our* CI runs, *our* deploy layout, *our* service inventory, maintenance history | stripped at L2, removed at L3 |
| **PATCH** | The substantive portable content: the method, the mechanism, the fix | survives at every level — this is what the artefact exists to deliver |
| **Provenance** | Signatures, author fields, licence notices | not clipped at any level; editing one is a defect |

When a passage resists this mapping, the tension is real and belongs to the owner: state the
affected definitions and let the owner correct the model rather than forcing a fit mid-task.

## 6. Pitfalls

1. **Generalising instead of removing.** The dominant failure: a pattern-driven clip cannot
   delete, so out-of-level passages survive as skeleton. Ask the §2 verdict explicitly; never
   let "what placeholder fits here?" stand in for it.
2. **Never `reset --hard` a workspace to sync it after the rewrite — it destroys other
   people's uncommitted work.** A workspace (the bridged private copy, or a second clone)
   routinely carries in-flight edits the rewritten source does not have. Before re-syncing,
   run `git status --short` and `git diff --stat` there: any modified file NOT in your change
   set is someone else's work — stash-and-pop or merge, never discard. When the two copies
   have **diverged** (each holds commits the other lacks), `merge --ff-only` refuses by
   design and an automatic sync is the wrong move: surface the divergence with both heads
   and let the owner resolve it, because the extra commits are unowned by you.
3. **Editing values without reading the record.** A hit is a pointer. Judging it in isolation
   generalises what should have been removed and mangles what should have been kept.
4. **Clipping metadata.** Signatures, author fields, notices — a clip that reaches these has
   misread "sounds private" for "is out-of-level".
5. **Treating a pattern list as the definition of private.** The list is incomplete by
   construction; the test is level membership (§1).
6. **Clipping the tip only.** Tags, PR refs and merge-introduced content survive a
   branch-only clip.
7. **Assuming a file-level declaration covers later growth.** A declared-generic file that
   gains a team-bound paragraph is a leak the declaration conceals; only the per-segment
   pass catches it.
8. **Judging only at release time.** Attribution is not a release-only pass — content that
   enters out-of-level is cheaper to stop at the point of writing than to clip later. Run the
   per-segment pass when content is created, whenever an edit adds a passage, and when an
   artefact is archived — archiving or `git rm`-ing a file does **not** remove its content
   from history, so an artefact that reached a public remote still discloses after it is moved
   out. The stage-by-stage hooks belong in the fix for the affected class: for skills,
   `skill-ecosystem`'s create/update/archive gates; for any repo artefact, the git-init
   lifecycle table.

## 7. Verification, from artefact objects

Verify what will be published, not the files you remember editing:

- **Sweep the projected tree** with `scripts/scan-tracked-values.py` (in `this repository`),
  run on the tree about to be pushed rather than on the source.
- **All refs, all reachable objects.** A tag, an unmerged PR ref, or a branch tip from before
  the clip still serves the old bytes; a clean tip can still disclose through `refs/tags/*`
  and `refs/pull/*`. For a real history rewrite scan every reachable blob
  (`git rev-list --objects --all` → `cat-file --batch`) — content introduced inside a merge
  commit is invisible to `git log -S`.
- **Commit messages are part of the record** (§3.1). A clip that edits content but leaves the
  message untouched leaves the leak in the message; `--replace-text` does not touch messages.
- **Confirm both directions** — the projected tree carries no out-of-level content, *and* no
  in-level content was lost to an over-eager clip.
