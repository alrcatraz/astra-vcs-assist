# Git Bundle Reference

> Companion reference for `astra-vcs-assist-git-sync` sub-skill.
> Covers git bundle creation, transfer, and application for
> cross-machine synchronisation when network transport is unavailable.

## What Is a Git Bundle?

A **git bundle** is a single file that contains packed git objects and
references (branches, tags). It lets you transfer commits between
repositories without a network connection—via USB drive, SCP, cloud
storage, email attachment, or any file transfer method.

Unlike a tarball of the `.git` directory, a bundle is:
- **Compact** — only the objects needed (delta-compressed)
- **Self-describing** — contains its own pack index
- **Verifiable** — `git bundle verify` checks integrity
- **Pullable** — applied with `git fetch` or `git pull`, like a remote

## When to Use Bundles

| Situation | Bundle | Alternative |
|:----------|:-------|:------------|
| Two machines on the same LAN | `git pull` over network | Bundle if no SSH/HTTP reachable |
| Air-gapped machine | ✅ Ideal | No other option |
| Temporary offline transfer | ✅ Good | USB + bundle |
| GPG signing bottleneck | ⚠️ See below | Set up GPG on the target |

**GPG signing note:** Bundles preserve commit signatures. If you create a
bundle from a machine with signed commits, the signatures survive the
transfer. The target machine doesn't need to have the signing GPG key
installed—the signatures are part of the commit objects.

## Creating a Bundle

### Bundle new commits (incremental)

On the source machine (e.g. desktop with GPG signing):

```bash
cd /path/to/repo

# Bundle only the commits not on the target yet
# (assumes target last synced at tag v1.0.0)
git bundle create /tmp/repo-update.bundle v1.0.0..main

# Also include tags
git bundle create /tmp/repo-update.bundle v1.0.0..main --tags
```

### Bundle entire repository (full clone)

```bash
# Bundle all branches and tags
git bundle create /tmp/repo-full.bundle --all

# Bundle a specific branch
git bundle create /tmp/repo-main.bundle main
```

### Bundle with a specific range

```bash
# Bundle commits between two tags
git bundle create /tmp/repo-v1.1.bundle v1.0.0..v1.1.0

# Bundle commits from the last N commits
git bundle create /tmp/repo-latest.bundle HEAD~10..HEAD
```

## Bundle File Management

```bash
# Size estimate
ls -lh /tmp/repo-*.bundle

# Bundle format is binary, not text
file /tmp/repo-update.bundle
# Output: Git bundle
```

## Verifying a Bundle

Before transferring, verify the bundle is intact:

```bash
git bundle verify /tmp/repo-update.bundle
# Output includes:
# - Number of references (branches/tags)
# - Prerequisite commits (what the target needs to have)
# - Checksum verification
```

## Transferring a Bundle

```bash
# Via SCP/SSH (if available)
scp /tmp/repo-update.bundle user@target-machine:/tmp/

# Via USB
cp /tmp/repo-update.bundle /media/usb/

# Via cloud storage
cp /tmp/repo-update.bundle ~/Nextcloud/shared/

# Via email (if small enough)
# Attach the bundle file to an email
```

## Applying a Bundle

### On a fresh clone (no existing repo)

```bash
# Clone from a bundle
git clone /tmp/repo-full.bundle /path/to/new-repo
cd /path/to/new-repo
git remote add origin <real-remote-url>   # add network remote later
```

### On an existing repo (incremental update)

```bash
cd /path/to/repo

# Pull from the bundle as if it were a remote
git pull /tmp/repo-update.bundle main

# Or fetch (if you want to inspect before merging)
git fetch /tmp/repo-update.bundle main:imported-main
git diff main..imported-main              # review changes
git merge imported-main                   # merge after review

# Or checkout a bundle branch
git checkout -b bundle-update /tmp/repo-update.bundle main
```

### List bundle contents without applying

```bash
# See what references the bundle contains
git bundle list-heads /tmp/repo-update.bundle
# Output:
# <sha1> refs/heads/main
# <sha2> refs/tags/v1.1.0
```

## Complete Workflow Example

**Source machine (desktop, has GPG signing):**

```bash
cd ~/Projects/my-project

# 1. Check what needs syncing
git log --oneline --graph main --since="7 days ago"

# 2. Create bundle of new work
git bundle create /tmp/my-project-update.bundle origin/main..HEAD

# 3. Verify
git bundle verify /tmp/my-project-update.bundle

# 4. Transfer (via USB)
cp /tmp/my-project-update.bundle /media/usb/
```

**Target machine (laptop, no GPG key):**

```bash
cd ~/Projects/my-project

# 1. Check what the source has
git bundle list-heads /media/usb/my-project-update.bundle

# 2. Pull the updates
git pull /media/usb/my-project-update.bundle main

# 3. Verify commits are signed (signatures preserved in bundle)
git log --show-signature -3

# 4. Push to remote (if network available)
git push origin main
```

## Bundle + HTTPS/SSH Fallback Strategy

```text
Preferred:   git push/pull over network (SSH or HTTPS)
Fallback:    git bundle via USB, SCP, or cloud storage
Last resort: git format-patch (email patches)
```

| Method | Speed | Preserves history | Preserves signatures | Requires |
|:-------|:-----:|:-----------------:|:--------------------:|:---------|
| SSH push | ⚡ Fast | ✅ Full | ✅ | Network + SSH key |
| git bundle | 🐢 File transfer | ✅ Full | ✅ | File transfer |
| git format-patch | 🐌 Per-commit | ⚠️ Linear only | ❌ No | Email or file |

## Pitfalls

1. **Large bundles may fail on email/certain file systems.** Bundle files are
   binary and may be rejected by email servers. Use SCP, USB, or cloud storage
   for bundles over 10MB.

2. **Bundle requires prerequisite commits.** If the target doesn't have the
   base commits the bundle was created from, `git pull` will fail. Always
   create bundles from a known reference point (tag, or `origin/main..HEAD`).

3. **Bundle is single-use for incremental updates.** Each incremental bundle
   builds on the previous state. Don't skip steps—apply bundles in order.

4. **`git bundle verify` doesn't check against your local repo.** It only
   confirms the bundle file itself is valid. Whether the bundle can be applied
   to your repo depends on whether you have the prerequisite commits.
