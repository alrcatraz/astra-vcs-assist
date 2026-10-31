> Credential handles in this file (`<...-password>`, `<...-secret>`) resolve from KeePassXC; see `credential-store-management` for the lookup order. Never inline the value.

# References index

All 8 reference files of `git-history-reorg`.

**Topical references**
- `decision-records.md` — Decision records — past rewrites: **Context.** A deliberately-public repo carried internal IPs, hostnames and a plaintext credential (`<fleet-sudo-password>`, plus an 8-
- `filter-repo-scoping-traps.md` — git-filter-repo: choosing the right rewrite mode: `git filter-repo` exposes several modes that look interchangeable and are not.
- `post-rewrite-propagation.md` — Post-rewrite propagation and the fleet-wide sweep: A history rewrite is finished when EVERY copy and every SIBLING REPO is clean — not when the pushed branch is.
- `rebuild-base-equivalence.md` — Rebuild base selection — proving a clean-up lost nothing: A history reorg is a **content-preserving** operation.
- `remote-file-editing.md` — Editing files on a remote working machine over SSH: scp-to-temp+mv write channel with three byte-verify checkpoints; base64 read round-trip; anchor preflight on decoded text (grep -Fxc lies); staged-vs-worktree diff visibility; ssh gate-phase handling.
- `staging-hygiene.md` — Staging Hygiene in a Shared Working Tree: Rule set for committing in a repo that OTHER workers also edit — a skills library, a dotfiles repo, a shared checkout on
- `two-copy-state-diagnosis.md` — Reading a two-copy repo without misdiagnosing it: A dev checkout and a production/deploy copy of the same repo hold *different* honest states, and each reads as a fault f
| `filter-repo-removal.md` | every variant of removing a term/file/artefact from history (cases A–E, mechanics) |
- `public-repo-sanitisation.md` — sanitising a public repo while authoring it
- `squash-before-push.md` — squashing a feature's local commits before pushing
- `rewrite-recipe-and-traps.md` — the end-to-end rewrite recipe plus the traps it turned up
