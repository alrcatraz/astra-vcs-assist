---
name: astra-vcs-assist-gpg-key
description: "GPG key lifecycle management — check existing keys, import from backup, generate new keys, configure for VCS signing, key rotation, and cross-machine distribution."
version: 1.0.0
platforms: [linux]
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
Name-Real: Alrcatraz
Name-Email: alrcatraz@gmx.com
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

1. **`gpg failed to sign the data`** — Usually means: (a) no secret key for the configured `user.signingkey`, (b) gpg-agent is stuck, or (c) passphrase not cached. Run `gpg --list-secret-keys <key-id>` first to confirm the key is present.

2. **`gpg-preset-passphrase` not found** — The binary lives at different paths depending on distro. Common locations: `/usr/libexec/gpg-preset-passphrase` (Fedora, openSUSE), `/usr/lib/gnupg2/gpg-preset-passphrase` (Debian/Ubuntu). Check `pacman -Ql gnupg | grep preset` or `dpkg -L gnupg | grep preset` to find it.

3. **Pinentry in non-TTY environments.** Without a display server, pinentry programs (gtk, qt, curses) can't open their dialog window. Use `--pinentry-mode loopback` or set `gpg-agent.conf`: `pinentry-mode loopback`.

4. **Email mismatch.** Git signing verification fails if the email in the GPG key doesn't match the email in the commit. Always verify: `gpg --list-key <key-id> | grep uid` and `git config user.email`.

5. **Trust model.** Without `trust` set to `ultimate`, GPG signs with a warning. Always run `gpg --edit-key <key-id> → trust → 5` after importing a key.

6. **Backup before rotation.** Export both secret and public keys before extending expiry or rotating. A mistake during `--edit-key` can leave you without a valid signing key.
