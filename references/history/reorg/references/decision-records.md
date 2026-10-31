> Credential handles in this file (`<...-password>`, `<...-secret>`) resolve from KeePassXC; see `credential-store-management` for the lookup order. Never inline the value.

# Decision records — past rewrites

> Recorded at closure. Context → options → chosen → cost of rejected. Read BEFORE
> deciding a fresh rewrite's shape or a post-push residual's fate.

## A public-repo leak cleanup (an earlier campaign) 

**Context.** A deliberately-public repo carried internal IPs, hostnames and a
plaintext credential (`<fleet-credential>`, plus an 8-device password table) across a 127-commit
history and 4 annotated tags.

**Options.**
- (A) `filter-repo --replace-text` + `--replace-message` over the whole history.
- (B) Abandon history: orphan rebuild, one root commit.
- (C) Clean only the tip, leave history as-is.

**Chosen:** (A). The leaking content had to REMAIN in history — the repo's value is
its continuity — so a rules file that exhausts every leak class was affordable.

**Cost of rejected options.** (B) costs public commit granularity (N → 1) and forces
re-tagging every release on the new root; (C) leaves every clone a live fetch of the
plaintext credential.

**Also chosen:** triage BEFORE bulk replace — three whole files were internal
decision memos (`storage-compute-layering.md`, `user-stores.md`,
`astra-sre/deployment.md`) that no string-replacement could redeem; they were deleted
plus their 6 referencing lines, as a separate commit on top of the rewrite. Bulk
replace without file triage leaves a "clean-looking" file whose entire subject is
still internal.

## Post-push `refs/pull/*` residual 

**Context.** After branches + tags were rewritten on both forges, the server-side PR
snapshot refs (`refs/pull/*`) still served the old leaky commits — a fifth fetch path
(see safety net 6 in SKILL.md).

**Options.**
- (A) Contact forge support.
- (B) Delete + recreate the public repo.
- (C) Accept the residual — **and explicitly decline credential rotation (C2)**.

**Chosen:** (C), both halves, decided by the user after being told plainly that with a
plaintext password reachable, rotation was the only remaining real mitigation.

**Cost of rejected options.** (A) loses weeks to support tickets and may not even
apply to `refs/pull`; (B) loses stars/issues/PR history permanently.

**Lesson.** The residual must be reported as *"leak reachable, credential NOT
rotated"* — never softened to "handled". A rewrite that leaves a live plaintext
secret reachable has reduced exposure, not removed it; say which.
