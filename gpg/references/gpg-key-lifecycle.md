# GPG Key Lifecycle Reference

> Companion reference for `astra-vcs-assist-gpg-key` sub-skill.
> Covers key generation algorithms, keygrip mechanics, gpg-agent configuration,
> and backup strategies in more depth than the sub-skill itself.

## Key Algorithms Comparison

| Algorithm | Strength | Key size | Use case |
|:----------|:---------|:---------|:---------|
| **RSA** | High | 2048–4096 | Universal compatibility |
| **Ed25519** | High (equivalent to RSA 3072+) | Fixed 256-bit | Modern, fast, compact |
| **Cv25519** (ECDH) | High | Fixed 256-bit | Encryption subkey paired with Ed25519 |

**Recommendation for code signing:** Ed25519 for the primary signing key,
Cv25519 for the encryption subkey. RSA 4096 if you need maximum compatibility
with older GnuPG versions (< 2.2).

## Keygrip Mechanics

GnuPG identifies keys internally by a **keygrip** — a 40-character hex string
that is the hash of the key material. Keygrips matter because:

- `gpg-preset-passphrase` identifies keys by keygrip, not key ID
- Git's `user.signingkey` uses the 16-character long key ID (`gpg --list-secret-keys --keyid-format LONG`)
- An Ed25519 key and its Cv25519 subkey have **different** keygrips

To find keygrips:

```bash
gpg --list-secret-keys --keyid-format LONG --with-keygrip <key-id>
```

A typical output shows:

```
sec   ed25519 2026-01-15 [SC] [expires: 2028-01-15]
      ABA1ABA2ABA3ABA4ABA5ABA6ABA7ABA8ABA9ABAA
      Keygrip = 1111222233334444555566667777888899990000
uid           [ultimate] User Name <user@example.com>
ssb   cv25519 2026-01-15 [E] [expires: 2028-01-15]
      Keygrip = BBBBCCCCDDDDEEEEFFFF00001111222233334444
```

The signing keygrip (`1111...`) and the encryption subkey keygrip (`BBBB...`)
are different. Both need to be cached with `gpg-preset-passphrase` if your
workflow touches both (signing commits + decrypting credential files).

## gpg-agent Configuration

File: `~/.gnupg/gpg-agent.conf`

```conf
# Cache passphrase for 24 hours (default: 600 seconds)
default-cache-ttl 86400
max-cache-ttl 604800

# Allow pinentry-mode loopback (for headless operations)
allow-loopback-pinentry
```

After changing this file:

```bash
gpgconf --kill gpg-agent
gpgconf --launch gpg-agent
```

## Backup Strategies

### Recommended backup layout

```
gpg-backup/
├── public-keys.asc              # gpg --export --armor
├── secret-keys.asc              # gpg --export-secret-keys --armor
├── revoke-<key-id>.asc          # gpg --gen-revoke
├── ownertrust.txt               # gpg --export-ownertrust
└── gpg-agent.conf               # configuration file
```

### Full export (with trust)

```bash
KEY_ID="<your-key-id>"

# Public keys
gpg --export --armor $KEY_ID > public-keys.asc

# Secret keys (includes subkeys)
gpg --export-secret-keys --armor $KEY_ID > secret-keys.asc

# Revocation certificate
gpg --gen-revoke $KEY_ID > revoke-${KEY_ID}.asc

# Ownertrust (so the restored key is trusted)
gpg --export-ownertrust > ownertrust.txt
```

### Full import

```bash
gpg --import public-keys.asc
gpg --import secret-keys.asc
gpg --import-ownertrust ownertrust.txt

# Verify
gpg --list-secret-keys --keyid-format LONG
```

## Subkey Separation (Advanced)

Best practice keeps your **master key** offline and uses a **signing subkey**
for daily work:

```
Master key (offline USB)        Signing subkey (daily laptop)
  ├── [C]  Certify only
  ├── [S]  Signing               ───→  [S]  Sign commits
  └── [E]  Encryption            ───→  [E]  Encryption
```

This means: if your laptop is compromised, the subkey can be revoked and a
new one issued, without touching the master key. The master key stays on a
USB drive that only comes out for key management.

Creating a separate signing subkey on an existing key:

```bash
gpg --edit-key <master-key-id>
> addkey
> Please select what kind of key you want:
>   (4) RSA (sign only)
>   (8) RSA (set your own capabilities)
>   (11) Existing key (for adding subkey to smartcard)
> Proposed: (4) for RSA sign-only, or tweak for Ed25519
> Key is valid for? (0) 2y
> save
```

Then export and distribute only the subkey to your daily machine:

```bash
# On the offline machine: export the subkey only
gpg --export-secret-subkeys --armor <key-id> > signing-subkey.asc
```

## Troubleshooting

### "gpg: signing failed: No secret key"

The key ID in `user.signingkey` doesn't match any secret key on this machine.
Run:

```bash
git config user.signingkey
gpg --list-secret-keys --keyid-format LONG | grep -c "$(git config user.signingkey)"
# → 0 means the key isn't installed
```

### "gpg: can't query passphrase in batch mode"

You're using `--batch` without `--pinentry-mode loopback`. Add both:

```bash
gpg --batch --pinentry-mode loopback --passphrase "..." --sign
```

### "gpg-agent is not available in this session"

The gpg-agent daemon isn't running. Start it:

```bash
gpgconf --launch gpg-agent
# Or: eval $(gpg-agent --daemon)
```
