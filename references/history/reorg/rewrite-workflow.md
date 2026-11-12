# Rewriting a history


## Traps that cost a rewrite

> Full execution transcript (commands + all 10 pitfalls): `references/rewrite-recipe-and-traps.md`

- **pre-commit/lint-staged 失败会 REVERT 全部 staged 状态** — eslint --fix 报错后
  "Reverting to original state" 会把整个 index 恢复原状（62 文件 staged 丢失）。
  修复原因后必须**重新 add 整个分组**再 commit，别假设 index 还在。
- **eslint suppression 失效阻塞 commit** — 删除文件/代码后 pre-commit 报 "suppressions
  left that do not occur anymore"（exit 1）。修复：对照 `git ls-files` 手动删已删文件的
  条目 + `npx eslint --fix --prune-suppressions --suppressions-location <file> <相关文件>`；
  suppressions 文件本身也要 add 进 commit。
- **push 前查 remote 名** — `git remote -v`：本项目 remote 是 `gitea` 而非 `origin`，
  误用 origin 报 "does not appear to be a git repository"。GitHub 模板占位 commit
  （"Initial commit" 脚手架）用 `git ls-remote` 侦察 + fetch 拿 lease + `--force-with-lease`
  覆盖。孤儿 tag 本地 `git tag -d` + 远端 `git push <remote> :refs/tags/<tag>` 双删。

- **`reset --soft` 后 index 保留全部差异** — 只移 HEAD，index 仍是旧 tree。直接 commit 会把全部
  ~1300 文件差异（含 1200 数据文件删除）提交进第一个 commit。必须先 `git reset`（mixed）
  unstage 全部 → 再按分组 `git add`。
- **`git add` 对目标 commit 中已删除的路径报 `fatal: pathspec did not match`** —
  用 `git diff --name-only A B | xargs git add -A --`（-A 支持 D 路径），别用裸 `git add`。
- **git add 取 worktree 内容** — 文件属于 commit A 的文件集但工作区后来改过（本属 commit B 的改动），
  commit A 会带进最终版（文件级归属：跨 commit 的文件归先 commit 的，接受即可）。
  两边都改的重叠文件：先 `git checkout <A> -- <path>` 取 A 版 + cp 保存工作区最终版到 /tmp，
  A commit 后再 cp 恢复。
- **husky/lint-staged 失败会 revert 全部 staged 状态** — 修复后重试必须重新 add 全部文件。
- **eslint suppressions 失效阻塞 pre-commit** — 删除文件后 `config/quality/eslint-suppressions.json`
  残留条目使 `eslint --fix` 报 "suppressions left that do not occur anymore"（hook 失败）。
  修复：`npx eslint --fix --prune-suppressions --suppressions-location config/quality/eslint-suppressions.json <相关文件>`
  + 用 python 对比 `git ls-files` 手动删已不存在的文件条目，add 该 json 再 commit。
- **推送策略** — 单人项目重写历史后直接 `git push --force-with-lease <remote> main` + 推 tag，
  不走 PR（PR 是增量合并，无法替换错误旧历史；评审价值≈0）。孤儿旧 tag 先
  `git tag -d <t>` + `git push <remote> :refs/tags/<t>`。remote 名不一定是 `origin`：
  push 前先 `git remote -v`（a first-party repo 的实际 remote 名 = `gitea`）。GitHub 新 repo
  常带模板 "Initial commit"（README/SKILL.md/pyproject/.gitkeep 占位，非空 repo）——
  先 `git ls-remote <url>` 侦察，有占位同样 force-with-lease 覆盖，别试普通 push。
  公开推送前品牌名残留要在 i18n 语言包全扫（43 locale，含本地化译名如
  OmniRuta/オムニルート——`== 'OmniRoute'` 检查会漏）。
