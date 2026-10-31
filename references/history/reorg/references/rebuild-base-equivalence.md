# Rebuild base selection — proving a clean-up lost nothing

A history reorg is a **content-preserving** operation. The commit graph changes;
the tree must not. Most of the verification advice in SKILL.md compares a branch
against its own former self, which is necessary but not sufficient — it is blind
to one specific, silent failure.

## The blind spot: rebuilding onto a different base

Cleaning up a feature branch normally rebuilds it against its own ancestor
(harmless). The dangerous variant is a rebuild whose base is a DIFFERENT ref than
the original branch was cut from:

- branch cut from `development`, rebuilt onto `main`
- branch cut from the private mirror, rebuilt onto the public one
- any "regenerate this branch cleanly from <other ref>" instruction

The branch's OWN content survives that move. What vanishes is whatever the
**original base** carried and the **new base** does not — and it vanishes with
no error, no conflict, and no trace in the branch-level diff.

Observed shape: a hardening commit (`ci: publish on release tags only, never on a
branch push`) lived on `development` but had never been merged to `main`. The
feature branch carried it by inheritance. Rebuilding the branch on `main`
produced a clean-looking history that had silently **reverted the hardening** —
the reorg restored the weaker, pre-hardening behaviour in the workflow file,
which is exactly the class of regression (an image publishing off a branch push)
that the hardening existed to prevent.

## Verify against both references

```bash
# a) branch content preserved — the usual check
git diff <original-branch> <new-branch> --stat
#    empty  ⇒ no content lost by the rebuild
#    non-empty ⇒ READ IT. It is either your intended reorg or a silent revert.

# b) commits the OLD base had that the NEW base does not — the blind spot
comm -23 <(git log --format=%H <old-base> ^<new-base> | sort) \
         <(git log --format=%H <new-branch> | sort)
#    every hit is a commit the rebuild dropped; cherry-pick the ones that belong
```

Step (b) is the one that matters after a cross-base rebuild, because a commit
that was never on the branch cannot appear in the branch-level diff — the diff
in (a) will read "identical" while the dropped work is simply gone.

## Reading a non-empty diff

Do not treat `--stat` output as noise to wave through. A non-empty diff is the
ONLY signal that catches a dropped sibling change, and it is three different
things depending on content:

| Diff shows | Meaning |
|:-----------|:--------|
| files you intentionally reworked | the reorg — expected |
| a file reverted to its pre-hardening form | **silent revert — fix before pushing** |
| an unrelated file you never touched | the rebuild pulled in or dropped foreign work |

When the pre-cleanup branch was based somewhere other than the rebuild target,
the base is part of the comparison — check it explicitly rather than assuming
the branch is a strict subset of its new parent.

## Same rule, other surfaces

The generalisation, which also applies to filter-repo work and lineage
retirement: **prove preservation, never assume it from the operation's success.**
A rewrite that exits 0, a rebuild with no conflicts, and a branch that "looks
right" are all statements about the operation, not about the content.
