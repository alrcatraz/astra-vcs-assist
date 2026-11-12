# Purging secrets and identities from published history


## Secret purge from public history (git filter-repo)

When plaintext credentials / real IPs / device names were ALREADY pushed to a public
remote (GitHub mirror), **editing the files is NOT enough** — anyone can
`git log -S "<secret>"` the remote history and find them. The repo's GitHub end
must be history-rewritten. Verified end-to-end on astra-aiagent-infra
(36 commits rewritten, 13 IPs + 4 passwords + 11 device keys purged, dual remote
force-push, fresh-clone verified zero residue).

```bash
# 1. BACKUP both workspaces (change-safeguard) + install tool
mkdir -p ~/.astra/backups/<date>-filter-repo
tar czf ~/.astra/backups/<date>-filter-repo/ws.tar.gz -C ~/Projects/astra <repo>
uv tool install git-filter-repo        # then export PATH="$HOME/.local/bin:$PATH"

# 2. Mirror clone ON DISK (never /tmp — tmpfs fills): filter-repo needs a fresh clone
git clone --mirror ~/Projects/astra/<repo> ~/.astra/backups/<date>-filter-repo/mirror.git
cd mirror.git

# 3. Rewrite content AND commit messages together (see pitfall below — they are
#    SEPARATE surfaces; --replace-text does NOT touch messages)
git filter-repo --replace-text ../filter-rules.txt \
                --replace-message ../filter-rules.txt --force

# 4. VERIFY zero residue BEFORE pushing (see pitfalls for the two verification traps)
git log --all --oneline -S "<secret>" | wc -l     # expect 0 — but -S is NOT sufficient,
                                                  # see pickaxe + message pitfalls below

# 5. filter-repo DELETES remotes — re-add from the source repo's `git remote -v`
#    (do NOT guess URLs — gitea is <private-forge-host>, NOT gitea.home.arpa)
git remote add gitea https://alrcatraz:<pass>@<private-forge-host>/<owner>/<repo>.git
git remote add origin https://github.com/<owner>/<repo>.git

# 6. Force-push EVERY branch to BOTH remotes (gitea needs HTTP/1.1)
git -c http.version=HTTP/1.1 push --force gitea main dev
git push --force origin main dev

# 6b. TAGS DO NOT FOLLOW the branch rewrite — local tags and both remotes keep
#     pointing at the OLD dirty commits (verified 2026-08-04: `git log --all -S`
#     hits all came from tags after branches were clean). filter-repo rewrites
#     tags inside the mirror; fetch them back, then force-push to every remote:
git fetch <backup-dir>/mirror.git 'refs/tags/*:refs/tags/*' --force
git push origin --tags --force
git -c http.version=HTTP/1.1 push gitea --tags --force
#     verify tag targets point at rewritten (clean) commits:
#     git tag -l | while read t; do echo "$t -> $(git rev-parse --short $t)"; done

# 7. Re-sync local workspaces to rewritten history
git fetch origin main dev && git fetch gitea main dev
git reset --hard origin/main            # in BOTH the workspace and the private copy
# re-run lifecycle-sync --update afterwards if the private copy uses hook injection
```

### Triage the FILES before choosing the rules (do not lead with bulk replace)

A repo that has leaked private values for a while is rarely "N clean docs + a few stray
strings". It accumulates **internal decision memos** — architecture discussion archives,
deployment matrices, credential how-tos written for ourselves — whose entire body is
internal reference (machine names, service/port inventory, container names, cron job IDs,
internal SHAs, disk/TTL figures, vault entry paths). Applying a replace-rules file to those
file-by-file does not sanitise them: you replace four tokens, the fifth line still names an
internal host, and the reader gets a document that is neither readable nor clean. The user's
framing is the rule — 「这里大量的信息全都是我们内部的，不仅仅是几个名字」.

Before writing a single rule, classify every file that carries a leak and decide its
disposition. The user explicitly prefers this order (看全貌再定方案): an assessment
covering the whole repo first, then per-file decisions — not iterate-file-by-file-then-
discover-the-strategy-was-wrong.

| Class | Definition | Disposition |
|:--|:--|:--|
| **A · technical doc, incidental example** | Generic method write-up; the private value is one illustrative line | `--replace-text` — semantics survive |
| **B · internal memo / ops archive** | Body IS internal reference (machine names + services + ports + IDs + paths throughout) | **delete the file from history** (`--invert-paths --path-glob`) or rewrite it wholesale as neutral architecture prose — never token-replace |
| **C · test fixture / YAML template** | Fake values in tests, placeholder schemas | `--replace-text`; semantics self-preserved (update test assertions in the same pass) |
| **D · mixed** | Technical doc body + one internal section/table | Delete the offending segment, keep the doc; or `--replace-text` if only discrete strings |

