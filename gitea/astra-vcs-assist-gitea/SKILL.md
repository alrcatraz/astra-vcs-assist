---
name: astra-vcs-assist-gitea
description: "Gitea platform operations — authentication, repositories, issues, pull requests, CI/CD, and webhooks via the Gitea API."
version: 1.0.0+alrcatraz.0.0.0
author: alrcatraz
platforms: [linux]

metadata:
  hermes:
    tags: [gitea, self-hosted-git, platform, api, repositories, issues, pull-requests, ci-cd, webhooks]
    related_skills:
      - astra-vcs-assist
      - astra-vcs-assist-github
---

# astra-vcs-assist-gitea — Gitea Platform Operations

Consolidated Gitea platform operations covering authentication, repository management, issues, pull requests, CI/CD pipelines, webhooks, and user administration. All operations use the Gitea REST API via `curl`.

## Dual-Copy Architecture

This skill follows a three-layer content hierarchy:

```
  Layer       Content                                 Storage
  ─────────────────────────────────────────────────────────────────
  Public      Generic VCS skills (no private info)     GitHub
     +
  Personal    Workflow preferences, default aliases,   Gitea (git01)
               project references, per-user configs
     +
  Machine-    Local project paths, Hermes profile      Private copy
  specific    configs, environment-specific             (~/.astra/repos/,
               credential store paths,                  one per Agent)
               per-Agent troubleshooting notes
```

Each layer includes everything above it and adds its own:

```
GitHub（公开）
  └── 通用 VCS 技能（平台操作、路由、公开参考）
        ↓ + 个人配置
Gitea（私有，跨机器共享）
  ├── 上述所有内容
  ├── 个人工作流偏好（默认分支策略、commit 模板偏好）
  ├── 个人项目引用（私有仓库路径、别名）
  ├── 自定义 CI/CD 配置（私有 runner 地址、内网镜像）
  └── 作者相关的默认设置
        ↓ + 机器/Agent 信息
私有副本（每台 Agent 各一份，不共享）
  ├── 上述所有内容
  ├── 本地项目路径（`~/Projects/` 下的实际位置）
  ├── 本机 Hermes profile 配置注记
  ├── 本机凭证存储路径（KeePassXC 数据库位置、GPG 密钥引用）
  └── 本机特有的排错历史

开发副本 (Dev) 负责维护和推送：
  ~/Projects/astra/astra-vcs-assist/
  ├── git push gitea main    →  Gitea (含个人配置)
  └── git push origin public  →  GitHub (仅公开部分)

私有副本从 Gitea 拉取后叠加本机信息：
  ~/.astra/repos/astra-vcs-assist/
  ├── git pull gitea main        ← 获取最新技能 + 个人配置
  └── 额外存本地信息（不推任何 remote）
```

**工作流：**

1. **开发副本**做日常开发 → `git push gitea main`（含个人配置）→ Gitea
2. **开发副本**发布公开版 → `git push origin public`（剥离 `gitea/` 和个人配置）→ GitHub
3. **私有副本**同步 → `git pull gitea main` → 从 Gitea 拉取技能 + 个人配置
4. **私有副本**叠加机器特定信息（路径、profile、凭证位置）→ 仅本地保留，不推送
5. 如果在私有副本发现了对所有人都有用的通用改进 → 通过开发副本或直接推回 Gitea

> **Gitea 作为备份：** 共享技能 + 个人配置在 Gitea 上有完整备份。如果某台 Agent 机器需重建，`git clone` 后重建 symlink 即可恢复所有技能和个人配置。机器特定信息不在 Gitea 上——需从本地存档恢复。

### Three-Layer Versioning

