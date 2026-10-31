---
name: github-pat-lifecycle
description: "Use when handling GitHub PATs. Manual creation only."
version: 0.1.0
author: alrcatraz
metadata:
  hermes:
    tags: [github, pat, ci-secrets, gitea, authentication]
triggers:
  - "GitHub PAT"
  - "ghp_ token 401"
  - "Bad credentials"
  - "create personal access token"
  - "nix flake github rate limit"
  - "Gitea actions secret github"
---

# GitHub PAT lifecycle

## First question: is a PAT actually needed?

Most CI-on-GitHub needs are covered without any personal token:

- **Push/pull packages for the SAME repo (ghcr.io)**: workflow `GITHUB_TOKEN` +
  job-level `permissions: packages: write` — implicit package creation works, no PAT.
- **Flake inputs / tarballs from public repos**: anonymous HTTPS, no token (see below).
- **API writes to your own repos from outside CI**: this is where a PAT earns its keep.

Before asking the user to create one, enumerate what the pipeline actually does — a
PAT collected "just in case" becomes a revocation-audit liability later.

## Hard rule: never automate PAT creation

Ask the user to create the PAT manually (classic, `public_repo` scope suffices for
reading public-repo tarballs) and deliver it via KeePassXC or direct message.
Automated web-form POST creation is a dead end: the plaintext appears exactly once
on the success response page, sudo-session validity after TOTP is unstable (POST
silently returns 200 form-page = not created), and every blind-created token ends up
an unusable 401 husk that must be individually deleted. Each retry multiplies junk
tokens on the account — the user has flagged this as dangerous.

## The invalid-credential lockout trap (diagnosis-critical)

GitHub temporarily rejects ALL authentication attempts for an account after several
requests with invalid credentials in a short window — including ones with VALID tokens
(401 `Bad credentials` even on `/rate_limit`, and authenticated codeload fetches flip
to 404 while anonymous stays 200). Therefore:

- One 401 on a freshly-supplied token does NOT mean the token is bad. STOP hammering,
  wait out the cooldown (minutes), then re-verify once.
- Batch verifications: prefer a single check over trial-and-error across header
  variants; each failed probe extends the lockout.
- Distinguish: valid token + lockout = temporary asymmetry that self-heals; revoked
  token = persistent failure after cooldown AND the web UI shows it deleted.
- **A history rewrite on any repo the token touches can revoke it.** GitHub's secret
  scanning acts on rewritten pushes: a force-push that rewrites commits where the token
  existed (or that rewrites the repo while the token is in use as a CI secret) makes the
  token go invalid — typically WITHOUT the cooldown asymmetry above. Symptom: the CI job
  fails at its very first step (checkout), not at the step that uses the token, so it
  reads like a broken pipeline rather than a dead credential. **Check the token's
  liveness before debugging any post-rewrite CI failure** — one `Bearer` `/user` call
  splits "pipeline broken" from "credential gone" in seconds.

## Verification recipe (one shot)

```bash
# value arrives via stdin / 600-perm temp file; delete after use, never echo
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $PAT" https://api.github.com/user
# 200 = alive. Scope check (only if needed, adds one request):
curl -sI -u "user:$PAT" https://api.github.com/user | grep -i x-oauth-scopes
```
Basic auth (`user:token`) works where Bearer 401s during a lockout — useful as a
secondary signal but do not treat the discrepancy as a property of the token itself.

## Wiring into Gitea Actions (the common consumer here)

- **Gitea forbids secret names starting `GITHUB_`/`GITEA_`** (reserved prefixes; PUT
  fails 400 "invalid variable or secret name"). `${{ secrets.GITHUB_TOKEN }}` in a
  Gitea workflow resolves to the runner's git-only task token — useless against real
  GitHub. Store the real PAT under another name, e.g. `NIX_GH_TOKEN`.
- Set via `PUT /api/v1/repos/<o>/<r>/actions/secrets/<NAME>` body
  `{"name":...,"data":...}`, basic auth with the Gitea login password from KeePassXC
  entry ``<forge-credential-entry>` (resolve the KeePass path from `credential-store-management`; the entry name names a machine, so it is not written here)`. Reusable helper on the forge host:
  `~/bin/set-gitea-secret.py <NAME>` (reads value from stdin, no disk plaintext).
- For nix flake lock resolution add to NIX_CONFIG:
  `access-tokens = github.com=${{ secrets.NIX_GH_TOKEN }}`.
  **But check first whether it's needed at all**: if every locked input URL in
  `flake.lock` points at a PUBLIC repo (nixpkgs/flake-utils/systems), anonymous
  codeload fetches fine and the token buys nothing while risking secret-scan
  revocations. Target state is zero GitHub credentials in flake CI.
- **Chat-relayed values are short-lived**: the gateway redacts credential-shaped
  strings in history, and mid-task cleanup can delete your only local copy — keep a
  600-perm file from receipt until the secret is confirmed written, then delete.
- **A user-reported "my token got deleted" is usually agent collateral damage** —
  before any token-cleanup pass, list names and get explicit confirmation for each
  deletion; never bulk-delete by pattern.

## Storage & cleanup discipline

- PAT value lives in exactly two places: KeePassXC (user-maintained entry/attribute)
  and the Gitea encrypted secret. Delete every /tmp copy immediately after wiring;
  chat-transmitted values are redacted by the gateway anyway — keep a local 600 file
  only within the same command block that consumes it.
- Cleanup pass after any incident: list tokens via web session or ask the user to
  revoke test-named entries; never leave blind-created tokens behind.