Worked giveaways for class B: the file's own opening line says it is a discussion record or
deposition archive; the leaks are not a few strings but a *density* (five machine names, an
IP range, cron IDs, container names, internal SHAs on one page). The `.bak` twins of such
files are always class B — delete, do not clean.

**Deliverable shape for the assessment**: per file — path, which refs carry it, leak summary,
class, disposition, one-line reason — plus class counts. That table is what the user rules
on; only after it do you write rules. Expect the assessment to surface leaks your initial
scan missed: a repo-wide classification pass reads whole files, so it catches internal
tokens that a keyword list did not contain (see the completeness pitfall below).

Automate the class-B detection start: `for f in $(git ls-files); do n=$(git grep -cE
'<internal-token-alternation>' "$f"); done` — a file with a HIGH hit count across MANY
distinct internal tokens is class B; one with a single incidental hit is class A.

Pitfalls (all hit for real, 2026-08-04):

- **`git log -S` pickaxe semantics**: 0 commits ≠ string absent. `-S` reports commits
  where the COUNT of occurrences changed — a string present since the root commit
  shows 0. Verify with `git grep -c "<secret>" <branch>` on the latest commit, or
  **fresh-clone from the ACTUAL public remote** (`git clone --depth 30 <github-url>`
  then scan) — the local mirror only proves the rewrite ran, not what GitHub serves.
- **`--replace-text` rewrites file content ONLY — commit MESSAGES are a separate surface.**
  A message body can carry the exact string the content rules removed ("protocol, Gitea/<host>"
  in a commit body) and will pass a `--replace-text` content scan clean. Scan messages
  separately before pushing: `git log --all --format='%H %s%n%b' -S "<secret>" | wc -l`
  is still pickaxe-blind for message-only text — use
  `git log --all --format='%H%n%s%n%b' | grep -c "<secret>"` (grep the raw message stream,
  not `-S`). To REWRITE messages, pass `--replace-message <same-rules-file>` alongside
  `--replace-text` — one invocation, both surfaces. If a rewrite already ran without it,
  re-clone a fresh mirror and rerun with both flags (second pass on a rewritten repo
  misbehaves — see second-pass rule below).
- **Merge-introduced content is invisible to pickaxe and to tip-tree grep.** A string
  that enters history only via a merge commit (neither parent's diff added it, or it
  arrived through a merge-side branch) shows 0 hits in `git log -S` AND can be absent
  from every branch tip while still present in history objects. The only reliable gate
  is a FULL-OBJECT scan over every reachable blob. Avoid `$()` (terminal guard mangles
  command substitution) — use the plain-pipe form:
  `git rev-list --objects --all | awk '{print $1}' | xargs -r git grep -l "<secret>"`
  (or clone fresh and scan that). Run it BEFORE the approval to push, not after.
- **Scan command form — avoid `$()`/`$(git ...)` for per-token counts**: the terminal
  guard mangles `$()` command substitution in loops, so `n=$(git rev-list --count
  -S "$s" $t)` silently printed usage errors / empty counts instead of numbers. The
  reliable form is a plain pipe count:
  `printf '%-18s -> ' "$s"; git log --all --format=%H -S "$s" | wc -l`.
  `git rev-list --count -S` also mis-orders args into usage text — prefer
  `git log --format=%H -S <s> <ref> | wc -l` everywhere.
- **`git log --all` includes TAGS**: after a rewrite, branch pickaxe may be 0 while
  `--all` still hits — the residue lives in tag refs (or a stale `refs/original/`).
  Diagnose with `git tag --contains <dirty-commit>` / `git branch -a --contains` to
  find which ref carries the old commit, then fix that ref (see step 6b) instead of
  assuming the rewrite failed.
- **Verification with `| head; echo $?` is a lie**: `$?` is head's exit code (always 0).
  Run grep bare or check `grep_exit=$?` on the grep command itself.
