---
name: astra-vcs-assist-gpg-key
description: "GPG key lifecycle management — check existing keys, import from backup, generate new keys, configure for VCS signing, key rotation, and cross-machine distribution."
version: 1.4.0
author: alrcatraz
triggers:
  - "GPG 密钥"
  - "签名密钥"
  - "gpg key"
  - "导入私钥"
  - "密钥备份"
  - "git commit -S"
  - "signing key"
platforms: [linux]
metadata:
  hermes:
    tags: [gpg, key-management, signing, backup, ssh-keys]

---

# astra-vcs-assist-gpg-key — GPG Key Lifecycle Management

## Trigger Conditions

Load this sub-skill when:

- Checking what GPG keys are available on the current machine
- Importing GPG keys from backup
- Generating a new GPG key for code signing
- Configuring VCS to use a specific signing key
- Rotating or revoking an existing signing key
- Setting up GPG on a new machine
- Troubleshooting "gpg failed to sign the data" errors

## Overview

GPG keys are the backbone of trusted VCS commits. This sub-skill covers the full lifecycle:

```text
Generate    →   Backup    →   Import    →   Configure    →   Sign    →   Rotate
  │                                                           │
  └── Algorithms & usage types          Cache passphrase ────┘
```

## 1. Checking Existing GPG Keys

### List all secret keys (private keys on this machine)

```bash
gpg --list-secret-keys --keyid-format LONG
gpg --list-secret-keys --keyid-format LONG --with-keygrip   # see keygrips for preset-passphrase
```

### List all public keys (includes imported ones)

```bash
gpg --list-keys --keyid-format LONG
```

### Identify which key git is using

```bash
git config --get user.signingkey
gpg --list-secret-keys --keyid-format LONG | grep -A1 "$(git config --get user.signingkey)"
```

### Show key details (algorithms, expiry, subkeys)

```bash
gpg --list-secret-keys --keyid-format LONG --key-format COLON <key-id>
# Or the human-readable version:
gpg --list-secret-keys --keyid-format LONG <key-id> | grep -E "^(sec|ssb|uid|fpr)"
```

## 2. Generating a New GPG Key

### Interactive generation (recommended for first time)

```bash
gpg --full-generate-key
```

Follow the prompts:
1. **Kind**: RSA and RSA (default) or Ed25519 (modern, smaller keys)
2. **Key size**: 4096 for RSA, or use Ed25519 (fixed 256-bit, equivalent to RSA 3072+)
3. **Expiry**: Choose a sensible expiry (1–3 years). You can extend it later.
4. **Real name**: Use your full name or GitHub username (matches your published identity)
5. **Email**: The email associated with your VCS commits

### Non-interactive generation (scriptable)

```bash
# Ed25519 primary key + encryption subkey
gpg --batch --gen-key <<EOF
Key-Type: eddsa
Key-Curve: ed25519
Key-Usage: sign
Subkey-Type: ecdh
Subkey-Curve: cv25519
Subkey-Usage: encrypt
Name-Real: User Name
Name-Email: user@example.com
Expire-Date: 2y
Passphrase: <supply securely>
EOF
```

### Key usage considerations

| Key type | Purpose | Recommended |
|:---------|:--------|:------------|
| RSA 4096 | Signing + encryption | Compatible everywhere, but slow to generate |
| Ed25519/Cv25519 | Signing + encryption | Modern, fast, compact. Widely supported since GnuPG 2.2+ |
| Separate signing subkey | Code signing only | Best practice — keeps your master key offline |

## 3. Importing Keys from Backup

### From an ASCII-armored backup file

```bash
gpg --import /path/to/secret-key-backup.asc
```

### From an encrypted backup (e.g. KeePassXC, USB drive)

```bash
# Decrypt first, then import
gpg --decrypt /path/to/encrypted-backup.gpg | gpg --import
```

### From a remote machine (SSH)

```bash
ssh user@remote "gpg --export-secret-keys --armor <key-id>" | gpg --import
```

### Trust the key after import

```bash
gpg --edit-key <key-id>
# In the interactive prompt:
> trust
> 5 (I trust ultimately)
> quit
```

### Import the public key to your Git hosting provider

```bash
gpg --export --armor <key-id>
# Copy output → GitHub Settings → SSH and GPG keys → New GPG key
```

## 4. Configuring Git to Use a Specific Signing Key

### Per-repository (recommended)