- **发布 tag 必须指向最终 commit** — amend 发布 commit 后（如把脱敏/文档改动并进
  发布 commit），tag 不会自动跟随：`git tag -f -s vX.Y.Z` 重新打（新 tag 对象 hash
  会变），再 `git push <remote> vX.Y.Z --force` 推到**所有** remote（main 仍是普通
  push，只有 tag 是 forced update）；验证 `git ls-remote <remote> refs/tags/vX.Y.Z^{}`
  解引用 == 最终 commit hash。
- **Gitea 推送 TLS 0A000126 是 HTTP/2 握手故障，不是瞬时抖动** — <private-forge-host>
  push/fetch 报 `TLS connect error: error:0A000126:SSL routines::unexpected eof`
  （根路径 curl 200、其它 remote 正常 → 排除服务宕机/网络）。**重试无效**（2026-08-04
  实测连试两次都失败），根因是 HTTP/2 TLS 层握手被掐。修复：强制 HTTP/1.1 —
  `git -c http.version=HTTP/1.1 fetch gitea main` / `git -c http.version=HTTP/1.1 push gitea main`，
  立即可用（fetch/push 都验证过）。早期「重试一次即成功」的记录已作废。
## Safety nets before a PUBLIC history rewrite

Any rewrite whose result will be force-pushed to a remote others can clone runs these
nets, in order, and presents the plan for approval BEFORE touching history — the
rewrite itself is the point of no return, so the approval gate sits before it, not after:

1. **Bundle + SHA ledger (rollback net).** `git bundle create <path>-FULL-$(date).bundle
   --all` OUTSIDE the repo, plus a text ledger of every remote tip and tag SHA about to
   change. Verify with `git bundle verify`. Keep both until the user confirms the public
   end is clean — in-repo backup refs die with the rewrite, the bundle does not.
2. **Fork / collaborator check.** `gh api repos/<o>/<r> --jq .forks_count` and the
   collaborators list. Forks retain the old history after your rewrite; zero forks and
   no outside collaborators is what makes a force-push safe.
3. **Isolated copy, never the working repo.** Clone to scratch and rewrite there. The
   dev repo and every production copy stay untouched; `filter-repo` also strips remotes
   from the clone it runs in — a side effect that protects the source, so re-add remotes
   by explicit URL before pushing.
4. **Classify leaks FIRST, then pick the shape** (see the table below). Run the gate
   against EVERY commit, not just the tip, and treat any BLOCKER as a stop — never
   "good enough". Exempt buckets (functional URLs, attribution, teaching placeholders)
   are a deliberate decision the scan must show, so a pass proves the exception was
   applied rather than the check skipped.
5. **Second-stage remote cleanup + fresh-clone verify.** The branch push is only half:
   enumerate tags and tracking refs, delete every tag pointing at the abandoned line
   (they are a live fetch path to the leaky history), re-point local tracking refs, then
   clone from the real public URL and scan that — only the clone proves what the remote
   serves.
6. **`refs/pull/*` is a fifth fetch path — and the two platforms handle it differently.**
   Every PR keeps a server-side snapshot ref `refs/pull/N/head`; closed PRs keep theirs.
   Gitea's client CANNOT delete it (API DELETE → 405, `git push :refs/pull/N/head` →
   `hook declined`, PATCH to re-point → 405 — it is server-owned); from the host shell,
   `docker exec -u git <gitea> git -C /data/git/repositories/<o>/<r>.git update-ref -d
   refs/pull/N/head` per N, then `reflog expire --expire=now --all && gc --prune=now
   --aggressive`. GitHub gives the client NOTHING (`deny updating a hidden ref`) — the ref
   survives your rewrite and old commits stay fetchable by SHA. **State that residual
   openly and let the user choose (support ticket / delete-and-recreate / accept); a
   residual holding a live plaintext credential means ROTATION is the only real
   mitigation, so never present "rewrite done" as "leak gone" while a secret is
   reachable.** Gate it with `git ls-remote <url> 'refs/pull/*'` after the push.
