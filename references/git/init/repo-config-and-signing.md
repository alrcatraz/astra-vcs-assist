# Per-repo git configuration, GPG binding, ignore rules, remotes

## 4. Per-Repository Git Configuration

### Essential settings

```bash
cd /path/to/repo

git config user.name "Your Name"              # or GitHub username
git config user.email "your.email@example.com" # must match GPG key and GitHub email

git config user.signingkey <key-id>            # from gpg --list-secret-keys
git config commit.gpgsign true
git config tag.gpgsign true

git config pull.ff only                        # prefer fast-forward only
git config push.autoSetupRemote true           # auto-set upstream on first push
git config push.default current                # push current branch to matching remote
```

### Global fallbacks (only for single-identity setups)

```bash
git config --global user.name "..."
git config --global user.email "..."
```

### Credential helper

```bash
# Option A: Git Credential Manager (GCM) — cross-platform UI
git config credential.helper "manager"         # Windows/macOS
git config credential.helper "manager-core"    # Linux with GCM

# Option B: pass (Linux, password-store)
git config credential.helper "store --file ~/.git-credentials"  # simple, plaintext ⚠️
git config credential.helper "!f() { cat ~/.git-credentials; }; f"  # custom

# Option C: GPG + pass on Linux (recommended for headless)
git config credential.helper "!/path/to/git-credential-pass.sh"

# Set default GitHub username (avoids GCM account picker)
git config credential.https://github.com.username <username>
```

## 5. GPG Key Binding

Ensure the GPG key selected matches the git identity:

```bash
# Verify match
echo "GPG email:"
gpg --list-key $(git config user.signingkey) --keyid-format LONG | grep uid
echo "Git email:"
git config user.email

# They MUST match — otherwise GitHub shows "Unverified" on commits
```

## 6. .gitignore

### Language-specific

```bash
# Fetch from GitHub's official templates
curl -sL https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore \
  -o .gitignore
```

Add project-specific entries at the bottom:

```gitignore
# IDE
.idea/
.vscode/
*.swp

# Build output
dist/
build/
*.egg-info/

# Environment
.env
.venv/

# Agent local instructions (sensitive — never published)
AGENTS.local.md
```

### Global gitignore (for all repos)

```bash
git config --global core.excludesFile ~/.gitignore_global
cat >> ~/.gitignore_global << 'EOF'
.DS_Store
Thumbs.db
*.log
EOF
```

## 7. Remote Configuration

### Standard setup (single remote)

```bash
git remote add origin https://github.com/owner/repo.git
git branch -M main
git push -u origin main
```

### Dual remote (mirror)

```bash
git remote add origin https://github.com/owner/repo.git
git remote add mirror https://git.example.com/owner/repo.git
git push -u origin main
git push -u mirror main
```

See `astra-vcs-assist` → `references/git/sync/SKILL.md` for dual-remote push workflow.
