---
name: astra-vcs-assist-git-sync
description: "Git remote synchronisation — single and dual-remote push, safe force push with --force-with-lease, credential injection strategies, and git bundle for cross-machine transfer."
version: 1.0.0
author: alrcatraz
platforms: [linux]
---

# astra-vcs-assist-git-sync — Remote Synchronisation

## Trigger Conditions

Load this sub-skill when:

- Pushing commits to a remote repository
- Pushing to multiple remotes (e.g. GitHub + self-hosted Gitea)
- Performing a force push after history cleanup
- Transferring commits between machines without network access
- Setting up or troubleshooting credential helpers
- Diagnosing push failures (auth, timeout, rejected)

## Overview

Getting commits from your local repository to remote destinations involves
three concerns: **transport** (push/bundle), **credentials** (auth), and
**safety** (—force-with-lease).

```text
Local commits
  │
  ├── Single remote    →  git push
  ├── Dual remote      →  git push + push mirror
  ├── Force push       →  git push --force-with-lease
  └── Cross-machine    →  git bundle → transfer → pull
```

## 0. Analyse Remote Topology (Do This First)

Before pushing, determine the remote relationship:

1. **Check existing remotes:**
   ```bash
   git remote -v
   ```

2. **Check remote ownership:**
   ```bash
   git remote get-url origin
   ```
   - Does the URL contain your own GitHub/Gitea account? → you own this repo
   - Does it point to someone else's account? → this is a fork

3. **Check for upstream:**
   ```bash
   git remote get-url upstream 2>/dev/null || echo "no upstream"
   ```

4. **Detect self-hosted backup mirror:**
   ```bash
   git remote -v | grep -vE '^(origin|upstream)\s' | \
     grep -iE 'git\..*\.(com|org|net|io|dev)|gitea|gitlab|自建' || \
     echo "no self-hosted mirror detected"
   ```
   Any remote whose URL contains your own git server domain
   (e.g. `git01.wrt.astra-lab.org`) is a backup mirror, regardless
   of what it's named (`backup`, `gitea`, `myrepo`, etc.).

### Decision: Which sync strategy?