```bash
cd /path/to/repo
git config user.signingkey <key-id>
git config commit.gpgsign true
git config tag.gpgsign true
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### Global (if all repos use the same identity)

```bash
git config --global user.signingkey <key-id>
git config --global commit.gpgsign true
```

### Verify git can sign

```bash
echo "test" | gpg --clearsign
git commit --allow-empty -S -m "test signing"
```

## 5. Caching the GPG Passphrase (Headless / Automated)

Two approaches, choose based on environment:

### A: gpg-preset-passphrase (when available)

Cache the passphrase into gpg-agent so non-interactive signing works:

```bash
# Find the signing subkey's keygrip
gpg --list-secret-keys --keyid-format LONG --with-keygrip <key-id>

# Preset the passphrase
echo "your-passphrase" | /usr/libexec/gpg-preset-passphrase --preset <keygrip>
```

**Important:**
- Multiple subkeys (signing + encryption) each need their own `--preset` call
- Default cache TTL: 600 seconds (10 minutes). Extend in `~/.gnupg/gpg-agent.conf`:
  ```
  default-cache-ttl 86400
  max-cache-ttl 604800
  ```
- If `gpg-preset-passphrase` is not installed, check `gnupg` package — it's sometimes a separate package or at a different path

### B: Pinentry loopback (when pinentry unavailable)

For headless environments (servers, containers, cron) without a pinentry program:

```bash
creds=$(gpg --batch --yes --pinentry-mode loopback \
  --passphrase "your-passphrase" \
  -d ~/.password-store/git/https/github.com/user.gpg 2>/dev/null)