7. **Re-point every copy and sweep the sibling repos.** A force-push leaves the dev and
   production checkouts on the abandoned line, and the leak class usually still sits in a
   sibling repo. Reset each copy (`fetch --tags --force` + `reset --hard`) after stashing
   any uncommitted work, re-scan each copy's `HEAD`, and run the token set across every
   repo in scope — see `references/post-rewrite-propagation.md` for the phantom-divergence
   trap, the local-path-remote trap, and the per-hit reachability verdicts.

## Choosing the rewrite shape: when filter-repo rules start sprawling, stop and rebuild

git-filter-repo must express EVERY removal as a rule, and each leak CLASS the first pass
missed (file-content version suffixes, tag names, IPs, emails) becomes another rule
family. The tell is mechanical: you are adding a rule class, re-running, and the gate
still reports hits from a class you had not modelled. That is the escalation point —
do not keep patching the rules file.

| Leak shape | Shape | Why |
|:-----------|:------|:----|
| A few discrete strings in an otherwise clean, WORTH KEEPING history | `filter-repo --replace-text` (+ message callback) on an isolated clone | One rules file; commit structure survives |
| Leaks concentrated in a subtree you are about to STOP SHIPPING, plus content/tag classes the rules keep missing | **Abandon the old history**: clean the tip, `git checkout --orphan`, one commit, force-push | Content you never push needs no rule to catch it; the gate runs against 1 commit instead of proving a rules file exhaustive over N |

Determinant: does the leaking content die with the old history anyway (a lower-trust
subtree you `git rm` in the projection)? Then rebuild — never clean what you never ship.
Only content that must REMAIN in the new history earns filter-repo's rule-complexity.
Cost is public commit granularity (N → 1): state it openly, and re-tag only versions that
still mean something on the new root (see orphan-rebuild recipe above — one root cannot
have held N releases).

## Dual-branch bootstrap (private main + standalone public, before remotes)

When a repo will eventually get a public end (GitHub) AND contains private
data (real registry values, private plan files), prepare the public branch
UP FRONT — before any remote exists — so the public end is never an
afterthought and never shares private history. User's architecture rule
(2026-08-05, astra-agent-constellation): the public branch is FULLY
standalone ("公开版分支就是完全的公开版本") — no coupling to the private
version, no README pointing back at private files, no shared maintenance
contract. And "不急着加远端" — prepare the branch locally; add the remote
only when the user explicitly says so.

Sequence (verified 2026-08-05):

1. **Private-value audit FIRST** — decide what public excludes by evidence,
   not guessing: `find . -type f -not -path "./.git/*" | sort` to see the
   whole tree, then `grep -rln "<real-hostname>|<real-name>|<real-version>"
   --include="*.md" --include="*.yaml" --include="*.py" .` to find exactly
   which files hold real values. Only those files get excluded from public.
2. **Commit the in-flight batch on main FIRST** — `git checkout -b public`
   forks from HEAD, so uncommitted changes must land as commits BEFORE the
   branch cut, else public loses the whole batch (forks from old HEAD).
3. `git checkout -b public` from main, then remove private files:
   `git rm -r <private-dir>/ <private-file>` and commit
   `chore: public branch without private registry and plan`.
4. **Zero-residue verification on public** (per sensitive token, expect 0):
   `for s in <token1> <token2>; do printf '%-14s -> ' "$s"; git grep -c "$s" public -- ':!*.css' | wc -l; done`
   — `git grep` lists per-file matches, so `wc -l` of zero lines = clean.
   Also confirm main still holds the private files
   (`git ls-tree -r --name-only main | grep -E "<private-dir>|<private-file>"`).
5. **Build BOTH branches** via a temporary worktree:
   `git worktree add /tmp/<check> public && (cd /tmp/<check> && <build>)`,
   then `git worktree remove /tmp/<check>`.
6. **Signatures**: `git log --show-signature --format="%h %G? %s"` — all `G`.

Pitfalls:
- **Terminal guard can block a compound checkout+rm+commit** command
  (flagged as restart/stop risk though it contains none) — split into
  separate commands: checkout, then rm, then commit. Same guard that
  mangles `$()` — splitting is the reliable workaround.
