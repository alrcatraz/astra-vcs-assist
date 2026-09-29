# astra-vcs-assist-git-sync — Remote Synchronisation

*This reference was migrated from the `astra-vcs-assist-git-sync` sub-skill.*

## Trigger Conditions

- Pushing commits to a remote repository
- Pushing to multiple remotes (e.g. GitHub + Gitea)
- Performing a force push after history cleanup
- Transferring commits between machines without network
- Setting up or troubleshooting credential helpers
- Diagnosing push failures

## Overview

```
Local commits
  ├── Single remote    →  git push
  ├── Dual remote      →  git push + push mirror
  ├── Force push       →  git push --force-with-lease
  └── Cross-machine    →  git bundle → transfer → pull
```

## 0. Analyse Remote Topology

```bash
git remote -v
git remote get-url origin
git remote get-url upstream 2>/dev/null || echo "no upstream"
```

| Topology | Strategy |
|:---------|:---------|
| Single remote | Standard push |
| Primary + backup mirror | Dual remote push |
| Upstream + fork | Fork sync |
| All three | Fork + backup combined |

## 1. Single Remote Push

```bash
git push                         # if upstream set
git push origin main
git push -u origin HEAD          # set upstream
git push origin main --tags
```

## 2. Dual Remote Push

```bash
git remote add origin https://github.com/owner/repo.git
git remote add mirror https://git.example.com/owner/repo.git
git push origin main
git push mirror main
```

Or push URL (single push to both):
```bash
git remote set-url --add --push origin https://github.com/owner/repo.git
git remote set-url --add --push origin https://git.example.com/owner/repo.git
git push origin main    # pushes to BOTH
```

### Fork Sync (upstream + your fork)

```bash
git remote add upstream https://github.com/upstream-owner/repo.git
git fetch upstream
git checkout main
git rebase upstream/main
git push origin main
```

## 3. Safe Force Push

```bash
# Safe — rejects if remote has unseen commits
git push --force-with-lease origin main
```

**When acceptable:** After rebase/squash, amending never-shared commits, fixing secrets.

**When NOT:** On shared branches, after published tags, without notifying collaborators.

### After force push

> "Force-pushed `main` to fix commit history after rebase. Please rebase your branches."

## 4. Cross-Machine Sync (Git Bundle)

```bash
# On machine A (source)
git bundle create /tmp/repo-update.bundle origin/main..HEAD
git bundle verify /tmp/repo-update.bundle

# On machine B (target)
git pull /tmp/repo-update.bundle main
```

## 5. Credential Strategies

| Strategy | Security | Headless |
|:---------|:---------|:---------|
| SSH key | ✅ High | ✅ |
| pass + GPG | ✅ High | ✅ |
| One-shot inline | ⚠️ Medium | ✅ |

### SSH key

```bash
ssh-keygen -t ed25519
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
git remote set-url origin git@github.com:owner/repo.git
ssh -T git@github.com
```

### One-shot credential injection

```bash
TOKEN=$(gpg ... --decrypt ... 2>/dev/null | head -1)
GIT_TERMINAL_PROMPT=0 \
  git -c credential.helper="!f() { echo username=user; echo password=$TOKEN; }; f" \
  push origin main
```

## 6. Handling Push Failures

### Rejected (non-fast-forward)

```bash
git fetch origin
git rebase origin/main
```

### Authentication failed

```bash
git config --get credential.helper
echo "protocol=https\nhost=github.com\n\n" | git credential fill
```

### Timeout

```bash
git config http.proxy http://127.0.0.1:7890
git config http.postBuffer 524288000   # 500MB
```

## 7. Post-Push Verification

```bash
git fetch origin
git log --oneline origin/main..HEAD            # should be empty
git diff origin/main HEAD                      # should be empty
```

## Pitfalls

1. **`--force` is dangerous; `--force-with-lease` is safer.** Always fetch first.
2. **Tags not protected by `--force-with-lease`.** Delete and re-push explicitly.
3. **`GIT_TERMINAL_PROMPT=0` required for headless pushes** — prevents hanging.
4. **Credentials in shell history** — on shared machines, use SSH keys.