- **Your leak list will be incomplete — build it from a token-alternation scan over the
  whole object store, not from the strings you already know about.** A hand-written keyword
  list finds exactly the values someone already spotted; the ones that matter are the ones
  nobody listed. Scan for CLASSES: every RFC-1918 range (`10\.`, `172\.1[6-9]\.|2[0-9]\.|3[01]\.`,
  `192\.168\.`), every dotted-host pattern (`[a-z0-9-]+\.(internal|local|lan)`), every
  internal forge FQDN root, AND the bare device/machine-name stems (`<host-a>`, `<host-c>`, the
  NAS model string, `<host-d>`) — device names leak in file paths, test fixtures and
  `registry.yaml` comments exactly as easily as IPs do. Run the scan over
  `git rev-list --objects --all`, then over `rev-list --objects <each-ref>` separately for
  refs the all-scan already cleaned. Expect the full-object scan to surface a network of
  internal references beyond the seeds (`NB 网段` as a named concept, container names,
  internal git SHAs, cron job IDs) — treat that as the normal outcome, not scope creep.
  Two consequences follow: (a) the token list is derived from the scan, not authored first;
  (b) it is regenerated after each rewrite until a pass returns zero, since each pass
  reveals the next class.
- **Ambiguous tokens need full-context rules, not bare strings**: `star` is a device
  name AND appears in GitHub stars badges / star-history charts — use regex rules
  (`regex:star@`, `regex:jump_star`, `regex:\\| star \\|`) not literal `star`.
  `openwrt` (lowercase device key) vs `OpenWrt` (uppercase system name) — replace
  only the lowercase; verify the uppercase survived (expect >0 commits).
  **Context-split rules for system/device homonyms** (astra-sre 2026-08-04):
  `openwrt` is BOTH a device key AND a system name / skill trigger word
  (`openwrt-proxy-stack`, `openwrt-tproxy-setup.md`) — a bare lowercase rule
  mangles docs. Use anchored regexes that only hit the device-key context:
  `regex:name: openwrt==>name: <router>` and `regex:/openwrt）==>/<router>）`,
  then verify the technical usages survived (`git log -S openwrt` still >0).
- **Keep RFC network ranges and Docker bridge examples OUT of the rules**: scanning
  found 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10 — these are iptables RETURN-list
  constants, not real infra; 172.17.0.1 / 172.19.0.1 are Docker bridge examples
  (`e.g.` teaching context). Replace host IPs only (192.168.0.20 yes, 192.168.0.0/16 no).
  Check each IP's surrounding context before adding it to the rules.
- **Tracked `*.bak` files are pre-sanitisation residue** (astra-sre public end had
  SKILL.md.bak / tuning-guide.md.bak with real IPs committed): purge them from ALL
  history with the rewrite itself — add `--invert-paths --path-glob '*.bak'` to the
  filter-repo invocation (not a separate commit, or they survive in old commits).
  Grep the tree for `.bak` BEFORE rewriting; live-file `.bak` references
  (`cp file file.bak`) are commands, not residue — those are fine.
- **Second-pass rule additions: re-clone a FRESH mirror and rerun the full rewrite**
  (idempotent), do NOT run filter-repo twice on the same mirror — filter-repo
  expects a clean clone and a second pass on a rewritten repo misbehaves.
- **Wrong-branch `reset --hard` after a failed `git checkout`**: syncing the local
  public branch after a force-push, `git checkout public` printed "Aborting" (worktree
  had uncommitted changes) but the following `git reset --hard origin/public` ran on
  the STILL-CHECKED-OUT branch (main) and clobbered it to the rewritten history.
  Check `git branch --show-current` AFTER any failed checkout before resetting; the
  private copy's main was restored with `git reset --hard gitea/main` — gitignored
  files (devices.yaml) survive, but uncommitted lifecycle-hook injections do not.
