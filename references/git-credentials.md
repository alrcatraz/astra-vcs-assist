# Git Credential Troubleshooting

*This reference covers GPG-locked credential failure modes, KeePassXC fallback, and Gitea API token auth. For standard credential strategies (SSH, pass+GPG, one-shot), see `git-sync.md` §5.*

## Detection

### Failure 1: GPG passphrase lock (GnuPG ≤ 2.4)

| Check | Command | Signal |
|:------|:--------|:-------|
| Agent cache | `gpg-connect-agent 'KEYINFO --list' /by | grep -c "1 1"` | Returns `0` |

Fix: Ask user to cache passphrase once (`gpg -d <file> > /dev/null`), or use `--pinentry-mode loopback`.

### Failure 2: GnuPG 2.5+ keyboxd failure

GnuPG 2.5+ uses `keyboxd`. Private keys register but agent returns ENOENT.

| Check | Signal |
|:------|:-------|
| `gpg --list-secret-keys` | Keys visible |
| `gpg --decrypt $FILE` | `public key decryption failed: No such file or directory` |
| `ls /run/user/$UID/gnupg/` | `S.keyboxd` socket present |

Fix: Skip GPG entirely → KeePassXC fallback (below).

## Resolution Paths (escalating)

### 1. `gh auth git-credential` (one-shot)

```bash
git -c credential.helper='!gh auth git-credential' push origin main
```

Requires `gh` authenticated: `gh auth login --hostname github.com --web`

### 2. KeePassXC fallback

```bash
keepassxc-cli search ~/Documents/KeePassXC/Combined.kdbx <entry> <<< "$KEEPASS_PASSWORD"
TOKEN=$(keepassxc-cli show -s ~/Documents/KeePassXC/Combined.kdbx <path> <<< "$KEEPASS_PASSWORD")
GIT_TERMINAL_PROMPT=0 \
  git -c credential.helper= \
  clone https://USER:$TOKEN@host.tld/owner/repo.git /tmp/repo
```

### 3. SSH conversion

```bash
git remote set-url origin git@github.com:owner/repo.git
```

### 4. Gitea API token auth

```bash
# Get token from fact_store or GPG store
TOKEN="<api-token>"
# Push via HTTPS+token:
git push "https://alrcatraz:${TOKEN}@git01.wrt.astra-lab.org/alrcatraz/repo.git" my-branch
```

## Pitfalls

1. **Keyboxd failure ≠ passphrase lock.** Different root cause, different fix. Diagnose before acting.
2. **`credential.helper=` clears all helpers** only when set to empty value. With `-c credential.helper=` (no value), it clears the last configured helper.
3. **Build hosts may have `commit.gpgsign=true` without GPG key.** Set `commit.gpgsign false` per-repo.