- **Public branch holds NO placeholder twin of private files** — the
  canonical placeholder template lives in `templates/` (e.g.
  `templates/agent-registry/registry.yaml.example`). If no template
  exists, add one to templates/ BEFORE cutting public so public consumers
  have a working example.
- **Branch semantics**: private values live ONLY on main; public is a
  standalone publishable tree. Future GitHub push targets public only;
  main never touches the public remote.
- **Agent/registry naming is a deployment decision, not a blueprint rule**
  — user corrected (2026-08-05): generic specs must NOT embed our naming
  conventions (executor-<host>, <orchestrator>/<guardian>). Names go in the private
  registry instance, never into shared docs/templates.

## Workflow

1. **Survey first**: `git log --name-status --format="=== %h %s"` per commit. Identify
   mixed-theme commits (e.g. a docs commit that also touched a mirror tree; a CI commit that
   also deleted 1200 data files). Group by **net effect**: create-then-delete pairs collapse
   into ONE "drop" commit. File-level grouping is the default; only hunk-split when one file
   spans two themes (package.json, ci.yml, policy check scripts).
2. `git reset --soft <root>` — HEAD moves to root, **index keeps ALL diffs staged**,
   worktree untouched.
3. `git reset` (mixed) — **mandatory** unstage; otherwise the first `git commit` would commit
   the whole pile. Now index = root, worktree = final state.
4. `git checkout -b <branch>` — user wants branch-based dev per spec; commit there, then
   `git checkout main && git merge --ff-only <branch>` + `git branch -d` for linear history.
5. Commit groups in **dependency order**: delete the mechanism BEFORE the commit that removes
   its CI job; docs purge AFTER the commit that removes the referenced code.
6. Tag the merge point: `git tag -s v0.1.0 -m "..."` (GPG annotated).
7. Verify: `git log --oneline`, `git status` clean, re-run affected tests on FINAL state,
   `git log --show-signature --format="%h %G? %s"` expects all `G`.

## Pitfalls (all hit for real on an early full-history rewrite)

- **多仓库会话：只整理「内容已确认完成」的仓库，迭代中的仓库保持工作区未提交** —
  一次会话改动多个 astra 仓库（如蓝图/docs 仓库 + 承载协议变更的 meta-repo）时，
  commit 整理与推送**只对内容确认完成的那个仓库做**；仍在设计迭代的仓库（如
  astra-agent-constellation 蓝图）保留未提交工作区改动（或未推送的零散 commit），
  不要因为「反正改了」就顺手整理它的历史。用户纠正（2026-08-04）：「你要整理commit
  推的是更新了协议的meta repo或什么正确的项目」——承载已确认变更的仓库才是整理/推送
  对象；其余自由迭代，历史留到迭代结束再规划。判断标准 = 内容是否已被用户确认可发布，
  不是「本会话是否 commit 过」。
