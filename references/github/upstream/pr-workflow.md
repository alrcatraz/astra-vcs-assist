# Account and GPG setup, branch setup, preparing the change

## Workflow

### 1. Account Selection & GPG Setup

> **Per-project active account — switch, don't assume one default.** This host
> carries multiple `gh` accounts (e.g. `alrcatraz` and `Zhen-LinHuo`) and the
> user's rule is that **each project picks its own default** — there is no single
> global Active account. For NousResearch/hermes-agent upstream PRs the default
> is `alrcatraz` (fork `alrcatraz/hermes-agent`; commits, pushes, and replies all
> go through it). Pick by project, then confirm before acting:
> `gh auth status` → `gh auth switch --user <account>` if the wrong one is Active.
> **The Active flag reverts without warning between tool calls** — a `gh auth
> switch` done earlier in a session is not durable; some gh invocations or OS
> keychain refreshes reset it. **Re-check `gh api user --jq .login` before EVERY write
> operation** (PATCH, POST comment, push, `gh pr create`), not just at session start —
> including *comments*: posting an issue/PR reply under the wrong account splits one
> person's thread into two identities, and repairing it needs the WRONG account again
> (a non-admin can only delete their own comment), so the fix costs two extra
> switches and leaves a deletion hole if anyone read it in between. Prefer
> `gh api user --jq .login` as the authority — `gh auth status` can show a stale
> Active flag (it showed `Zhen-LinHuo / Active account: true` minutes after a
> successful alrcatraz push). The cost is asymmetric: a read succeeds on EITHER
> account, so "the GET worked" never proves your identity — only an
> author-attributed write (comment, push, edit) exposes it.
> A wrong Active account on a write surfaces as **404 on PATCH that succeeds on GET**
> (GitHub returns 404 rather than 403 for insufficient write permission on the
> pulls/issues endpoints), so a PATCH-404 after a working GET means the account
> switched, not that the URL is wrong. Fix: `gh auth switch -u <owner>` →
> verify `gh api user --jq .login` → retry. Pushes additionally need the
> credential-helper override if GCM is the configured helper (see the Push 403
> pitfall below).
> The Active account is the push credential AND (via `gh auth git-credential`)
> the author-attribution source, so setting it once per project avoids both the
> 403 and the unattributed-commit failures below.

> **Sign by default — this project's own commits are always signed.** Our
> contribution commits on NousResearch/hermes-agent carry GPG signatures
> (verify: `git log --format='%h %G?' <our-branch>` → `E`/`G`, never `N`), so
> the standing rule is the normal `commit.gpgsign true` + `user.signingkey`
> path — see skill `astra-vcs-assist` → `references/gpg/key-lifecycle/SKILL.md` (preset the passphrase first with
> `~/.hermes/scripts/preset_gpg_signing.sh`; it ends in a real sign test, so
> `SIGN_OK` means signing works and there is nothing to debug).
>
> `%G?` showing `E` means the signature exists but the key is not in the LOCAL
> keyring — that is expected on a machine that verifies-but-does-not-own the
> key, and it is NOT "unsigned". Do not misread `E` as `N`.
>
> Measure the upstream repo's own convention separately if you ever need to
> (e.g. `git log <base> --format='%h %G? %s'`); whatever the maintainers do,
> our contributions stay signed for attribution.

```bash
# List available gh accounts
gh auth status

# Switch to the account you'll open the PR from
gh auth switch --user alrcatraz

# If the clone is fresh, configure per-repo identity
# ⚠️ CRITICAL: git user.email MUST match the GitHub account's primary email.
# GitHub uses the commit email to associate commits with an account, NOT the
# author name. Using zhenlinhuo503@outlook.com makes GitHub show Zhen-LinHuo
# instead of alrcatraz on the PR page.
git config user.name "alrcatraz"
git config user.email "alrcatraz@gmx.com"
git config user.signingkey B01ECDF27D2D156D
git config commit.gpgsign true
```

If GPG signing fails with a timeout on gpg 2.5.20+ (openSUSE), the passphrase
may not be cached. Retrieve it from `~/.hermes/.env` (`GPG_Key_Alrcatraz`) and
use the wrapper approach:

```bash
PASSPHRASE=$(grep GPG_Key_Alrcatraz ~/.hermes/.env | cut -d= -f2)
cat > /tmp/gpg-sign.sh << EOGPG
#!/bin/bash
exec gpg --batch --pinentry-mode loopback --passphrase "$PASSPHRASE" "$@"
EOGPG
chmod +x /tmp/gpg-sign.sh
GIT_SSH_COMMAND= git config gpg.program /tmp/gpg-sign.sh
```

**Faster alternative — preset the passphrase into gpg-agent** (works for plain
`git commit -S` without wrapper scripts; verified in the field):

```bash
# 1. Get the keygrip of the signing key
gpg --with-keygrip --list-secret-keys B01ECDF27D2D156D | grep 'Keygrip = ' | awk '{print $3}'
# 2. Preset the passphrase (binary NOT in PATH on openSUSE — use full path)
echo "$PASSPHRASE" | /usr/libexec/gpg-preset-passphrase --preset <KEYGRIP_HEX>
# 3. Now `git commit -S` succeeds in the same gpg-agent session (no tty needed)
```

