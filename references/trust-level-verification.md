# Trust-Level Verification — measuring a remote's real level

A trust level (tower-model §1.1) describes what content a remote carries. The
level written in AGENTS.md and the content actually pushed drift apart, because
either side can change without the other. Verify the level from content; never
inherit it from a label.

## 1. When

- Declaring a level for a newly created project or a newly added remote.
- Re-labelling an existing remote (a `gitea: L2` moved to another level, a
  GitHub repo promoted from private to public, a level claimed from platform
  type).
- Pre-push review of a repo whose stated level looks inconsistent with what it
  actually carries.

## 2. Measure, don't infer

1. Enumerate the values the ladder acts on, in ladder order — ADAPT first
   (forge domains and hostnames, machine-specific paths, private IPs and internal
   endpoints, credential references), then INFRA (CI/deploy configuration files),
   then private identifiers. The order matters: it is the clip sequence, and a
   scan that skips straight to INFRA will report a repo as clean while its
   reader-specific values are still present.
2. List which tracked files carry each one — run `scripts/scan-tracked-values.py`
   from this repo (it walks `git ls-files` and reports file:line per pattern).
   Hand-rolling the scan in a shell pipeline fails silently once the pattern has
   alternation: quoting of `|` and `\d` breaks differently in `sh`, `bash` and
   inside an f-string, so write the pattern to a `.py` file first and run that.
3. Derive the level from the result, in ladder order (values first, then
   INFRA, then identifiers — matching §1.1's clip sequence):
   - **L0** — the full tower, real values intact (dev copy / authority);
   - **L1** — private tier: INFRA intact, ADAPT kept concrete for fleet consumers
     (neutralise only if the repo's consumers need it — the intent test, §3);
   - **L2** — INFRA stripped (ADAPT neutralised at L1 only if the repo chose to; otherwise neutralise it here for cross-org exchange);
   - **L3** — private identifiers stripped + clean leak grep.
   Two traps: (a) a repo with **no INFRA files** has L0 and L1 *content-identical*
   — L0 is reserved for the authority/dev copy; a remote carrying that same
   content declares L1 (the intent test, §3 decides the rest); (b) real values
   present does **not** by itself mean L0 — a repo that deliberately keeps ADAPT
   concrete for its fleet also sits at L1.
4. Compare against the AGENTS.md declaration. A mismatch is a **finding**, not
   an obstacle — report the inventory and let the owner decide whether the
   declaration, the content, or the taxonomy is wrong.

## 3. The intent test (last, and it overrides aesthetics)

The declared level must be the one that makes the intended consumer work. A
repo meant to be pulled on a fresh machine where each agent fills in its own
values **wants concrete values preserved** — neutralising them to satisfy a
definition destroys the delivery the repo exists to provide. Judge the level by
who consumes the content and what they must be able to do with it, not by which
label reads as more careful.

Allowlists are part of this: files explicitly exempt from sanitisation (an
`AGENTS.md` publication allowlist, a platform skill that must name its own
forge) keep the repo at the level their content actually is, regardless of how
tidy a lower level would look.

## 4. When the model itself looks wrong

If the ladder's ordering or boundaries seem inconsistent with how content
really is sensitive, state the tension and the affected definitions, then let
the owner decide the correction — a trust-model edit is a design decision,
never a cleanup step taken mid-task. Once corrected, rewrite the affected
definitions in place in `references/tower-model.md` and every place that quotes
them (pre-push procedures, disclosure rows, remote-declaration bullets); grep
for the old wording across the repo, because level definitions are quoted by
value in several files.