```

`--pinentry-mode loopback` lets GPG accept `--passphrase` directly without a pinentry dialog.

## 6. Key Maintenance

### Extend expiry of an existing key

```bash
gpg --edit-key <key-id>
> expire
> 3y
> key 1          # select subkey 1
> expire
> 3y
> save
```

### Export updated public key (after extending expiry)

```bash
gpg --export --armor <key-id> > updated-public-key.asc
```

### Revoking a compromised key

```bash
gpg --gen-revoke <key-id> > revoke.asc
gpg --import revoke.asc
# Upload to keyservers or share with collaborators
gpg --keyserver keyserver.ubuntu.com --send-keys <key-id>
```

## 7. Cross-Machine GPG Strategy

| Scenario | Approach |
|:---------|:---------|
| **Same OS, same distro** | Copy `~/.gnupg/` directory (minus `private-keys-v1.d/` — export/import secret keys instead) |
| **Different machines, same identity** | Export secret key from machine A → import on machine B → set `user.signingkey` per-repo |
| **Different key per machine** | Generate separate keys per machine, add each public key to GitHub/Gitea |
| **No GPG on target** | Use `git bundle` to transfer commits to a signed-signing-capable machine |

## Pitfalls

0. **Cross-machine: signing passphrase may be stored in an env file.** On
alrcatraz's machines the signing passphrase may live in an env file
(var `GPG_Key_Alrcatraz`, short). Preset it with
`gpg-preset-passphrase --preset <signing keygrip>` (this machine has
`allow-preset-passphrase` + long cache TTL). **Never run
`gpgconf --kill gpg-agent` to debug signing — it clears the cached
passphrase and forces a re-preset.** If the Hermes terminal lifecycle
guard crashes (`embedded null byte`) when a bash command contains the
keygrip/passphrase string, use a small Python `subprocess` via
`execute_code`, or run `~/.hermes/scripts/preset_gpg_signing.sh`.

   **Recipe is HC01-only; do NOT port it blindly.** Verified 2026-09-16 on
   SUSETLearn00 (GnuPG 2.5.22): `--pinentry-mode loopback` with either
   `--passphrase-fd 0` or `--passphrase ARG` over SSH returns error 67109041
   "No passphrase given" for ALL candidate passphrases (env GPG_Key_* AND the
   sudo pw) — the loopback request never reaches the agent, so right-vs-wrong
   passphrase cannot even be distinguished remotely; `gpg-preset-passphrase`
   fails Not supported / Not implemented even after adding
   `allow-preset-passphrase` + reloadagent. Lessons: (a) check before appending
   config directives — mine duplicated an existing one; (b) after two distinct
   failure modes STOP grinding and hand the user one literal copy-pasteable
   commit command; (c) staged-but-uncommitted is acceptable only if explicitly
   surfaced.

1. **`gpg failed to sign the data`** — Usually means: (a) no secret key for the configured `user.signingkey`, (b) gpg-agent is stuck, or (c) passphrase not cached. Run `gpg --list-secret-keys <key-id>` first to confirm the key is present.

1. **FIRST ACTION after any restart: re-preset the passphrase — do not report "cannot sign" to the user.**

   On machines with the HC01-style setup (agent cache TTL 1 day / 7 days max,
   `allow-preset-passphrase`), a Hermes restart or `gpg-agent` relaunch clears
   the cached passphrase, and `git commit` then dies with
   `PINENTRY_LAUNCHED … not a tty — Operation cancelled`. This is NOT a
   capability gap: the environment is fine, the cache is simply cold.

   Run the existing script and retry — it ends with a real sign test:

   ```bash
   bash ~/.hermes/scripts/preset_gpg_signing.sh   # prints PRESET_EXIT=0 / SIGN_OK
   ```

   Only if that prints `SIGN_FAIL` is there a real problem. Reporting
   "I can't sign, you do it" without running this wastes the user's time and
   misrepresents a one-command fix as a blocker — expect pushback along the
   lines of "it used to work", and they are right.

   Check the cache is cold, not the config broken:
   `git config --get gpg.program` empty + `~/.gnupg/gpg-agent.conf` containing
   `allow-preset-passphrase` = nothing to fix but the cache.

1a. **Never point `gpg.program` at a `/tmp` script.** A wrapper that injects the
   passphrase into `gpg --batch --pinentry-mode loopback --passphrase …` is a
   legitimate headless workaround, but pinning `gpg.program` to a `/tmp` path
   breaks silently the moment the temp directory is cleared — the config entry
   outlives the file:

   ```
   fatal: cannot exec '/tmp/git-gpg-wrapper.sh': No such file or directory
   ```

   Symptom: every `git commit` in that repo fails to sign; the repo sits with a
   clean-looking `.git/config` that points at a file nobody can find.
   Detection: `git config --list | grep gpg` (a `gpg.program` entry is the
   suspect) and `ls -l` the referenced path.
   Fix: `git config --unset gpg.program` — plain `gpg` works once the
   passphrase is preset into the agent (§5-A / Pitfall 0 below).
   That is also the safer route: `--passphrase ARG` briefly exposes the
   passphrase in the process list, while the agent cache does not. If you
   genuinely need a pinentry-free invocation, keep the wrapper under
   `~/.local/bin/`, never `/tmp`.

   *This machine (instance copy):* the retired wrapper read `GPG_Key_Alrcatraz`
   from `~/.hermes/.env`, and a copy was pinned into
   `~/Projects/astra/astra-aigate/.git/config` on 2026-08-13 while the file
   itself lived in `/tmp` — breaking signing there until 2026-09-12. The durable
   route is `~/.hermes/scripts/preset_gpg_signing.sh` (presets the signing
   keygrip into the agent; TTL 1 day, 7 days max).
   Verify the fix in a throwaway repo (no pollution of the real one):

   ```bash
   T=$(mktemp -d); cd "$T"; git init -q
   git config user.name  "Alrcatraz"; git config user.email "alrcatraz@gmx.com"
   git config user.signingkey B01ECDF27D2D156D; git config commit.gpgsign true
   git commit -q --allow-empty -S -m "signing test"
   git log -1 --show-signature | grep -E "Good signature|BAD signature"
   cd /; rm -rf "$T"
   ```

2. **`gpg-preset-passphrase` not found** — The binary lives at different paths depending on distro. Common locations: `/usr/libexec/gpg-preset-passphrase` (Fedora, openSUSE), `/usr/lib/gnupg2/gpg-preset-passphrase` (Debian/Ubuntu). Check `pacman -Ql gnupg | grep preset` or `dpkg -L gnupg | grep preset` to find it.

3. **Pinentry in non-TTY environments.** Without a display server, pinentry programs (gtk, qt, curses) can't open their dialog window. Use `--pinentry-mode loopback` or set `gpg-agent.conf`: `pinentry-mode loopback`.

4. **Email mismatch.** Git signing verification fails if the email in the GPG key doesn't match the email in the commit. Always verify: `gpg --list-key <key-id> | grep uid` and `git config user.email`.

5. **Trust model.** Without `trust` set to `ultimate`, GPG signs with a warning. Always run `gpg --edit-key <key-id> → trust → 5` after importing a key.

6. **Backup before rotation.** Export both secret and public keys before extending expiry or rotating. A mistake during `--edit-key` can leave you without a valid signing key.
