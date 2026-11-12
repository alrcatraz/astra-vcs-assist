# Failure modes at initialisation

## Pitfalls

1. **LICENSE file must be standard text.** GitHub detects licences by matching the exact text. Even a single line of preamble (e.g. "This project uses the MIT licence") causes `NOASSERTION`. Put explanatory notes in `LICENSE.DUAL.md`.

2. **GPG email mismatch.** The email in the GPG key's `uid` must match `git config user.email` exactly. GitHub verifies commits against the email on the GPG key.

3. **`user.signingkey` without `commit.gpgsign true`.** Many users forget the second config. Without it, `git commit` doesn't auto-sign — you have to remember `-S` every time.

4. **First push without `push.autoSetupRemote true`.** Without this setting, `git push` on a new branch fails with "no upstream configured". Either set it or always use `git push -u origin HEAD`.

5. **Credential helper order matters.** Multiple credential helpers run in sequence. If GCM is listed first, it may prompt interactively before falling through to your script. Order them: custom script first, then GCM as fallback.

6. **`pull.ff only` prevents merge commits.** This avoids accidental merge bubbles during `git pull`. Use `git pull --rebase` when you intentionally need to rebase.

7. **Global vs per-repo identity.** If you work on multiple projects (personal, work, OSS), use per-repo config, never global identity. Global `user.name`/`user.email` is a common source of misattributed commits.

8. **A repo with no local identity silently inherits the global one — and `git config user.email` hides it.** Outside the repo, that read looks authoritative; it is the merged value. Ask `git config --local --get user.email`: empty output means this repository is drifting with whatever the global config happens to be, now and after the next change. The damage is invisible because the commit still succeeds and the forge still shows a name. At init, pin `user.name`, `user.email`, `user.signingkey`, `commit.gpgsign` and `tag.gpgsign` per repo, and record the identity and key id in `AGENTS.local.md` (see `readme-and-docs.md`) — the repo-local config is unversioned, so the written line is the only place a later agent can learn which identity the repository is meant to carry. Check across the fleet with one loop: any repo whose local email is empty is one global edit away from re-attribution.
