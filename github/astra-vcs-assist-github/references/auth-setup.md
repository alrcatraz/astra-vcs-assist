# Authentication Setup

How to authenticate with GitHub. All approaches assume a Linux environment.

## Git Credential Manager (GCM) — Recommended

```bash
# Install
dotnet tool install -g git-credential-manager 2>/dev/null || \
  echo "GCM may already be installed"

# Configure GPG-backed credential store
git config --global credential.credentialStore gpg
git-credential-manager configure
```

Device code flow (no browser on remote):
```bash
git config --global credential.gitHubAuthModes "device"
git config --global credential.guiPrompt false
script -q -c "timeout 900 git-credential-manager github login --no-ui" /tmp/gcm-login.log
```

## Personal Access Token (most portable)

```bash
echo -e "protocol=https\nhost=github.com\nusername=<user>\npassword=<pat_token>\n" | git-credential-manager approve
```

## Custom pass Credential Helper

For headless environments:

```bash
# Store token in pass
pass insert git/https/github.com/<username>
```

Save as `~/.hermes/scripts/git-credential-pass.sh`:
```bash
#!/bin/bash
set -euo pipefail
PROTOCOL=""; HOST=""; USERNAME=""
while IFS='=' read -r key val || [ -n "$key" ]; do
    [ -z "$key" ] && break
    case "$key" in protocol) PROTOCOL="$val" ;; host) HOST="$val" ;; username) USERNAME="$val" ;; esac
done
[ "$PROTOCOL" != "https" ] || [ "$HOST" != "github.com" ] && exit 0
PASS_PATH="git/https/$HOST/${USERNAME:-oauth2}"
if output=$(pass show "$PASS_PATH" 2>/dev/null); then
    TOKEN=$(echo "$output" | head -1)
    ACCOUNT=$(echo "$output" | grep "^account=" | sed 's/^account=//')
    [ -z "$ACCOUNT" ] && ACCOUNT="${USERNAME:-alrcatraz}"
    echo "username=$ACCOUNT"
    echo "password=$TOKEN"
    exit 0
fi
exit 0
```

## gh CLI Auth

```bash
# Interactive (desktop)
gh auth login

# Token-based (headless)
echo "<token>" | gh auth login --with-token
gh auth setup-git

# Verify
gh auth status
```

## SSH Key Auth

```bash
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
# Add to https://github.com/settings/keys
ssh -T git@github.com
```

## Multi-Account Pitfall — gh active-account mismatch (403 on push)

> Symptom: `push https://github.com/<owner>/<repo>` returns `403 Permission denied to <login-A>` while commit identity (user.name/email) has always been `<login-B>` and signing is fine.

**When `gh auth login` has several GitHub accounts on one machine**, git push credentials come from the **currently active gh account** (`gh auth git-credential` returns the token of the `Active account`):

- `<login-A>` (active)
- `<login-B>` (inactive, yet the real owner of the target repo with push:true/admin)

If the target repo belongs to the **inactive** account, pushing with the active one yields 403 — **a credential-identity mismatch, not a signing or local-git-identity problem**.

### Diagnosis

```bash
# 1. Account list and which one is active
gh auth status                     # Active account: true/false
# 2. The target account's real push permission on the repo (query WITH that account's token, never the active one)
OWNER_TOKEN=$(gh auth token -h github.com --user <owner>)   # explicitly switch account for the token
GH_TOKEN="$ZH_TOKEN" gh api repos/<owner>/<repo> --jq '.permissions'
# push:true → that account can write
```

⚠️ Querying `.permissions` with the active account shows **its own** rights and misleads: `push:false` ≠ the repo is unwritable, only that the active account cannot write.

### Fix (minimal side effects)

```bash
gh auth switch --user <owner>     # point the active account at the repo owner
git push -f <remote> <branch>     # push (succeeds)
gh auth switch --user <original>  # switch straight back; avoid a lasting global change
```

