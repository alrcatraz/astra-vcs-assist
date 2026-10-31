# History rewrite (credential purge) — verified procedure

Validated on astra-knowledge-base-mcp v1.4.3 (2026-09-24): purged leaked
defaults from `scripts/run.sh` across full history, both remotes.

## Steps that matter

1. **Backup FIRST**: `git bundle create … --all` + `git clone --mirror`.
   Verify the bundle. Delete local backup tags pinning leaky blobs *before*
   rewriting, else the purge is cosmetic (they keep objects reachable).
2. `git filter-repo --invert-paths --path <file> --force` — non-interactive
   shells must pipe `y` to its sanity check (`echo y | git filter-repo …`).
   It drops ALL remotes and refuses non-fresh clones → re-add remotes after.
3. Restore the stripped file at tip from a leak-free ancestor
   (`git show <pre-leak-sha>:<path>`), as a normal signed commit.
4. Tags auto-retarget to rewritten commits; verify each tag tree is clean,
   then add a new release tag for the rewritten state.
5. **Force-push needs protection relaxed per-platform**:
   - Gitea: admin API `DELETE`+`POST /repos/{repo}/branch_protections[/main]`
     with `enable_force_push:true`; save original JSON first and RESTORE after
     (the singular `/branch_protection/main` endpoint 404s — use plural).
   - GitHub classic protection blocks even admins when created via API with
     allow_force_pushes:false. For mirror repos: delete remote branch
     (`push origin :refs/heads/X`; the default branch can't be deleted — push
     the rewritten main directly if force is permitted, otherwise switch
     default temporarily), then recreate protection
     (`gh api -X PUT repos/…/branches/main/protection`).
6. **Server-side GC is mandatory and ref-aware**. Force-push alone leaves old
   objects reachable from PR-head refs:
   - GitHub: `refs/pull/*/head` are read-only via API but vanish when the
     branch is deleted + recreated.
   - Gitea: keeps `refs/pull/N/head` which SURVIVE force-push. Prune requires
     shell into the bare repo — on Synology containerised Gitea:
     `sudo /usr/local/bin/docker exec -u git gitea bash -c 'cd
     /data/git/repositories/<user>/<repo>.git && git update-ref -d
     refs/pull/N/head && git reflog expire --expire=all --all && git gc
     --prune=now'`. Quoting hell: base64-encode the inner script through ssh.
7. **Prove it per remote**: fresh `git init` dir, `git fetch --depth=1 <url>
   <leaky-sha>` → must fail with OBJECT-ABSENT. A successful shallow fetch of
   an unknown sha means the object is still served.
8. Gitea temp-admin gotchas (CLI-created helper account):
   - `admin user create-admin` accepts NO flags in current builds — use
     `admin user create --username X --password Y --email Z --admin`.
   - CLI-created users get must-change-password → all APIs 403 "You must change
     your password" until `change-password --must-change-password=false`.
   - `generate-access-token --raw` tokens do NOT work as `Authorization: token`;
     Basic auth with the account works fine.
   - Token names must be unique per user (retry with a fresh name on
     "has been used already").
   - DELETE the temp account when done (`admin user delete --username X`) —
     deleting the user invalidates its tokens.

## Residual-risk framing (for the owner)

Rewrite + GC removes passive grep hits on both forges permanently, but anyone
who cloned/forked earlier retains copies, and platform support may have
internal snapshots. Purge is hygiene, not revocation — leaked credentials should
still be rotated when feasible. LAN-scoped credentials lower urgency, not to zero.