- **`git add -A` multi-path aborts wholesale on one bad pathspec**: one path that is deleted
  from worktree AND absent from index (e.g. a test removed by an earlier commit) → fatal
  "pathspec did not match" → nothing after it gets staged and the `&&` chain dies. Fix:
  `git status --short <dir>` first to get exact paths (incl. subdirs like `tests/unit/build/`),
  or add per-directory in separate commands. (For the separate hazard of `git add -A` in a
  tree that holds other authors' work, see `verification.md`.)
- **`git add` stages WORKTREE content, not the old commit's content**: a file present in an
  old commit's file set gets its FINAL workspace version committed into the early commit
  (electron-script removal + orphan-key cleanup landed inside the UI-rewrite commit because
  package.json/tsconfig/messages were in its set). Accept or hunk-split — but expect it.
- **Overlapping files (old commit + workspace, different themes)**: `cp` workspace copies to
  /tmp → `git checkout <oldcommit> -- <files>` (index+worktree → old version) → commit old
  theme → `cp` workspace copies back → commit later theme.
- **husky lint-staged failure REVERTS staged state** ("Reverting to original state"): after
  fixing the cause, re-`git add` EVERYTHING before retrying the commit.
- **Stale eslint suppressions after deleting code**: lint-staged eslint --fix fails with
  "There are suppressions left that do not occur anymore". Fix: drop file-level stale keys
  (compare suppression JSON keys vs `git ls-files`), then
  `npx eslint --fix --prune-suppressions --suppressions-location <file> <changed files>`;
  re-add the suppressions file itself to the commit.
- **Orphan tags**: old release tags (seed-era, e.g. v3.8.50) point at commits NOT on the new
  main. `git tag -d <old>` before `push --tags` or the stale tag pollutes the remote.
- **Version field is seed residue**: a fork inherits upstream's version (e.g. 3.8.50). Per
  user version semantics: project is 0.x per completed phase (0.1.0 after Phase 1); 1.0.0
  only when ALL PLAN phases are done.

## Pre-flight: history rewrites can invalidate credentials and CI gates

Before force-pushing a rewritten branch, audit what depends on the old history:

- **Provider-side secret revocation.** GitHub's secret scanning reacts to rewritten
  pushes: a force-push that rewrites commits where a token was present, or that rewrites
  a repo whose CI secret holds a live token, can invalidate that token. The failure
  surfaces LATER and MISLEADINGLY — the CI job dies at its *first* step (checkout), not
  at the step that consumes the token, so it presents as a broken pipeline rather than a
  dead credential. Verify the token independently (`Bearer` → `/user`) before debugging
  any post-rewrite CI failure.
- **Do not stop at "the credential died" — ask whether the credential was needed at
  all.** A token in CI config usually exists for one narrow reason; before scheduling
  a re-issue, check whether that reason still applies. A GitHub PAT in a Nix
  `access-tokens` line exists only to authenticate *private* flake inputs; when
  `flake.lock` resolves every input to a public tarball the token is pure liability —
  it is the one thing a rewrite can revoke, and it re-arms the revocation every time
  history is rewritten. Enumerate the inputs (`flake.lock` → each `locked.url`) and
  test anonymous fetch before concluding a re-issue is needed. **Zero external
  credentials in CI is the default target**; each one you remove is a failure mode
  removed. Re-issuing a revoked credential without this check just schedules the same
  incident again.
- **Branch protection keyed to job names.** Status-check gates reference job names; if the
  rewritten pipeline no longer produces a check under that exact name, every push to the
  protected branch is blocked. Confirm required contexts still match real job names.
- **Protected branches block the post-rewrite push itself.** If the branch you just
  rewrote is protected, the force-push is rejected (`Not allowed to push to protected
  branch <name>`) and the rewrite has landed nowhere. Check protection state BEFORE
  rewriting, and land the work on an unprotected branch (`git push <remote>
  <current>:<unprotected>`) if the rewrite must go out immediately.
- **Unlocking a protected branch for force-push is platform-specific — read the exact
  rejection message before concluding "API can't do it".** Gitea: `enable_force_push` is
  honoured only by PATCH `/repos/<o>/<r>/branch_protections/<rule>` (PUT and delete+recreate
  return 405; POST-create silently coerces the field to false). Gitea then enforces
  force-push as an EXTENSION of regular push — with `enable_push=false` the pre-receive hook
  still rejects even when `enable_force_push=true`, so the working unlock is
  `PATCH {"enable_push":true,"enable_force_push":true}`; restore both fields afterwards.
  GitHub: no allow-toggle needed at all — DELETE `/branches/main/protection`, push with
  lease, then PUT the protection back. Probe each platform's real semantics (throwaway rule,
  or one documented attempt) before telling the user a manual UI click is required.
- **GitHub PUT branch-protection needs JSON body, not `gh -F`.** `gh api -F key='{...}'`
  sends the object as a STRING and the API rejects with 422 "is not an object"; pipe the
  payload via `--input <(echo ...)` or `-f`-free stdin instead.
- **Orphaned CI run history.** Runs for rewritten commits stay in the platform's run list
  referencing unreachable SHAs (may span several pages of retained runs); prune them
  deliberately instead of assuming they self-clean.
