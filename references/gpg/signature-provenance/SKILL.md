---
name: astra-vcs-assist-signature-provenance
description: "Use when a signed commit still shows Unverified on a forge."
version: 1.0.0
author: <owner>
platforms: [linux]
tags: [git, gpg, signature, provenance, forge, identity, committer]
triggers:
  - signed commit unverified
  - commit shows unverified
  - signature provenance
  - committer vs author mismatch
  - forge verification flag
  - pin identity per repository
  - verify a push with gh api
---

# Signature provenance — why a signed commit still shows Unverified

## When to use

A commit is signed and the forge still says unverified; a rewrite must end with
the right author on the right account; several repositories in one session need
different identities. This is the *proof* layer. Key creation, passphrase caching
and `gpg failed to sign` belong to `references/gpg/key-lifecycle/SKILL.md`.

## The rule that explains almost every "unverified"

A forge matches the signature against the account of the **committer**, and
attributes the commit to the account of the **author**. Local `%G?` proves the
object is signed; it says nothing about either lookup.

Consequence: a byte-perfect signature still fails when the committer is a
synthetic identity.

- web-editor commits carry committer `GitHub <noreply@github.com>`;
- **PR merges performed in the web UI are always merge commits carrying that same
  committer — they cannot verify, however they are signed.**

## Diagnose in three steps, in this order

1. **Read several commits, not the tip.** One branch can hold both verdicts.

   ```bash
   gh api "repos/<owner>/<repo>/commits?sha=<branch>&per_page=10" \
     --jq '.[] | "\(.sha[0:7]) \(.commit.verification.verified) \(.commit.verification.reason) \(.commit.author.email)"'
   ```

   Mixed `valid` / `unknown_key` on the same key and the same signing pass is a
   committer problem, not a key problem.

2. **Compare a failing and a passing commit.**

   ```bash
   git log -1 --format='%h parents=%p committer=%ce author=%ae' <failing-sha> <passing-sha>
   ```

   Two parents plus `noreply@github.com` explains it. Same parent count and same
   committer on both: keep looking — the cause is elsewhere.

3. **Probe the key/account binding on a throwaway branch**, never on the branch
   that matters.

   ```bash
   git checkout -q -b key-probe && git commit -q --allow-empty -S -m "chore: probe signing key"
   git push -q origin key-probe
   gh api repos/<owner>/<repo>/commits/key-probe --jq '.commit.verification'
   git push -q origin --delete key-probe && git branch -D key-probe
   ```

   `unknown_key` means that account does not hold that key. With two personas,
   a probe signed with the *other* persona's key reports `unknown_key` too — that
   is the expected answer. `gh api user/gpg_keys` cannot serve as the check: it
   needs the `admin:gpg_key` scope and returns 404 with or without keys.

## Identity per repository

Default identity is the **owner of the remote**, not a session-wide choice:

```bash
git remote get-url origin            # owner is in the URL
```

A personal-handle account owns personal and public work; a real-name account owns
academic and work-facing repositories, and each account holds its own signing key
whose UID carries that account's email. Pin all of it repo-locally (`user.name`,
`user.email`, `user.signingkey`, `commit.gpgsign`, `tag.gpgsign`) — a repo without
local config commits as whoever the globals say at that moment, and the failure is
invisible because the commit still succeeds.

Never sign with an agent identity. Never move a repository's persona to make one
commit verify.

## After a rewrite: prove the copy that survived

Two clones of one repository each rewritten independently will both push, and the
last pusher wins; the loser silently keeps its own lineage. Check before reporting
done:

```bash
git fetch -q origin <branch>
git diff --name-only refs/remotes/origin/<branch> <branch> | wc -l
```

- **0 files differing** — same content, different SHAs. A derived or production
  copy can be aligned safely: `git reset --hard origin/<branch>`.
- **Files differing, especially with additions on both sides** — real divergence.
  Do not reset and do not force; report which side holds what and let the owner
  choose.

## Reporting

State which of these it was, with counts: (a) the key is not on that account,
(b) a known number of forge-merged commits that cannot verify by design, (c) not
computed yet — the verdict is evaluated lazily, so re-read once after a pause; two
identical answers mean it is final.

Never rewrite history to chase a badge. Normalising the committer of a merge
commit asserts that a human performed a merge the forge performed; that is a
provenance change, not a cosmetic fix.
