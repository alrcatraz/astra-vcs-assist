# Safe Force Push Reference

> Companion reference for `astra-vcs-assist-git-sync` sub-skill.
> Covers scenarios where force push is acceptable, `--force-with-lease`
> mechanics, recovery from accidental force push, and team notification
> patterns.

## What Force Push Actually Does

A normal push adds commits to the tip of a branch:

```
Normal push:   A---B---C  (local)
               A---B---C  (remote, fast-forward)
```

A force push **replaces** the remote branch tip unconditionally:

```
Force push:    A---B---D  (local, C was rebased away)
               A---B---D  (remote, C is gone)
```

Commits `C` become **orphaned** — they still exist in the object store
for a while (90 days on GitHub) but are no longer reachable from any
branch or tag.

## When Force Push Is Acceptable

| Scenario | Acceptable? | Notes |
|:---------|:-----------:|:------|
| Rebasing a private feature branch | ✅ | No one else has based work on it |
| Squashing WIP commits before PR | ✅ | Standard practice |
| Fixing accidentally committed secrets | ✅ | Do this immediately |
| Correcting authorship on your own commits | ✅ | If no one else has the old commits |
| Rewriting shared `main` branch | ❌ | Notify entire team first |
| Moving a published tag | ❌ | Tags should be immutable |
| Someone else has branched from your branch | ❌ | They'll have divergent history |

## `--force-with-lease` Mechanics

The lease is a **checksum of the remote branch tip** that git stores
locally in your `refs/remotes/origin/main`. On push, git sends this
checksum to the remote. The remote compares it with its actual tip:

- **Match** → Push proceeds (no new commits on remote since you last fetched)
- **Mismatch** → Push rejected (someone else pushed, or you never fetched)

```bash
# If you last fetched and origin/main was at C:
git fetch origin
# origin/main → C

# Locally, you rebased to D:
git rebase -i origin/main    # C becomes D

# The lease says: "remote main should still be at C"
git push --force-with-lease origin main
# ✅ Passes — remote main is still at C
```

```bash
# If someone pushed E in the meantime:
git fetch origin
# origin/main → E (someone pushed while you were offline)

# Your lease says C, but remote is at E:
git push --force-with-lease origin main
# ❌ Rejected — remote main is at E, not C
# error: failed to push some refs to ...
# hint: Updates were rejected because the tip of your current branch
# hint: is behind behind its remote counterpart.
```

### Why `--force-with-lease` is safer than `--force`

`git push --force` sends **no lease check**. It overwrites whatever is on
the remote. If someone pushed E while you were rebasing, `--force` silently
destroys E. `--force-with-lease` catches this and refuses.

### Why `--force-with-lease` is not magic

The lease is only as good as your last `git fetch`. If you haven't fetched
in a while, the lease might match a stale state:

```bash
cd ~/Projects/astra/repo
# last fetch was 2 hours ago
# someone pushed 30 minutes ago
# you haven't fetched since before that:

git push --force-with-lease origin main
# Remote tip is at F, your lease says F (from 2 hours ago)
# But: E was pushed 30 min ago and F contains E
# If you're overwriting F, E goes with it
# ❌ Lease passes! But you're still destroying E
```

**Rule:** Always `git fetch origin` immediately before `--force-with-lease`.

### Using lease with specific ref

```bash
# Check what your lease expects
git push --force-with-lease origin/main

# Override the lease value (advanced: use the exact SHA you expect)
git push --force-with-lease origin/main:<expected-sha>
```

## The Force Push Checklist

Before any force push:

```bash
# 1. Fetch latest
git fetch origin

# 2. Compare what you're about to overwrite
git log origin/main..HEAD          # your commits (what you're pushing)
git log HEAD..origin/main          # their commits (what you're overwriting)

# 3. Confirm no one is depending on this branch
#    (Ask: "Are you working on this branch?")

# 4. Use the safe flag
git push --force-with-lease origin main
```

## Recovery from Accidental Force Push

### On GitHub

GitHub keeps force-pushed commits in the reflog for 90 days:

```bash
# Find the lost commit's SHA
curl -s https://api.github.com/repos/owner/repo/events | \
  python3 -c "import sys,json; [print(e['payload']['head']) for e in json.load(sys.stdin) if 'head' in e.get('payload',{})]"

# If you found the SHA, create a branch from it
git push origin <lost-sha>:refs/heads/recover-lost-commits
```

### On Gitea / self-hosted

Check the remote's git reflog if you have shell access:

```bash
ssh user@git-server
cd /path/to/repo.git
git reflog --date=iso
# Find the lost SHA
```

### If you have the commits locally

```bash
# Your local repo still has the commits if you didn't prune
git reflog | grep "commit: "
git checkout <lost-sha>
git branch recovered-branch
git push origin recovered-branch
```

## Notification Template

After force-pushing a shared branch:

> Force-pushed `main` to clean up commit history after rebase.
> If you have local work based on the old tip, rebase:
> ```
> git fetch origin
> git rebase origin/main
> ```
> If you get errors, check: `git log origin/main..HEAD`

## When NOT to Force Push

1. **On a tag.** Once `v1.0.0` is pushed, it belongs to everyone who pulled
   it. Never `git push --force origin v1.0.0`.

2. **On a release branch** that CI/CD uses. CI may have already deployed
   from that commit. Rewriting it breaks audit trail.

3. **On a branch that has an open PR.** GitHub warns you, but `--force`
   overrides the warning. The PR diff becomes garbage.

4. **Without telling your team.** Even if you think no one is affected,
   send a brief notification. Someone might be mid-work.