See the [root `README.md`](../../README.md#three-layer-versioning) for the general scheme and this instance's naming convention (`alrcatraz` / agent name). The repository [`VERSION`](../../VERSION) file holds the current private-copy version.

## When to Load

- Setting up Gitea authentication (API tokens, SSH keys)
- Creating, mirroring, forking, or managing repositories
- Working with issues and pull requests
- Deploying or debugging Gitea Actions CI/CD pipelines
- Configuring webhooks for external service integration
- Managing users, organisations, and repository permissions

## Prerequisites

### Auth Detection

```bash
# Gitea API token — required for most operations
if [ -z "$GITEA_TOKEN" ]; then
  if _env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_env" ] && grep -q "^GITEA_TOKEN=" "$_env"; then
    GITEA_TOKEN=$(grep "^GITEA_TOKEN=" "$_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
  elif grep -q "git01.wrt.astra-lab.org" ~/.git-credentials 2>/dev/null; then
    GITEA_TOKEN=$(grep "git01.wrt.astra-lab.org" ~/.git-credentials 2>/dev/null | \
      sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  fi
fi

# Gitea instance URL
GITEA_URL="${GITEA_URL:-https://git01.wrt.astra-lab.org}"
API="${GITEA_URL}/api/v1"
```

> **Note:** For Docker-internal access (co-hosted runners), set `GITEA_URL=http://gitea:3000`.

### Extract Owner/Repo

```bash
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*(gitea|git01)\.[^:/]*[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)

# Manual override when not in a git directory
: "${OWNER:=alrcatraz}"
: "${REPO:=astra-vcs-assist}"
```

## Reference Files

Load specific topics via `skill_view`:

| Topic | Load with |
|:------|:----------|
| CI/CD pipelines (Gitea Actions, act_runner, workflow authoring, upstream tag tracking, 30+ pitfalls) | `skill_view(name='astra-vcs-assist-gitea', file_path='references/ci-cd-pipelines.md')` |
| ci-release.py reusable script | `skill_view(name='astra-vcs-assist-gitea', file_path='scripts/ci-release.py')` |

## Quick Reference

| Operation | curl endpoint |
|-----------|---------------|
| **Auth — create token** | `POST /api/v1/users/{username}/tokens` |
| **Auth — list tokens** | `GET /api/v1/users/{username}/tokens` |
| **Auth — delete token** | `DELETE /api/v1/users/{username}/tokens/{id}` |
| **Repos — list user repos** | `GET /api/v1/user/repos` |
| **Repos — create** | `POST /api/v1/user/repos` |
| **Repos — migrate/mirror** | `POST /api/v1/repos/migrate` |
| **Repos — search** | `GET /api/v1/repos/search?q={query}` |
| **Repos — get** | `GET /api/v1/repos/{owner}/{repo}` |
| **Repos — delete** | `DELETE /api/v1/repos/{owner}/{repo}` |
| **Issues — list** | `GET /api/v1/repos/{owner}/{repo}/issues` |
| **Issues — create** | `POST /api/v1/repos/{owner}/{repo}/issues` |
| **Issues — close** | `PATCH /api/v1/repos/{owner}/{repo}/issues/{index}` |
| **Pull Requests — list** | `GET /api/v1/repos/{owner}/{repo}/pulls` |
| **Pull Requests — create** | `POST /api/v1/repos/{owner}/{repo}/pulls` |
| **Pull Requests — merge** | `POST /api/v1/repos/{owner}/{repo}/pulls/{index}/merge` |
| **Releases — create** | `POST /api/v1/repos/{owner}/{repo}/releases` |
| **Releases — upload asset** | `POST /api/v1/repos/{owner}/{repo}/releases/{id}/assets` |
| **CI — list workflows** | `GET /api/v1/repos/{owner}/{repo}/actions/workflows` |
| **CI — dispatch workflow** | `POST /api/v1/repos/{owner}/{repo}/actions/workflows/{id}/dispatches` |
| **CI — list runs** | `GET /api/v1/repos/{owner}/{repo}/actions/runs` |
| **Webhooks — list** | `GET /api/v1/repos/{owner}/{repo}/hooks` |
| **Webhooks — create** | `POST /api/v1/repos/{owner}/{repo}/hooks` |
| **Users — get authenticated** | `GET /api/v1/user` |
| **Users — search** | `GET /api/v1/users/search?q={query}` |
| **Orgs — list user orgs** | `GET /api/v1/user/orgs` |
| **Runners — list** | `GET /api/v1/admin/actions/runners` |

## Common Operations

### Authentication

Gitea uses personal access tokens for API access. Unlike GitHub's `gh` CLI, Gitea has no standalone CLI — all API operations go through `curl` or Docker exec. API tokens are the **only** auth method for automation.

```bash
# Create a token (via Docker exec if Gitea runs in container)
docker exec -u git gitea gitea admin user generate-access-token \
  -u alrcatraz --scopes all

# Or via the API (requires an existing token)
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"hermes-agent","scopes":["write:admin","write:repository","write:user"]}' \
  "$API/users/alrcatraz/tokens"
```

**SSH key management** for git push access:

```bash
# List user's SSH keys
curl -s -H "Authorization: token $GITEA_TOKEN" "$API/user/keys"

# Add an SSH key
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"my-laptop","key":"'"$(cat ~/.ssh/id_ed25519.pub)"'"}' \
  "$API/user/keys"
```

### Repository Management

```bash
# Create a new repository
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-new-repo",
    "description": "A new project",
    "private": true,
    "auto_init": true,
    "license": "MIT",
    "readme": "Default"
  }' "$API/user/repos"

# Mirror an upstream repository
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clone_addr": "https://github.com/upstream/project.git",
    "repo_name": "project",
    "mirror": true,
    "private": true,
    "description": "Mirror of upstream/project"
  }' "$API/repos/migrate"

# Search for repositories
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$API/repos/search?q=astra-vcs&owner=alrcatraz"
```

### Issues and Pull Requests

```bash
# List open issues
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$API/repos/$OWNER/$REPO/issues?state=open&limit=10"

# Create an issue
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bug: login form broken on mobile",
    "body": "## Steps to reproduce\n1. Open on iPhone\n2. Try to log in\n3. Form elements overlap",
    "assignees": ["alrcatraz"],
    "labels": ["bug"]
  }' "$API/repos/$OWNER/$REPO/issues"

# Create a pull request
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Fix mobile login layout",
    "body": "Uses CSS flexbox instead of float-based layout.",
    "head": "fix/mobile-login",
    "base": "main"
  }' "$API/repos/$OWNER/$REPO/pulls"

# Merge a pull request
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"Do":"merge"}' \
  "$API/repos/$OWNER/$REPO/pulls/42/merge"
```

### Webhooks

```bash
# List webhooks for a repo
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$API/repos/$OWNER/$REPO/hooks"

# Create a webhook (Slack/Discord/Generic)
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "gitea",
    "config": {
      "url": "https://hooks.example.com/webhook",
      "content_type": "json",
      "secret": "your-webhook-secret"
    },
    "events": ["push", "issues", "pull_request"],
    "active": true
  }' "$API/repos/$OWNER/$REPO/hooks"
```

### CI/CD: Quick Dispatch

For full CI/CD pipeline setup, workflow authoring, upstream tag tracking, act_runner deployment, and 30+ pitfalls, load the dedicated reference:

```bash
skill_view(name='astra-vcs-assist-gitea', file_path='references/ci-cd-pipelines.md')
```

Quick-start — dispatch a workflow run:

```bash
WORKFLOW_ID=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$API/repos/$OWNER/$REPO/actions/workflows" | \
  python3 -c "import sys,json; ws=json.load(sys.stdin)['workflows']; print([w['id'] for w in ws if 'build' in w['name'].lower()][0])")

curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","inputs":{"version":"v1.0.0"}}' \
  "$API/repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/dispatches"
```

### User and Organisation Management

```bash
# Get authenticated user info
curl -s -H "Authorization: token $GITEA_TOKEN" "$API/user"

# List organisations the user belongs to
curl -s -H "Authorization: token $GITEA_TOKEN" "$API/user/orgs"

# List members of an organisation
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$API/orgs/$ORG_NAME/members"

# Search users
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$API/users/search?q=alrcatraz"
```

## Pitfalls

1. **`${{ github.token }}` lacks release creation scope in Gitea Actions.** The auto-injected token in Gitea Actions v1.26.x has read/write scope for checkout but NOT for creating releases. Always use a Personal Access Token with `write:repository` scope for release operations. See `references/ci-cd-pipelines.md` for the full fix.

2. **Gitea API artifact upload silently fails in v1.26.x.** `POST /actions/artifacts` returns HTTP 200 but files are never stored. Always use Gitea Releases API instead (`POST /releases` → `POST /releases/{id}/assets`).

3. **Container checkouts need internal vs external URL routing.** On Docker co-hosted runners, CI containers can reach Gitea via Docker DNS (`http://gitea:3000`). On separate-host runners, use the external URL (`https://git01.wrt.astra-lab.org`). See `references/ci-cd-pipelines.md` §Container Networking.

4. **Gitea's `actions/checkout@v4` requires Node.js in the build container.** Standard Linux images (`rust:latest`, `ubuntu:24.04`) lack Node.js. Install `nodejs` via apt or replace with `git clone` + curl API upload.

5. **Gitea Cron tasks for repository maintenance must be enabled.** `git_gc_repos` and other cron tasks are configurable via the admin panel or API. Disabled cron can lead to repository corruption over time.