| Remote topology | How to recognise | Strategy |
|:----------------|:-----------------|:---------|
| **Single remote** | Only `origin`, no other remotes | §1 — Single Remote Push |
| **Primary + backup mirror** | `origin` (GitHub) + one or more other remotes pointing to self-hosted git | §2 — Dual Remote Push |
| **Upstream + fork** | `upstream` (owner's repo) + `origin` (your fork) + no self-hosted mirror | §2a — Fork Sync |
| **Upstream + fork + backup** | All three: `upstream` + `origin` + self-hosted mirror | §2a + §2 combined |

## 1. Single Remote Push (Standard)

### Normal push

```bash
# Push current branch to upstream (if set via push.autoSetupRemote)
git push

# Push to a specific remote/branch
git push origin main

# Push current branch and set upstream
git push -u origin HEAD

# Push with tags
git push origin main --tags
```

### Pre-push checklist

```bash
# Before pushing, verify what's going:
git status                         # no unintended staged files
git log --oneline origin/main..    # commits you're about to push
git log --show-signature -1        # last commit is signed
git diff --stat origin/main..      # scope of changes
```

## 2. Dual Remote Push (Mirror to Two Remotes)

When pushing to both a primary (e.g. GitHub) and a mirror (e.g. self-hosted
Gitea), set up two remotes:

```bash
# Set up remotes
git remote add origin   https://github.com/owner/repo.git
git remote add mirror   https://git.example.com/owner/repo.git

# Or rename for clarity
git remote rename origin github
git remote add gitea https://git.example.com/owner/repo.git
```

### Push to both remotes

```bash
# Method A — push to each explicitly
git push origin main
git push mirror main
git push origin v1.2.0
git push mirror v1.2.0

# Method B — push URL (single push goes to both)
git remote set-url --add --push origin https://github.com/owner/repo.git
git remote set-url --add --push origin https://git.example.com/owner/repo.git
# Now `git push origin main` pushes to BOTH destinations
```

### Dual remote sync workflow

After cleaning up commits or force-pushing, always sync to both:

```bash
# On the development machine:
git push origin main --force-with-lease
git push origin --tags

# On the machine hosting the mirror:
cd /path/to/repo
git pull            # or re-clone if history diverged
```

### 2a. Fork Sync (Upstream + Your Fork)

When you track an upstream repo and maintain your own fork (e.g.
`jo-inc/camofox-browser` upstream → `alrcatraz/astra-camofox-browser` fork):

```bash
# Remotes
git remote add upstream https://github.com/upstream-owner/repo.git  # read-only
git remote rename origin github                                      # your fork (push)
# Or keep as origin (your fork):
# git remote add upstream https://github.com/upstream-owner/repo.git
```

**Daily sync from upstream:**

```bash
# Fetch upstream changes
git fetch upstream

# Update your main branch
git checkout main
git rebase upstream/main          # or: git merge upstream/main

# Push updated main to your fork
git push origin main

# Now rebase your feature branch on top
git checkout feat/my-feature
git rebase main
```

**Pushing your changes:**

```bash
# Push feature branch to your fork
git push -u origin feat/my-feature

# Open a PR to upstream (see git-release §8)
```

**Dual push (fork + backup):**

```bash
# If you also have a self-hosted mirror:
git remote add gitea https://git.example.com/your-username/repo.git
git push origin main
git push gitea main
```

## 3. Safe Force Push

### When force push is acceptable

- You just rebased or squashed local commits (history rewritten)
- Amending a commit that was never shared with others
- Fixing credentials or secrets accidentally committed
- On a private branch that only you work on

### When force push is NOT acceptable

- On a shared branch that others have based work on
- After a tag has been published (tags are promises)
- Without notifying collaborators first

### Use `--force-with-lease` (not `--force`)

```bash
# Safe — rejects if the remote has new commits you haven't seen
git push --force-with-lease origin main

# Force push with tags
git push --force-with-lease origin main
git push --force origin v1.2.0         # tags don't have lease protection
                                       # → use `git push origin :refs/tags/v1.2.0`
                                       #   then `git push origin v1.2.0` instead
```

`--force-with-lease` checks that your local understanding of the remote
branch matches reality. If someone else pushed in the meantime, the push
is rejected — preventing accidental overwrites.

```bash
# If lease check fails:
git fetch origin
git log origin/main..                  # see what they pushed
git diff origin/main HEAD              # compare with yours
# Then decide: rebase, or force push (if you're sure)
git push --force-with-lease origin main
```

### After force push, notify

Force-pushing rewrites history. If anyone else uses this repository:

> "Force-pushed `main` to fix commit history after rebase.
> Please rebase your branches: `git fetch && git rebase origin/main`"

## 4. Cross-Machine Sync (Git Bundle)

When machines can't reach each other (no network, firewalls, VPN down),
`git bundle` packs commits into a single file for transfer.

### Create a bundle

```bash
# On machine A (source)
cd /path/to/repo

# Bundle all new commits since the last shared state
git bundle create /tmp/repo-update.bundle origin/main..HEAD

# Bundle specific branches
git bundle create /tmp/repo-full.bundle --all

# Bundle just the main branch
git bundle create /tmp/repo-main.bundle main

# Verify the bundle
git bundle verify /tmp/repo-main.bundle
```

### Transfer the bundle

USB drive, SCP, email attachment, NAS share, file transfer service.

### Apply the bundle

```bash
# On machine B (target — may not have GPG signing set up)
cd /path/to/repo

# Pull from the bundle as if it were a remote
git pull /tmp/repo-main.bundle main

# Or fetch + merge
git fetch /tmp/repo-main.bundle main:imported-branch
git checkout imported-branch

# Or inspect without applying
git bundle list-heads /tmp/repo-main.bundle
```

### Bundle strategy for GPG signing

If machine B lacks GPG keys for signing:

```bash
# 1. Create the bundle on machine A (signed commits included)
# 2. Transfer to machine B
# 3. Machine B can push the signed commits to a remote
#    (the signatures are part of the commit objects — they survive)
```

## 5. Credential Strategies

### Strategy comparison

| Strategy | Setup | Security | Headless | Best for |
|:---------|:------|:---------|:---------|:---------|
| **SSH key** | `ssh-keygen + deploy key` | ✅ High | ✅ | Single user, low complexity |
| **GCM + GPG** | `git config credential.helper manager` | ✅ High | ❌ needs display | Desktop development |
| **pass + GPG** | `pass insert git/...` + custom helper | ✅ High | ✅ loopback | Headless servers |
| **Inline credential** | `-c credential.helper="!f() { echo ... }"` | ⚠️ Medium | ✅ | One-shot pushes |
| **Netrc** | `~/.netrc` | ❌ Plaintext | ✅ | Legacy only |

### SSH key (recommended for simplicity)

```bash
# Generate a key if you don't have one
ssh-keygen -t ed25519 -C "your.email@example.com"

# Add to ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Configure remote to use SSH
git remote set-url origin git@github.com:owner/repo.git

# Test
ssh -T git@github.com
```

### GPG + pass (for headless environments)

From `astra-vcs-assist-gpg-key` — the two-path approach:

```bash
# Path A: gpg-preset-passphrase
echo "passphrase" | /usr/libexec/gpg-preset-passphrase --preset <keygrip>

# Path B: pinentry loopback (when no pinentry)
creds=$(gpg --batch --yes --pinentry-mode loopback \
  --passphrase "passphrase" \
  -d ~/.password-store/git/https/github.com/user.gpg 2>/dev/null)
token=$(echo "$creds" | head -1)
printf "protocol=https\\\\nhost=github.com\\\\nusername=user\\\\npassword=%s\\\\n" "$token" \
  | git credential approve
```

### One-shot credential injection

For a single push without config changes:

```bash
TOKEN=$(gpg ... --decrypt ... 2>/dev/null | head -1)
GIT_TERMINAL_PROMPT=0 \
  git -c credential.helper="!f() { echo username=alrcatraz; echo password=$TOKEN; }; f" \
  push origin main
```

`GIT_TERMINAL_PROMPT=0` prevents git from falling back to an interactive
password prompt (which would hang in headless environments).

## 6. Handling Push Failures

### Rejected (non-fast-forward)

```bash
# Remote has commits you don't have locally
git fetch origin
git log origin/main..HEAD                    # your commits
git log HEAD..origin/main                    # their commits

# Fix: rebase your work on top of theirs
git rebase origin/main

# Or: merge their work in first
git pull origin main
```

### Authentication failed

```bash
# Check which credential helper is being used
git config --get credential.helper

# Test credential injection manually
echo "protocol=https\\nhost=github.com\\n\\n" | \
  git credential fill

# If the helper is GCM and it's stuck:
#   → try SSH instead (git remote set-url ...)
#   → or use one-shot injection (Section 5 above)
```

### Timeout / network issue

```bash
# Check remote reachability
curl -s -o /dev/null -w "%{http_code}" https://github.com

# If behind a proxy:
git config http.proxy http://127.0.0.1:7890
git config https.proxy http://127.0.0.1:7890

# For large pushes, increase buffer
git config http.postBuffer 524288000   # 500MB
```

### Push size limit exceeded

GitHub has a 100MB file size limit. For large files:

```bash
# Use Git LFS
git lfs track "*.psd" "*.zip"
git add .gitattributes
git commit -m "chore: track large files with LFS"
```

## 7. Post-Push Verification

After pushing, verify the remote matches:

```bash
# Fetch and compare
git fetch origin
git log --oneline origin/main..HEAD            # should be empty
git diff origin/main HEAD                      # should be empty

# Verify tag propagation
git ls-remote --tags origin | grep v1.2.0

# For dual remote, repeat with the second remote
git fetch mirror
git log --oneline mirror/main..HEAD
```

## Pitfalls

1. **`--force` is dangerous, `--force-with-lease` is safer but not magic.** Learn checks that your remote-tracking branch is current. If you haven't fetched in a while, the check is meaningless. Always fetch first.

2. **Tags are not protected by `--force-with-lease`.** A tag push with `--force` overwrites remote tags unconditionally. Delete and re-push tags explicitly to avoid surprises.

3. **Multiple push URLs with `--push --add` is order-dependent.** Git tries URLs in order. If the first succeeds, it stops. Use this for mirroring, not for primary-only pushes.

4. **`git bundle` includes all commits referenced.** Bundling `--all` includes every reachable commit in the repo. For partial transfers, be specific about the range.

5. **SSH key passphrase prompts.** If your SSH key has a passphrase and `ssh-agent` isn't running, every `git push` will prompt for the passphrase. Set up `ssh-agent` at login.

6. **`GIT_TERMINAL_PROMPT=0` is required for headless pushes.** Without it, git falls back to an interactive username/password prompt that hangs forever in cron or automated scripts.

7. **Credentials in shell history.** When injecting credentials via `-c credential.helper=...`, the token appears in the process table briefly. On shared machines, use SSH keys instead.
