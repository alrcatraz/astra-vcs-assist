# astra-vcs-assist-gpg-key — GPG Key Lifecycle Management

*This reference was migrated from the `astra-vcs-assist-gpg-key` sub-skill.*

## Trigger Conditions

- Checking what GPG keys are available
- Importing GPG keys from backup
- Generating a new GPG key for code signing
- Configuring VCS to use a specific signing key
- Rotating or revoking an existing signing key
- Setting up GPG on a new machine
- Troubleshooting "gpg failed to sign the data"

## Overview

```
Generate   →   Backup   →   Import   →   Configure   →   Sign   →   Rotate
```

## 1. Checking Existing GPG Keys

```bash
gpg --list-secret-keys --keyid-format LONG
gpg --list-secret-keys --keyid-format LONG --with-keygrip
gpg --list-keys --keyid-format LONG
git config --get user.signingkey
```

## 2. Generating a New GPG Key

### Interactive (recommended)

```bash
gpg --full-generate-key
```

### Non-interactive

```bash
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

## 3. Importing Keys from Backup

```bash
gpg --import /path/to/secret-key-backup.asc
gpg --edit-key <key-id>
> trust
> 5 (I trust ultimately)
> quit
```

From SSH:
```bash
ssh user@remote "gpg --export-secret-keys --armor <key-id>" | gpg --import
```

Upload public key to GitHub:
```bash
gpg --export --armor <key-id>
# Copy → GitHub Settings → SSH and GPG keys → New GPG key
```

## 4. Configuring Git

```bash
cd /path/to/repo
git config user.signingkey <key-id>
git config commit.gpgsign true
git config tag.gpgsign true
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

Verify:
```bash
echo "test" | gpg --clearsign
git commit --allow-empty -S -m "test signing"
```

## 5. Caching GPG Passphrase (Headless)

### A: gpg-preset-passphrase

```bash
# Find keygrip
gpg --list-secret-keys --keyid-format LONG --with-keygrip <key-id>
# Preset
echo "passphrase" | /usr/libexec/gpg-preset-passphrase --preset <keygrip>
```

Extend cache TTL in `~/.gnupg/gpg-agent.conf`:
```
default-cache-ttl 86400
max-cache-ttl 604800
```

### B: Pinentry loopback (no pinentry)

```bash
gpg --batch --yes --pinentry-mode loopback \
  --passphrase "passphrase" \
  -d ~/.password-store/git/https/github.com/user.gpg 2>/dev/null
```

## 6. Key Maintenance

### Extend expiry

```bash
gpg --edit-key <key-id>
> expire
> 3y
> key 1
> expire
> 3y
> save
```

### Revoke compromised key

```bash
gpg --gen-revoke <key-id> > revoke.asc
gpg --import revoke.asc
gpg --keyserver keyserver.ubuntu.com --send-keys <key-id>
```

## Pitfalls

1. **`gpg failed to sign the data`** — missing secret key, stuck agent, or uncached passphrase.
2. **`gpg-preset-passphrase` paths differ by distro** — check with `pacman -Ql gnupg | grep preset` or `dpkg -L gnupg | grep preset`.
3. **Pinentry in headless environments** — use `--pinentry-mode loopback`.
4. **Email mismatch** between GPG key `uid` and `git config user.email` causes "Unverified" commits.
5. **Trust model** — must set trust to `ultimate` after import.
6. **Backup before rotation** — export keys before extending expiry or rotating.
