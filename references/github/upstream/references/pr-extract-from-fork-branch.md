# Extracting a PR branch from a diverged fork

When the feature lives on a long-lived fork branch (dev/main with fork-only infra,
branding, and several features), open the upstream PR from a **fresh branch off
upstream main** and bring over only the files belonging to THIS PR's feature.
Never push the fork branch itself — it drags private history into a public PR.

## Procedure

1. Fetch upstream shallow (`git fetch upstream --depth=50`) so `merge-base` resolves
   and `git diff --stat upstream/main...dev` shows exactly what the fork added.
2. `git checkout -b feat/<thing> upstream/main`, then bring the feature's files:
   `git checkout dev -- <files>`. File lists come from the stat above minus
   fork-only infra (flake.nix/lock, CI, branding docs, local AGENTS notes).
3. **Check default values of every build flag your code reads.** Fork branches often
   flip defaults via `--dart-define`; the PR must ship upstream-neutral defaults
   (opt-in) so an ordinary upstream build is unchanged. Grep `bool.fromEnvironment`
   / `defaultValue:` in the brought-over files.
4. Commit with `-c user.name/-c user.email` for the PR identity and match upstream's
   signing convention (check contributors first: `git log upstream/main --format="%h %G? %s"`).
   The identity MUST be the user-chosen one for that repo (personal vs public GitHub
   email) — NEVER an agent-branded address like angelia@<lab-domain>; no agent
   address has ever been authorized for public git metadata. If fork history already
   carries agent-branded authorship, rewrite it out before any push.
5. Verify the extracted branch BUILDS standalone before pushing — the feature may
   have quietly grown dependencies on other fork features:
   - compile errors naming symbols you never touched = missing shared dependency;
     bring that file too if it is generic (e.g. an enum helper), or split the PR.
   - run the analyze/build inside the repo's own devShell flake; when the branch
     intentionally excludes flake.nix, keep it on disk untracked and use
     `git add -N flake.nix flake.lock` so Nix sees it without staging it into the
     commit; `git reset flake.nix flake.lock` before committing.
6. Re-run the on-device acceptance suite against the PR-built APK with the flags set
   the way upstream users would get them (feature on, siblings off). Assert the
   registry/behaviour matches ONLY this feature — extra entries mean fork defaults
   leaked into the branch.
7. Local build workarounds (e.g. a disabled upload task) stay UNCOMMITTED — reapply
   after checkout, revert before any commit that goes public.

## Scope rules (user)

- One PR = one feature. If the fork also carries features someone else already PR'd
  upstream, or adjacent features sharing plumbing, strip them from the branch even
  when the code is entangled — behaviour-neutral defaults are the minimum bar.

**Re-applying your commits onto a much-advanced main is CHERRY-PICK, not
`git checkout dev -- <files>`.** When the feature lives as a SERIES of commits
already reviewed locally (and the fork branch has drifted far past upstream, or
has retracted work you must not drag in), do not copy the working tree — replay
the commits:

```bash
git fetch origin main && git checkout -b pr/<thing> origin/main
for c in <sha1> <sha2> <sha3>; do git cherry-pick $c; done
```

Expect CONFLICTS — that is normal, not a sign of a wrong plan. Resolution
policy, in order:

1. **HEAD side empty (upstream has no such code) → take the incoming side.**
2. **Both sides carry logic (upstream rewrote the area, your change builds on
   the old structure) → MERGE BOTH, then re-verify the semantics.** A merge can
   silently leave your helper DEFINED but never CALLED (the call site stayed
   upstream's), or a duplicated line with a dangling brace — re-read the merged
   function body, not just the conflict markers.
3. **Re-run the tests you brought with EACH commit before `--continue`.** A
   green suite at the end does not excuse a broken intermediate.
4. **A missing prerequisite commit surfaces as a TEST FAILURE, not a conflict.**
   If your commit's tests fail because a helper/constant never exists, check
   whether the commit they depend on was left out of the cherry-pick list
   (`git log --oneline -S '<symbol>' <branch>` finds it). Cherry-pick the
   prerequisite as its own commit; do not rewrite the dependent commit to inline
   it.

After the full series: run the touched-file test set + project-wide
`tsc --noEmit`, and judge only NEW errors in files you touched (upstream's own
files may carry pre-existing errors — baseline against `origin/main`).

**The SINGLE-SQUASH-COMMIT graft case.** When the PR head is one squash commit
(not a series) and the branch has diverged from upstream main, cherry-pick that
one commit onto a fresh branch from current main:

```bash
git fetch upstream main
# Check the clone isn't shallow first — shallow clones make merge-base lie
# (see multi-pr-review-and-rebase-repair.md §0d: unrelated-histories false
#  positive, whole-tree diff instead of feature diff)
git rev-parse --is-shallow-repository   # true → git fetch upstream main --unshallow first
git checkout -b pr/<graft> upstream/main
git cherry-pick <squash-commit-sha>     # will conflict in the neighbour-renovated files
```

**The neighbour-renovation conflict is resolved by grafting INTO upstream's new
structure, not by keeping your old copy in the conflict hunk.** When upstream has
moved your target functions to a new module (e.g. `web_server.py` helpers moved
into `web_server_boundary.py`), the conflict has two blocks per file — one for
the import/re-export area, one for the function bodies:

- **Import block**: take upstream's re-export line (`from new_module import ...`)
  and keep only YOUR new-module imports (e.g. `from your_new_helper import ...`) —
  drop your local duplicate definitions that upstream now owns.
- **Function body block**: if upstream's version in the new module is SINGLE-ARG
  and yours adds COLLECTION support, you must **patch the new module itself**
  (add `isinstance(x, str): x={x}` normalization inside upstream's function) and
  take upstream's delegation call-site in the old file — do NOT keep your old
  full-function copy in the conflict hunk.

After resolving: `py_compile` each touched file, verify import chains
(`grep _SYMBOL <new_module>` for every symbol the old file still imports), and
run the project's canonical test runner (`scripts/run_tests.sh`, NOT
direct `.venv/bin/pytest` — see SKILL.md §4.1a) on the touched test files before
`cherry-pick --continue`.

**`git commit --amend -S --no-edit` keeps the OLD message — including any word
you meant to remove.** After a desensitisation pass (device names, fleet terms),
a later amend reuses the message verbatim and silently reintroduces the stripped
word into commit text even though the working tree is clean. Re-verify with
`git log <base>..HEAD --format='%B' | grep -i <term>` after EVERY amend, not once
at the start.

**Labelled fix sets (A/B/C …) are LOCAL shorthand only.** Do not carry the
letter labels into the PR body — a label can collide with a previously-retracted
patch of the same letter and reads as confusion to outsiders. Describe each
change by what it does. The PR text speaks as the user, technically: no internal
progress, plans, agent orchestration, private fork/device names (Contribution
purity pitfall in SKILL.md) — sweep commit messages (`git log --format='%B'`),
the code diff (`git diff <base>...HEAD`), AND the PR body file, once more after
any amend.

**A delta re-review can find a real defect in the prior round's FIX, not just in
the original code — fail-closed applies to delta rounds too.** After a blocking
finding is fixed, the re-review may show the fix incomplete (e.g. two parallel
counters where only each branch's OWN counter was reset, leaving the other
stale so the failure mode persists through it). Fix every instance of the
pattern, re-amend, re-run tests, re-review — never declare pass on your own
verification of someone else's finding.

- The PR text speaks as the user, technically: no internal progress, plans, agent
  orchestration, private fork/device names (see Contribution purity pitfall in SKILL.md).