`gpg-preset-passphrase` lives at `/usr/libexec/gpg-preset-passphrase` on
openSUSE (find it: `find /usr -name 'gpg-preset-passphrase'`; could also be
`/usr/lib64/gnupg/`). The preset persists for the gpg-agent cache lifetime
(default ttl), so subsequent commits in the same session don't re-prompt.

> **Hermes terminal-guard crash on passphrase strings.** Inside Hermes, running a
> bash command or script that *contains the passphrase/$gpg-preset-passphrase
> invocation inline* can trip the terminal lifecycle guard, which crashes with
> `embedded null byte` (a guard bug when it tries to re-parse the command it
> thinks is dangerous). Workaround: put the preset in a standalone script
> (`~/.hermes/scripts/preset_gpg_signing.sh`) and run that, or run the preset
> via a small Python `subprocess` through `execute_code`. The preset itself is
> safe — only the inline bash form trips the guard. Also: **never run
> `gpgconf --kill gpg-agent` to debug signing** — it clears the cached
> passphrase and forces a re-preset (skill `astra-vcs-assist` → `references/gpg/key-lifecycle/SKILL.md`).

### GPG Pitfall: git rebase
`git rebase` replays commits, each of which is re-signed. If the GPG passphrase isn't
cached in the agent (gpg-agent.conf), rebase will hang waiting for the passphrase and
time out after ~30 s per commit. Workarounds (in order of reliability):

1. **Preferred: disable signing for the rebase.** Use `-c commit.gpgsign=false`:
   ```bash
   git -c commit.gpgsign=false rebase origin/main
   ```
2. **Cache the passphrase.** If you installed a local gpg-agent.conf that auto-presets
   the passphrase (common on new machines), run `gpg-connect-agent reloadagent /bye`
   before the rebase.
3. **Wrap gpg with passphrase injection** (see GPG setup section above) — fragile if
   the user's machine doesn't have the same env variable.

### 2. Branch Setup

```bash
# Set up dual remotes (fork + upstream)
git remote add fork git@github.com:alrcatraz/hermes-agent.git
git remote add upstream git@github.com:NousResearch/hermes-agent.git

# Create feature branch from upstream main
git fetch upstream main
git checkout -b feat/my-feature upstream/main

# Push to fork
git push -u fork feat/my-feature
```

### 3. Before Making Changes

- **Read upstream docs before writing fixes — but when the project lives on
  GitLab, use its REST API, not just the web UI.** The user's stated rule
  (2026-08-17): **"看上游有没有修复或 Issue，没有就 PR + 补丁"** — before writing
  any fix, check upstream for BOTH an existing fix (open/merged PR) AND an open
  Issue describing the bug:
- Check if a PR already exists for this (`gh pr list`)
- **GitLab-hosted upstreams (freedesktop etc.): the web UI blocks anonymous
  browsing ("influx of spam" gate), and general web search may be down. Use the
  unauthenticated issues API instead** (verified 2026-09-04 for NetworkManager
  triage): `curl -sk "https://gitlab.freedesktop.org/api/v4/projects/<group>%2F<project>/issues?search=<kw>&state=all&per_page=20"`
  — run several narrow keyword queries (symptom words, component names,
  version numbers), filter titles, then fetch one issue's full description via
  `/issues/<iid>` before judging relevance. This found #1984/#1711/#1004 in
  minutes when SearXNG was 401. GitHub equivalent: `gh search issues` /
  `gh api`.
- **Query open Issues that may describe the exact bug** — a faithful bug report
  often lives as an open Issue WHILE a fix PR is already open against it
  (e.g. `gh search issues --repo <repo> "keyword" --state open`; then inspect
  cross-referenced PRs on the Issue via `gh api repos/<r>/issues/<n>/timeline
  --jq '[.[] | select(.event=="cross-referenced") | .source.issue.number]'`).
- Read the upstream code to understand conventions
- Base all work on `origin/main` (fork's main) which is synced from upstream

**Branch on what you find upstream — this decides PR+patch vs just-patch:**

| Upstream state | Action |
|:--|:--|
| **No Issue, no PR** for the bug | You own it: write the fix → **PR + local patch** (patch so already-deployed instances get it before merge). |
| **Open Issue, no PR** | Reproduce/confirm the bug, then **PR (Fixes #N) + patch** — the PR closes the issue. |
| **Open PR already fixing it** | **Do NOT repeat the PR.** Review that PR's diff; take/adapt ITS patch for deployed instances to get the fix live before merge. Track it in PR monitoring to follow the merge. Only re-PR if the existing PR is stale/mergeable:false AND covers a different layer than your fix. |
| **Fix merged upstream** | Nothing to PR; sync upstream and drop your local patch. |

- When an existing PR is `mergeable:false` (conflicts with main) or touches many
  unrelated files, prefer extracting ONLY the minimal diff you need (e.g.
  `gh api .../pulls/N/files --jq '.[].filename'` to see scope; apply just the
  hunk you need) rather than bringing the whole PR into your deployment.
- Deepen: a reported bug often has TWO layers — the forwarding gap (param never
  passed down) and the actual missing feature (e.g. a param exists but is not
  independently usable). Upstream may fix only layer 1; if you need layer 2,
  that's a SEPARATE PR even when an open PR covers layer 1.