- **Public-end branch inventory after rewrite**: a dual-end repo (private main →
  gitea, sanitised public → GitHub) must have ONLY `public` on GitHub. `git ls-remote
  --heads origin` may still show a stale `main` (pre-split era) whose history carries
  the old secrets. Confirm it's fully contained (`git merge-base --is-ancestor main
  public`) then `git push origin --delete main`; fix the dangling
  `refs/remotes/origin/HEAD` with `git remote set-head origin public`.
- **Teaching examples are fine to keep**: placeholder-style docs (`192.168.1.100`,
  `secret123`) are not real secrets — excluding them from the rules avoids mangling
  legitimate docs.
- **Rule file order**: passwords first (L5 MUST NOT), then IPs, then device keys,
  then ambiguous-token regexes. Test each class with a `git log -S` count after.
- **Don't create the verify clone inside the repo being verified** — the `??` untracked
  dir pollutes `git status` and then gets swept by a later `git add -A`.
- **Backup mirror stays as rollback** (616K for 36 commits) — keep it until the user
  confirms the public end is clean.
- **Exposed passwords should be rotated** — rewriting history removes retrievability
  but the secret was public; flag rotation to the user, never rotate device passwords
  yourself (user discipline: ask first). For a LAN-scoped credential the user may weigh
  rotation as unnecessary and accept rewrite-only — present that trade-off, don't assume.
- **Prefer `--invert-paths --path <file>` over `--replace-text` when the file has a clean
  pre-leak ancestor**: strip the whole file from all history, then restore the pre-leak
  version (`git show <leak-commit>^:<path>`) as one new signed commit. No `<REDACTED>`
  noise survives anywhere and the restored blob provably predates the leak.
- **Local safety tags/branches pin dirty blobs through a rewrite**: any ref still pointing
  at old commits keeps the secret reachable *inside* the rewritten repo. Delete backup tags
  BEFORE rewriting — the out-of-repo bundle/mirror is the real rollback, not in-repo refs.
  Record deletions via `git notes add -f -m "recover via <bundle path>" <sha>` for traceability.
- **filter-repo needs interactive stdin even with `--force`**: its sanity check calls
  `input()` and dies with `EOFError` under non-TTY execution. Pipe an affirmative:
  `echo y | git filter-repo ... --force`. If it aborts mid-way the repo is left stripped of
  remotes with `.git/filter-repo/already_ran` present — recover by restoring refs from the
  backup bundle (`git update-ref refs/heads/<b> <sha>`), re-add remotes from saved
  `git remote -v` output, `rm -rf .git/filter-repo`, then rerun properly.
- **Hex-hash false positives in residue scans**: a secret substring can collide inside
  sha256 digests in lockfiles (`uv.lock`/`package-lock`). When `git grep` hits only
  `hash = "sha256:..."` or `packages/` URL lines, that is a collision, not a leak — confirm
  by filtering those line shapes before concluding residue exists.
- **A gateway/MCP bridge can mask a healthy server as broken — isolate layers before
  fixing the deep one**: if tools/list succeeds but every tools/call to ONE upstream
  fails with -32602 while sibling servers through the SAME bridge work, the fault is the
  client's registration entry (stale merged tool table / wrong transport), not the bridge
  or the upstream. Re-register the client directly against the upstream endpoint and
  restart; verify with a raw curl of the upstream's own SSE/HTTP path first so you never
  chase a phantom bug in the middle layer.
- **Force-push approval may time out silently on messaging platforms**: if a gated push
  returns "timed out without user response", do NOT rephrase or split the command —
  report the exact pending command plus current completed-state so the user can approve
  explicitly in their next message.
## Purging an identity or hostname from history

Four traps, each hit in a real fleet-wide purge; all four cost a wasted run.

1. **`filter-repo` blocks on a continuation prompt after any aborted run.** A
   failed invocation leaves `.git/filter-repo/`; the next run asks "Treat this
   run as a continuation of filtering in the previous run (Y/N)?" and dies with
   `EOFError` under a non-interactive shell — leaving history untouched while
   the script reports success. Fix: `rm -rf .git/filter-repo` and run with
   `</dev/null`, and **never send filter-repo's stderr to /dev/null**: the
   abort was invisible for a whole batch because of `>/dev/null 2>&1`, and the
   "tree unchanged" check then passed vacuously (nothing had changed at all).
2. **`filter-repo` removes the `origin` remote.** Re-add it before pushing, or
   every push fails with a misleading "correct access rights" message because
   the URL resolved to nothing.
3. **`git rebase -r --root --exec 'git commit --amend -S'` duplicates commits**
   on PR-merge topology: a 37-commit repo came back as 74, with trees and merge
   counts per branch still equal — so a naive tree/merge check passes while the
   log is polluted. Do not use rebase to add signatures to history.
4. **`git filter-branch --commit-filter 'git commit-tree -S "$@"' -- --all`
   preserves the DAG exactly** (same trees, same commit counts, same merge
   counts) and signs every commit. Two caveats: it rewrites tags too, and
   piping its output through `head` sends SIGPIPE and silently aborts the
   rewrite. Clean `refs/original/*` afterwards or the repo carries a duplicate
   set of refs (`git rev-list --count --all` then reports double).

Serverside, distinguish the two read-only shapes before assuming a permissions
bug: an **archived** repository rejects every push with a bare
`403 ... requested URL returned error: 403` regardless of `admin: true`, while
**branch protection** answers `remote: error: GH006: Protected branch update
failed for refs/heads/main` and names the ref. And a repo's own `pre-push`
hook refusing to push a private branch to a public remote is working as
designed — not a failure to fix.

Before rewriting, record what must survive: per-branch tree hash, commit count
and merge count, plus `git ls-remote --heads <url>` as the rollback facts.
`filter-repo` drops GPG signatures on everything it rewrites; state that cost
before starting, and sign in a second pass with the method above.
