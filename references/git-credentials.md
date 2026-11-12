# Git Credential Troubleshooting

*This reference covers GPG-locked credential failure modes, KeePassXC fallback, and Gitea API token auth. For standard credential strategies (SSH, pass+GPG, one-shot), see `references/git/sync/SKILL.md`.*

## Detection

### Failure 1: GPG passphrase lock (GnuPG ≤ 2.4)

| Check | Command | Signal |
|:------|:--------|:-------|
| Agent cache | `gpg-connect-agent 'KEYINFO --list' /by | grep -c "1 1"` | Returns `0` |

Fix: Ask user to cache passphrase once (`gpg -d <file> > /dev/null`), or use `--pinentry-mode loopback`.

Agent self-service (no user round-trip) when the signing key's passphrase lives in the
Hermes agent env file (`~/.hermes/.env`, key `GPG_Key_Alrcatraz` for the fleet identity):

```bash
F=$(mktemp); chmod 600 $F; W=$(mktemp); chmod 700 $W
grep '^GPG_Key_Alrcatraz=' ~/.hermes/.env | cut -d= -f2- > $F
printf '#!/bin/sh\nexec /usr/bin/gpg --pinentry-mode loopback --batch --yes --passphrase-file %s "$@"\n' "$F" > $W
git -c gpg.program=$W commit -m "…"; RC=$?
shred -u $F; rm -f $W
```

Background: fleet commits sign through repo-local `gpg.program`
(`~/.local/bin/gpg-loopback` = `/usr/bin/gpg --pinentry-mode loopback`), which relies
on the gpg-agent passphrase cache. The cache TTL expires inside long agent sessions,
and loopback with no supplied passphrase hangs (`gpg: Sorry, we are in batchmode`) —
the symptom is `git commit` timing out while `hermes --version` style commands are fine.
The env-file route keeps the commit unattended; still tell the user it was used.

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
git push "https://alrcatraz:${TOKEN}@your-forge.example.com/alrcatraz/repo.git" my-branch
```

## Pitfalls

1. **Keyboxd failure ≠ passphrase lock.** Different root cause, different fix. Diagnose before acting.
2. **`credential.helper=` clears all helpers** only when set to empty value. With `-c credential.helper=` (no value), it clears the last configured helper.
3. **Build hosts may have `commit.gpgsign=true` without GPG key.** Set `commit.gpgsign false` per-repo.
