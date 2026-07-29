# Gitea Actions CI/CD (Reference)

> Reference file for `astra-vcs-assist-gitea`. Contains full Gitea Actions CI/CD setup — act_runner deployment, workflow authoring, upstream tag tracking, GFW workarounds, and 30+ pitfalls. Load via:
> `skill_view(name='astra-vcs-assist-gitea', file_path='references/ci-cd-pipelines.md')`

Set up a self-hosted CI/CD pipeline using Gitea Actions (v1.20+) with act_runner on a local Linux machine, integrated with Podman for container execution and GFW-friendly registry mirrors.

## 1. When to Use

When set up a self-hosted CI/CD pipeline using Gitea Actions (v1.20+) with act_runner on a local Linux machine, integrated with Podman for container execution and GFW-friendly registry mirrors.

## 2. Architecture

```
┌─────────────────┐    poll for jobs     ┌──────────────────────────┐
│  Gitea Server   │◄────────────────────►│  act_runner (HomeCentre) │
│  (NAS Docker)   │   HTTPS / API v1     │  systemd service         │
│  v1.26.x        │                      │  DOCKER_HOST→Podman sock │
└────────┬────────┘                      └───────────┬──────────────┘
         │                                            │
         │  Webhook / Git push                        │ Podman containers
         ▼                                            ▼
   Repo: .gitea/workflows/*.yml           rust:latest, ubuntu:24.04
```

## 3. Prerequisites

- Gitea instance v1.20+ (Actions built-in)
  - Verify: Settings → "Enable Actions" (default on since v1.21)
- A Linux machine to host the runner (24/7, Docker or Podman)
- Gitea API token with scopes: `write:admin`, `write:repository`, `write:user`

## 4. Quick Start

### 1. Get a Runner Registration Token

```bash
GITEA_TOKEN="your-api-token"
GITEA_URL="https://git01.example.org"

# Generate registration token
curl -s -X POST -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/admin/actions/runners/registration-token"
# Returns: {"token":"eqtA8ZH..."}
```

### 2. Install act_runner

```bash
# Download (check latest version at https://gitea.com/gitea/act_runner/releases)
curl -L -o /tmp/act_runner \
  "https://gitea.com/gitea/act_runner/releases/download/v0.2.12/act_runner-0.2.12-linux-amd64"
chmod +x /tmp/act_runner
sudo cp /tmp/act_runner /usr/local/bin/act_runner

# Register
sudo act_runner register \
  --instance "$GITEA_URL" \
  --token "eqtA8ZH..." \
  --name "my-runner" \
  --labels "ubuntu-latest:docker://node:20-bullseye,ubuntu-24.04:docker://ubuntu:24.04" \
  --no-interactive
```

The `.runner` config file is created in the current directory. Move it to a system location:

```bash
sudo mkdir -p /etc/act_runner
sudo mv .runner /etc/act_runner/
```

### 3. Set Up Systemd Service

```ini
[Unit]
Description=Gitea Actions Runner (act_runner)
After=podman.socket network.target
Wants=podman.socket

[Service]
Type=simple
Environment=DOCKER_HOST=unix:///run/podman/podman.sock
ExecStart=/usr/local/bin/act_runner daemon --config /etc/act_runner/.runner
WorkingDirectory=/etc/act_runner
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now act_runner
```

### 4. Verify Runner is Online

```bash
# Check systemd
sudo systemctl status act_runner

# Check in Gitea Admin UI
# Settings → Actions → Runners → should show "my-runner" as idle

# Check API
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/admin/actions/runners"
```

## 5. Workflow Authoring

Workflows go in `.gitea/workflows/*.yml` (NOT `.github/workflows/`).

### Multi-Binary Release (Template — Core+CLI + Web + Web-Embed)

For Rust workspaces with multiple packages, build each in dependency order so cargo's incremental cache speeds up subsequent invocations.

**Build order matters:**
1. `easytier` package → core + cli (2 binaries, 1 invocation, most deps cached here)
2. `easytier-web` standalone (reuses cached deps)
3. `easytier-web --features embed` (re-caches with embed feature)

```yaml
name: Build Release from Upstream Tag
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Upstream tag to build (e.g. v2.6.4)"
        required: true
        type: string

jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - name: Install build deps & Rust
        run: |
          apt-get update -qq
          apt-get install -y -qq git curl gcc protobuf-compiler libprotobuf-dev \
            pkg-config libssl-dev musl-tools libclang-dev clang make nodejs
          which node || ln -sf /usr/bin/nodejs /usr/bin/node || true
          curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
          . "$HOME/.cargo/env"
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Checkout + Switch to upstream tag
        env:
          GIT_TOKEN: ${{ github.token }}
        run: |
          git clone --depth 1 "https://git:${GIT_TOKEN}@gitea:3000/owner/repo.git" .
          git remote add upstream https://github.com/Upstream/Project.git 2>/dev/null || true
          git fetch upstream --tags 2>&1
          git checkout refs/tags/${{ inputs.version }} 2>/dev/null || \
            git checkout upstream/${{ inputs.version }} 2>/dev/null || {
            echo "ERROR: Tag ${{ inputs.version }} not found"
            exit 1
          }

      - name: Add musl target
        run: |
          . "$HOME/.cargo/env"
          for i in 1 2 3 4 5; do
            rustup target add x86_64-unknown-linux-musl && break
            sleep 10
          done

      - name: 🏗️ Build core + cli (MagicDNS)
        run: |
          . "$HOME/.cargo/env"
          cargo build --release --package=easytier \
            --features "magic-dns,jemalloc" --target x86_64-unknown-linux-musl

      - name: 🏗️ Build web (standalone)
        run: |
          . "$HOME/.cargo/env"
          cargo build --release --package=easytier-web --target x86_64-unknown-linux-musl

      - name: 🏗️ Build web-embed (embedded frontend)
        run: |
          . "$HOME/.cargo/env"
          cargo build --release --package=easytier-web \
            --features embed --target x86_64-unknown-linux-musl
          cp target/x86_64-unknown-linux-musl/release/easytier-web \
            target/x86_64-unknown-linux-musl/release/easytier-web-embed

      - name: UPX compress
        run: upx --lzma --best target/x86_64-unknown-linux-musl/release/easytier-* || true

      - name: Package
        run: |
          VERSION="${{ inputs.version }}"
          mkdir -p dist
          cp target/x86_64-unknown-linux-musl/release/easytier-core      dist/easytier-core-x86_64-${VERSION}
          cp target/x86_64-unknown-linux-musl/release/easytier-cli       dist/easytier-cli-x86_64-${VERSION}
          cp target/x86_64-unknown-linux-musl/release/easytier-web       dist/easytier-web-x86_64-${VERSION}
          cp target/x86_64-unknown-linux-musl/release/easytier-web-embed dist/easytier-web-embed-x86_64-${VERSION}
          cd dist && sha256sum * > CHECKSUMS-${VERSION}.txt

      - name: Create Gitea Release
        id: create_release
        env:
          GITEA_TOKEN: ${{ github.token }}
        run: |
          VERSION="${{ inputs.version }}"
          RELEASE_JSON=$(curl -s -X POST \
            -H "Authorization: token ${GITEA_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{
              "tag_name": "'"${VERSION}"'-magicdns",
              "name": "EasyTier '"${VERSION}"' (MagicDNS enabled)",
              "body": "Build of upstream '"${VERSION}"' with MagicDNS",
              "draft": false,
              "prerelease": false
            }' "http://gitea:3000/api/v1/repos/owner/repo/releases")
          RELEASE_ID=$(echo "$RELEASE_JSON" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
          echo "release_id=$RELEASE_ID" >> $GITHUB_OUTPUT

      - name: Upload Release Assets
        env:
          GITEA_TOKEN: ${{ github.token }}
        run: |
          RELEASE_ID=${{ steps.create_release.outputs.release_id }}
          for f in dist/*; do
            [ -f "$f" ] || continue
            curl -s -X POST \
              -H "Authorization: token ${GITEA_TOKEN}" \
              -F "attachment=@$f" \
              "http://gitea:3000/api/v1/repos/owner/repo/releases/${RELEASE_ID}/assets?name=$(basename "$f")"
          done
```

### Workflow Triggers

| Event | Syntax | When to Use |
|:------|:-------|:------------|
| Branch push | `push: { branches: [main] }` | Build on every commit |
| Tag push | `push: { tags: ['v*'] }` | Build on version tags |
| Manual | `workflow_dispatch:` | Trigger from UI or API |
| Release | `release: { types: [published] }` | Build on Gitea release |

**Note on tag pushes:** When pushing upstream tags (from a mirror), the tag commit contains the upstream's workflow files, not yours. Your `.gitea/workflows/build.yml` only exists on your default branch. **Do NOT use tag push triggers for mirrored repos** — use `workflow_dispatch` + a cron job instead.

### Tag-Triggered Custom Branch Release

When your custom branch (e.g. `astra`) has patches on top of an upstream release, use a **semver pre-release tag** pattern to trigger CI builds and create Gitea Releases automatically. This is distinct from the upstream mirror workflow — here, the tag points to your branch, not to an upstream tag.

**Version convention:** `v<upstream-version>-astra.<N>` (e.g. `v2.6.4-astra.1`). The `-astra.` suffix is both human-readable and machine-matchable by the CI trigger pattern.

**Workflow pattern:**

```yaml
name: Build Custom Branch Release
on:
  push:
    tags:
      - 'v*-astra*'           # ← matches v2.6.4-astra.1, v2.6.4-astra.2, etc.

jobs:
  build:
    runs-on: rust
    steps:
      - name: Install deps
        run: |
          apt-get update -qq
          apt-get install -y -qq protobuf-compiler pkg-config libssl-dev musl-tools \
            nodejs libclang-dev clang make curl
          which node || ln -sf /usr/bin/nodejs /usr/bin/node || true

      - name: Checkout
        uses: actions/checkout@v4

      - name: Parse tag
        run: echo "TAG=${GITHUB_REF_NAME}" >> $GITHUB_ENV

      - name: Build
        run: |
          # Custom build steps with patches enabled...
          cargo build --release --features "magic-dns,jemalloc" \
            --target x86_64-unknown-linux-musl

      - name: Package
        run: |
          mkdir -p dist
          cp target/x86_64-unknown-linux-musl/release/easytier-core \
            dist/easytier-core-x86_64-${TAG}
          cd dist && sha256sum * > CHECKSUMS-${TAG}.txt

      - name: Create Gitea Release
        env:
          GITEA_TOKEN: ${{ github.token }}
        run: |
          TAG="${GITHUB_REF_NAME}"
          RELEASE_JSON=$(curl -s -X POST \
            -H "Authorization: token ${GITEA_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{
              \"tag_name\": \"${TAG}\",
              \"name\": \"Project ${TAG}\",
              \"body\": \"Custom branch build with patches.\",
              \"draft\": false,
              \"prerelease\": false
            }" "http://gitea:3000/api/v1/repos/owner/repo/releases")
          # ...upload assets...
```

**Key differences from the upstream-tag workflow:**
- **Trigger:** `push: { tags: ['v*-astra*'] }` — fires when you push a matching tag
- **Checkout:** `actions/checkout@v4` directly checks out the tag (no upstream fetch needed)
- **Tag already exists:** The tag is created locally first (`git tag -a v2.6.4-astra.1 -m "..."`) then pushed
- **Release tag name:** Same as the git tag (no `-suffix` appended — the tag name IS the suffix)
- **Idempotency:** The API first tries POST, then falls back to GET `/releases/tag/{tag}` if the release already exists

**Version bump discipline:** Always increment the build number (`.N` suffix) for each new tag. Never reuse a tag — if a build fails, fix the issue, create a new tag with the next number. Gitea auto-creates the release tag from the API call, so the git tag and release are always in sync.

### ⚠️ `actions/checkout@v4 ref:` — use this, not `git fetch + git checkout`

The `actions/checkout@v4` action supports a `ref:` parameter that directly specifies the branch, tag, or SHA to check out. This replaces the error-prone `git fetch origin --tags && git checkout refs/tags/...` pattern which fails in Gitea Actions' shallow clone environment.

**❌ Broken pattern** (Gitea's shallow clone may not resolve `fetch --tags`):
```yaml
- name: Checkout
  uses: actions/checkout@v4

- name: Checkout tag
  run: |
    git fetch origin --tags 2>&1
    git checkout refs/tags/$VERSION || { echo "ERROR"; exit 1; }
```

**✅ Correct pattern** — single step, works with Gitea's shallow clone:
```yaml
- name: Checkout tag
  uses: actions/checkout@v4
  with:
    ref: ${{ inputs.version }}
```

The `ref:` parameter resolves via the runner's Gitea API token, not `git fetch`.

### ⚠️ Python inline scripts: `-c` breaks YAML — use heredoc

`python3 -c "..."` inside YAML `run: |` blocks causes parsing errors because `{`, `}`, `:`, and `'` are interpreted by the YAML parser as structure tokens.

**❌ Broken** — YAML sees `:` in `{'Authorization': ...}` as a key-value separator:
```yaml
run: |
  python3 -c "
headers = {'Authorization': f'token {token}'}
"
```

**✅ Correct** — heredoc passes Python via stdin, safe from YAML:
```yaml
run: |
  python3 -u /dev/stdin << 'SCR_END'
import os, requests
token = os.environ.get('GITEA_TOKEN', '')
headers = {'Authorization': f'token {token}'}
SCR_END
```

All Python lines must be indented at the same level as `python3 -u /dev/stdin`. Single-quote the delimiter (`'SCR_END'`) to prevent shell expansion of `${{ }}` inside the heredoc.

Verify YAML locally before pushing:
```bash
python3 -c "import yaml; yaml.safe_load(open('.gitea/workflows/build.yml')); print('valid')"
```

### ⚠️ CI fix discipline: diagnose all → one commit → force push → retag

**Do NOT fix CI failures trial-and-error** (push → fail → tweak → push → fail). Each iteration wastes 5+ min build time.

**Correct workflow:**

1. **Diagnose fully**: GET run overview → GET jobs → find failing step → read act_runner logs
2. **Identify ALL root causes** in one pass
3. **Apply all fixes in one commit**
4. **Clean up stale tags**: `git push origin --delete refs/tags/astra.1`
5. **Force push the branch**: `git push --force origin astra`
6. **Re-tag the new commit**: `git tag -f astra.1 <sha> && git push origin refs/tags/astra.1`
7. **Trigger CI**: POST to `.../actions/workflows/build.yml/dispatches` with `{"ref":"astra","inputs":{"version":"astra.1"}}`

This ensures every tag points to a known commit with no orphaned tags from debugging.

### ⚠️ Critical: `${{ github.token }}` lacks release creation scope

The auto-injected `${{ github.token }}` in Gitea Actions v1.26.x has read/write scope
for checkout, but NOT for creating releases. The Release Create API call fails
silently (the step logs show no helpful error). **Fix:** Use a Personal Access Token (PAT) with
`write:repository` scope instead of `${{ github.token }}`, and combine create+upload into a
single step to avoid cross-step variable passing issues:

```yaml
- name: Create Gitea Release & Upload Assets
  env:
    GITEA_PAT: <token>   # 从 GPG 提取: credential-store-management → gitea.api_token
  run: |
    TAG="${GITHUB_REF_NAME}"
    API="http://gitea:3000/api/v1/repos/owner/repo"

    # Delete existing release for this tag
    EXISTING_ID=$(curl -s -H "Authorization: token ${GITEA_PAT}" \
      "${API}/releases/tag/${TAG}" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    if [ -n "$EXISTING_ID" ]; then
      curl -s -X DELETE -H "Authorization: token ${GITEA_PAT}" \
        "${API}/releases/${EXISTING_ID}"
    fi

    # Create release
    RELEASE_JSON=$(curl -s -X POST -H "Authorization: token ${GITEA_PAT}" \
      -H "Content-Type: application/json" \
      -d "$(printf '{"tag_name":"%s","name":"Release %s","body":"Custom build","draft":false,"prerelease":false}' "${TAG}" "${TAG}")" \
      "${API}/releases")
    RELEASE_ID=$(echo "$RELEASE_JSON" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    if [ -z "$RELEASE_ID" ]; then
      echo "ERROR: Failed to create release. Response: $RELEASE_JSON"
      exit 1
    fi
    echo "release_id=${RELEASE_ID}" >> $GITHUB_OUTPUT

    # Upload assets
    for f in dist/*; do
      [ -f "$f" ] || continue
      curl -s -X POST -H "Authorization: token ${GITEA_PAT}" \
        -F "attachment=@$f" "${API}/releases/${RELEASE_ID}/assets?name=$(basename "$f")" > /dev/null
      echo "  -> uploaded $(basename "$f")"
    done
```

**Why combine steps:** The `steps.create_release.outputs.release_id` cross-step variable
can be empty in upload step due to Gitea Actions env parsing quirks. A single step avoids
this entirely.

### Release JSON construction: three approaches in order of reliability

When building JSON for the Gitea Release API inside a YAML `run: |` block,
three approaches exist — only the third is robust against all shell escaping
issues:

**❌ Approach 1: Multi-line JSON in `-d '...'`** — shell escaping breaks on
multiline bodies, quotes inside strings, and backslashes. The error message is
usually silent.

**❌ Approach 2: `printf` + file redirect + `-d @file`** — works for simple
cases but `printf` in YAML block scalars (`run: |`) can introduce literal
newlines inside JSON strings (e.g. `\"body\"` with multi-line text), producing
invalid JSON that the API rejects silently. **Observed failure mode:** the JSON
looks correct in human inspection but contains an embedded `\n` that curl sends
as a real newline, breaking the JSON parser on the server side. The API returns
HTTP 200 (not an error!) but no release is created.

```yaml
# ❌ printf can introduce literal \n → broken JSON that returns HTTP 200
printf '{"tag_name":"%s","name":"Release %s","body":"Auto build.","draft":false,"prerelease":false}' \
  "${TAG}" "${TAG}" > /tmp/release.json
```

**✅ Approach 3 (RECOMMENDED): Dedicated python3 script (`ci-release.py`)** —
Python's `json.dumps()` generates perfectly valid JSON regardless of content.
Zero shell escaping concerns. This is the only approach that survived all 4
attempts (Runs #104-#107) against Gitea's release API without a single
format-related failure.

Create `ci-release.py` in the repo's `.gitea/` or project root:

```python
#!/usr/bin/env python3
"""Create a Gitea release and upload assets."""
import json, os, subprocess, sys, time

def api(path, data=None, method="GET"):
    token = os.environ.get("GITEA_PAT", os.environ.get("GITEA_TOKEN", ""))
    base = os.environ.get("GITEA_API", "http://gitea:3000/api/v1")
    headers = ["-s", "-X", method,
               "-H", f"Authorization: token {token}",
               "-H", "Content-Type: application/json"]
    if data is not None:
        cmd = ["curl"] + headers + ["-d", json.dumps(data), f"{base}{path}"]
    else:
        cmd = ["curl"] + headers + [f"{base}{path}"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout

tag = os.environ.get("GITHUB_REF_NAME", "")
repo = "owner/repo"  # ← adjust to your repo

release_data = {
    "tag_name": tag,
    "name": f"Release {tag}",
    "body": f"Build of {tag}",
    "draft": False,
    "prerelease": False,
}

# Delete existing release for this tag (idempotent)
existing = api(f"/repos/{repo}/releases/tag/{tag}")
if '"id"' in existing and json.loads(existing).get("id"):
    api(f"/repos/{repo}/releases/{json.loads(existing)['id']}", method="DELETE")
    time.sleep(1)

# Create release
resp = api(f"/repos/{repo}/releases", data=release_data, method="POST")
release = json.loads(resp)
release_id = release.get("id")
if not release_id:
    print(f"ERROR: Failed to create release. Response: {resp}", file=sys.stderr)
    sys.exit(1)
print(f"release_id={release_id}")

# Upload assets
token = os.environ.get("GITEA_PAT", os.environ.get("GITEA_TOKEN", ""))
api_base = os.environ.get("GITEA_API", "http://gitea:3000/api/v1")
for f in sorted(os.listdir("dist")):
    fpath = os.path.join("dist", f)
    if not os.path.isfile(fpath):
        continue
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        "-H", f"Authorization: token {token}",
        "-F", f"attachment=@{fpath}",
        f"{api_base}/repos/{repo}/releases/{release_id}/assets?name={f}"
    ], capture_output=True, text=True)
    print(f"  -> uploaded {f}" if result.returncode == 0 else f"  -> FAILED {f}")
```

Then in the workflow:

```yaml
- name: Create Gitea Release & Upload
  env:
    GITEA_PAT: <token>   # 从 GPG 提取: credential-store-management → gitea.api_token
  run: |
    python3 .gitea/ci-release.py
```

**Why Approach 3 wins:**
- `json.dumps()` handles escaping, newlines, special chars — no shell can corrupt it
- Error handling is explicit (not silent like `printf` failures where API returns HTTP 200 with no release)
- Upload loop is simpler (no bash `for f in dist/*` with path quoting issues)
- The same script works across workflow runs, tag builds, and manual dispatches
- Can be extended with retry logic, asset verification, or multi-repo support
- **A reusable script is packaged with this skill** — see `scripts/ci-release.py`. Copy it into your repo's `.gitea/` or project root via `skill_view(name='astra-vcs-assist-gitea', file_path='scripts/ci-release.py')`.

### Adding triggers for custom-branch tag patterns

When adding a tag-driven trigger to a workflow, ensure the tag pattern is sufficiently specific. `'v*'` is too broad — it catches upstream tags pushed to the mirror as well. Use `'v*-custom*'` or `'v*-astra*'` to target only your custom branch releases. This prevents double-triggering when the upstream tag sync cron runs.

## 6. Container Runtime Integration

### Podman (recommended for separate-host runners)

Replace Docker with Podman for daemonless, rootless-friendly container execution:

```bash
# 1. Install podman-docker (makes `docker` command = podman)
sudo zypper install podman-docker   # openSUSE
sudo apt install podman-docker      # Debian/Ubuntu

# 2. Enable rootful Podman socket
sudo systemctl enable --now podman.socket

# 3. Verify socket
ls -la /run/podman/podman.sock
sudo curl -s --unix-socket /run/podman/podman.sock http://localhost/_ping
# Returns: OK

# 4. Set DOCKER_HOST in act_runner systemd service
# Environment=DOCKER_HOST=unix:///run/podman/podman.sock
```

**Note:** Rootful Podman socket (`/run/podman/podman.sock`) is needed so the runner (running as root) can communicate with Podman's Docker-compatible API.

### Docker (alternative)

```bash
sudo systemctl enable --now docker
# Docker socket: /var/run/docker.sock (default, no DOCKER_HOST needed)
```

### Co-hosted Runner as Docker Container (RECOMMENDED for NAS/Server)

When the runner and Gitea share the same Docker daemon, run act_runner as a Docker container. This eliminates all container networking issues — CI job containers are spawned on the same Docker network as Gitea.

```bash
# 1. Create persistent data directory
mkdir -p /path/to/act_runner_data

# 2. Generate a registration token from Gitea
docker exec -u git gitea gitea actions generate-runner-token
# Returns: eqtA8ZH...

# 3. Create config.yaml (see "Runner Configuration" section below)

# 4. Deploy the runner container
docker run -d \\
  --name act_runner \\
  --restart always \\
  --network gitea_default \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -v /path/to/act_runner_data:/data \\
  -e GITEA_INSTANCE_URL=http://gitea:3000 \\
  -e GITEA_RUNNER_REGISTRATION_TOKEN="eqtA8ZHMp4..." \\
  -e GITEA_RUNNER_NAME="ds425plus" \\
  -e CONFIG_FILE=/data/config.yaml \\
  gitea/act_runner:latest
```

#### IMPORTANT: CONFIG_FILE env var

Mounting config.yaml at `/data/config.yaml` is NOT enough. The `run.sh` entrypoint only passes `--config` to the runner when `CONFIG_FILE` env var is set. Without it, `--config` is never passed -> config.yaml is ignored -> labels default to `:host` mode.

#### IMPORTANT: Network for co-hosted runners

Join the **same Docker network as Gitea** (`--network gitea_default`). This allows CI job containers to resolve `gitea` via Docker DNS and use internal URLs for checkout/upload.

When CI containers need internet access: The Docker bridge network may not have full internet egress, especially behind a transparent proxy (mihomo TPROXY) on the router. CI containers may fail to reach `sh.rustup.rs:443` with `SSL_ERROR_SYSCALL`. See "GFW / CI Container Egress" section below and `references/container-network-diagnostics.md` for a systematic diagnosis approach.

**CONFIG_FILE env var (CRITICAL):** Mounting config.yaml at `/data/config.yaml` is NOT enough. The `run.sh` entrypoint only passes `--config` to the runner when `CONFIG_FILE` env var is set. Without it, `--config` is never passed → config.yaml is ignored → labels default to `:host` mode.

**Network:** Join the same Docker network as Gitea

**Socket:** Mount the host's Docker socket so the runner can spawn sibling containers for CI jobs.

**Labels:** Define labels in the config.yaml file (see below) — do NOT rely on GITEA_RUNNER_LABELS env var alone, as v0.6.1 appends `:host` to env-specified labels.

## 7. Upstream Tag Tracking

When mirroring an upstream project that releases new versions, set up a cron job to auto-detect and push new tags.

Choose the approach that matches your workflow:

### MUSL Build Images: BlackDex/rust-musl as Alternative to rust:latest

When `rust:latest` + `--target musl` fails (rustup target add issues, linker errors, OOM compiling OpenSSL), use a dedicated MUSL build image:

| Image | OpenSSL | Best for |
|:------|:--------|:---------|
| `ghcr.io/blackdex/rust-musl:x86_64-musl-stable` | ✅ Pre-compiled v3.5.7 | Projects needing OpenSSL FFI |
| `clux/muslrust:stable` | ❌ Removed 2025 | Projects using rustls |

`blackdex/rust-musl` is preferred for easytier-web (needs OpenSSL). Usage:

```bash
docker run --rm \
  -v "$(pwd)":/home/rust/src \
  -e RUSTUP_TOOLCHAIN=stable \
  ghcr.io/blackdex/rust-musl:x86_64-musl-stable \
  bash -c "apt-get update -qq && apt-get install -y -qq protobuf-compiler libprotobuf-dev && cargo build --release --features=embed"
```

**Protobuf requirement:** Projects using `prost` / `prost-wkt-types` need BOTH `protobuf-compiler` (the `protoc` binary) AND `libprotobuf-dev` (Google's standard `.proto` includes like `google/protobuf/duration.proto`). The latter is easy to miss — without it, protoc fails with `google/protobuf/duration.proto: File not found`.

Install command (Debian/Ubuntu):
```bash
apt-get update -qq && apt-get install -y -qq protobuf-compiler libprotobuf-dev
```

The `.proto` include files live at `/usr/include/google/protobuf/` after `libprotobuf-dev` is installed. See `astra-vcs-assist-gitea` skill's `references/blackdex-rust-musl-build.md` for the full session trail.

The `RUSTUP_TOOLCHAIN=stable` env var prevents cargo from downloading/switching Rust versions based on `rust-toolchain.toml`. See Pitfall #33.
      cargo build --release --features=embed
```

The `RUSTUP_TOOLCHAIN=stable` env var prevents cargo from downloading/switching Rust versions based on `rust-toolchain.toml`. See Pitfall #33.

### Gitea Artifact Upload Caution (Gitea 1.26.x)

`POST /api/v1/repos/{owner}/{repo}/actions/artifacts?run_id=...` returns HTTP 200 but files are **never stored** on disk. The `actions_artifacts` directory stays empty and the API returns `{\"artifacts\":[]}`. **Always use Gitea Releases instead** for persistent binary distribution:

```yaml
# Create a Gitea Release + upload assets (reliable)
- name: Create Gitea Release
  id: create_release
  env:
    GITEA_TOKEN: ${{ github.token }}
  run: |
    RELEASE_JSON=$(curl -s -X POST \
      -H "Authorization: token ${GITEA_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"tag_name":"v1.0.0-build","name":"Build v1.0.0","body":"...","draft":false,"prerelease":false}' \
      "http://gitea:3000/api/v1/repos/owner/repo/releases")
    RELEASE_ID=$(echo "$RELEASE_JSON" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    echo "release_id=$RELEASE_ID" >> $GITHUB_OUTPUT

- name: Upload Release Assets
  env:
    GITEA_TOKEN: ${{ github.token }}
  run: |
    RELEASE_ID=${{ steps.create_release.outputs.release_id }}
    for f in dist/*; do
      [ -f "$f" ] || continue
      curl -s -X POST -H "Authorization: token ${GITEA_TOKEN}" \
        -F "attachment=@$f" \
        "http://gitea:3000/api/v1/repos/owner/repo/releases/${RELEASE_ID}/assets?name=$(basename "$f")"
    done
```

Gitea auto-creates the tag even if it doesn't exist yet. Releases survive run cleanup. Use `GET /releases/tag/{tag}` to find an existing release instead of creating a duplicate.

### Approach A: Push All Tags (Simple Mirror)

Use when you only need to keep the Gitea mirror up-to-date and don't need per-tag CI builds:

```bash
# Trigger: every 6h
# Prompt template:
Check the upstream repo for new tags:
1. cd ~/Projects/mirror-repo
2. git fetch origin --tags
3. Compare upstream tags with Gitea tags
4. If new tags found: git -c credential.helper= push gitea --tags
5. Report new tags found, or "No new upstream tags found"
```

### Approach B: Push + Build per Tag (CI on Each Release)

Use when each new upstream tag should trigger a Gitea Actions CI build. Instead of pushing all tags at once, iterate over new tags individually: push the tag, then dispatch a workflow build for it.

**Cron Job Pattern:**

```bash
# 1. Fetch upstream tags
cd ~/Projects/mirror-repo
git fetch origin --tags 2>&1

# 2. List upstream tags
upstream_tags=$(git tag --list 'v*' --sort=-version:refname)

# 3. Get tags already on Gitea
gitea_tags=$(git -c credential.helper= ls-remote --tags gitea | grep -o 'refs/tags/[^^]*' | sed 's|refs/tags/||')

# 4. For each new tag, push individually and trigger CI
for tag in $upstream_tags; do
  if echo "$gitea_tags" | grep -q "^$tag$"; then
    echo "Already on Gitea: $tag — skipping"
    continue
  fi
  echo "New tag: $tag"

  # Push to Gitea
  git -c credential.helper= push gitea "refs/tags/$tag" 2>&1

  # Trigger Gitea Actions CI build
  curl -s -X POST \
    "https://git01.wrt.astra-lab.org/api/v1/repos/owner/repo/actions/workflows/build.yml/dispatches" \
    -H "Authorization: token $GITEA_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"ref\":\"main\",\"inputs\":{\"version\":\"$tag\"}}"

  echo "Triggered CI build for $tag"
done
```

**Key difference from Approach A:** Pushing tags individually (not `--tags` bulk) ensures that the `workflow_dispatch` trigger is paired with the correct tag name. If the tag commit also triggers automatic workflows (e.g. tag-push triggers in workflow YAML), those run in parallel.

### Workflow Template: Upstream Tag → Gitea Release (Reliable Artifact Delivery)

**Problem:** Gitea Action artifact upload API (`POST /actions/artifacts`) silently fails on Gitea 1.26.x — files are POSTed with HTTP 200 status but never stored on disk. The `actions_artifacts` directory remains empty.

**Fix:** Use Gitea Releases API instead. Build from an upstream tag, create a Gitea Release, upload binaries as release assets. Pattern verified working across Gitea versions.

```yaml
name: Build Release from Upstream Tag
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Upstream tag to build"
        required: true
        type: string

jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      # ... install deps, checkout, build steps (standard) ...

      - name: Create Gitea Release
        id: create_release
        env:
          GITEA_TOKEN: ${{ github.token }}
        run: |
          VERSION="${{ inputs.version }}"
          RELEASE_JSON=$(curl -s -X POST \
            -H "Authorization: token ${GITEA_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{
              "tag_name": "'"${VERSION}"'-custom",
              "name": "Project '"${VERSION}"' (custom features)",
              "body": "Build of upstream '"${VERSION}"'",
              "draft": false,
              "prerelease": false
            }' \
            "http://gitea:3000/api/v1/repos/owner/repo/releases")
          RELEASE_ID=$(echo "$RELEASE_JSON" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
          echo "release_id=$RELEASE_ID" >> $GITHUB_OUTPUT

      - name: Upload Release Assets
        env:
          GITEA_TOKEN: ${{ github.token }}
        run: |
          RELEASE_ID=${{ steps.create_release.outputs.release_id }}
          for f in dist/*; do
            [ -f "$f" ] || continue
            curl -s -X POST \
              -H "Authorization: token ${GITEA_TOKEN}" \
              -F "attachment=@$f" \
              "http://gitea:3000/api/v1/repos/owner/repo/releases/${RELEASE_ID}/assets?name=$(basename "$f")"
          done
```

**Key difference between Artifact and Release APIs:**
- Artifact upload: `POST /actions/artifacts?run_id=...` — silently fails in 1.26.x
- Release create + asset upload: `POST /releases` → `POST /releases/{id}/assets` — verified working
- Release tag naming convention: use `{VERSION}-{suffix}` (e.g. `v2.6.4-magicdns`) to keep releases distinct from upstream tags

### Manual Dispatch for Tag Builds

For one-off manual builds (e.g. re-running a failed CI build for a tag that already exists on Gitea):

```bash
curl -X POST -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/repos/owner/repo/actions/workflows/build.yml/dispatches" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","inputs":{"version":"v2.6.5"}}'
```

The workflow uses `workflow_dispatch` with an optional `version` input.

## 8. Runner Configuration (config.yaml)

act_runner v0.6.1+ uses a **config.yaml** file (not just CLI flags) for persistent configuration. Without it, the runner defaults to `:host` execution mode — running CI jobs directly on the runner's host OS instead of in Docker containers.

**This is the most common pitfall when deploying act_runner.** The symptom: `apt-get: command not found` on Synology or any non-Debian host.

### Generate a Config Template

```bash
docker exec act_runner act_runner generate-config > config.yaml
```

### Critical Sections

**labels:** This is where you define what Docker image each `runs-on:` label maps to. Use `docker://` format (NOT `:host`):

```yaml
runner:
  labels:
    - "ubuntu-latest:docker://docker.gitea.com/runner-images:ubuntu-latest"
    - "ubuntu-24.04:docker://docker.gitea.com/runner-images:ubuntu-24.04"
    - "ubuntu-22.04:docker://docker.gitea.com/runner-images:ubuntu-22.04"
```

Each label entry has the format: `<label-name>:docker://<image-name>`

Available runner images published by Gitea: https://gitea.com/gitea/runner-images

For custom images (e.g., smaller or pre-cached), use any Docker Hub image:

```yaml
runner:
  labels:
    - "ubuntu-24.04:docker://ubuntu:24.04"   # 77MB minimal — needs apt-get install
    - "rust-builder:docker://rust:latest"     # 1.2GB — has Rust but no node, causes cgroup v2 fork issues
```

**container.network:** Set to Gitea's Docker network for co-hosted runners:

```yaml
container:
  network: gitea_default
```

**Important:** The config.yaml must be mounted at `/data/config.yaml` inside the runner container. Using env vars alone (`GITEA_RUNNER_LABELS`) causes the runner to append `:host` suffix automatically.

Gitea credentials are stored in git remote URLs embedded with password:

```bash
# Typical remote URL with credentials:
# https://username:password@gitea.example.org/owner/repo.git

# Push without triggering pass credential helper:
git -c credential.helper= push gitea main

# API token for automation:
# Scope: write:admin, write:repository, write:user
```

## 9. GFW / CI Container Egress

CI containers on a Docker bridge network may have **limited or no internet access** when the host NAS/server is behind a transparent proxy (mihomo TPROXY) on the router. The symptom:

```text
curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to sh.rustup.rs:443
```

### Why this happens

The Docker bridge network routes container traffic through the host's default gateway (the router). If the router runs mihomo in TPROXY mode:

1. Container outbound HTTPS (port 443) hits the router
2. TPROXY intercepts it, sends through proxy nodes
3. Proxy nodes may be unhealthy or the connection is GFW-interfered
4. TLS handshake fails with SSL_ERROR_SYSCALL in the container

### Fixes

#### Option A: Pre-cache the Rust toolchain (RECOMMENDED)

Build a custom runner image with Rust pre-installed so the container doesn't need internet at build time:

```dockerfile
FROM docker.gitea.com/runner-images:ubuntu-24.04
# Pre-install Rust toolchain (including musl target)
RUN apt-get update && apt-get install -y curl && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . "$HOME/.cargo/env" && \
    rustup target add x86_64-unknown-linux-musl
```

Push to a local registry and reference it in config.yaml labels.

#### Option B: Use `network_mode: host` for CI containers

```yaml
# config.yaml
container:
  network: gitea_default
  network_mode: "host"
```

⚠️ Security: CI containers share the host's full network stack. Only use in trusted environments.

#### Option C: Install rust from Ubuntu packages

```yaml
- name: Install Rust (avoid rustup HTTPS)
  run: |
    apt-get install -y -qq rustc cargo 2>&1 || true
```

⚠️ Ubuntu packages are often outdated (e.g. rustc 1.75 vs latest 1.96).

#### Option E: Retry transient HTTPS corruption in rustup + cargo (quickest fix)

When TPROXY nodes are overloaded, the container may successfully download large toolchain archives (200 MB+) but fail on smaller files with `error decoding response body`. This is not a full block — it's intermittent corruption. Instead of switching images or mirrors, add retry loops around both `rustup target add` and `cargo build`:

**For rustup — loop with sleep:**
```bash
for i in 1 2 3 4 5; do
  rustup target add x86_64-unknown-linux-musl && break
  sleep 10
done
```

**For cargo — use `CARGO_NET_RETRY` env var:**
```bash
CARGO_NET_RETRY=5 cargo build --release --package=easytier --target x86_64-unknown-linux-musl
```

`CARGO_NET_RETRY=5` tells cargo to retry failed downloads up to 5 times with built-in backoff. This covers crate download failures that rustup's retry loop doesn't reach.

```yaml
- name: Build with custom features
  run: |
    # Retry up to 5 times — proxy corruption is transient
    for i in 1 2 3 4 5; do
      rustup target add x86_64-unknown-linux-musl && break
      echo "musl target download failed (attempt $i/5), retrying in 10s..."
      sleep 10
    done
    . "$HOME/.cargo/env"
    cargo build --release --package=easytier --features "magic-dns,jemalloc" \
      --target x86_64-unknown-linux-musl
```

This pattern works because:
- The large toolchain download (cargo + rustc + rust-std) usually succeeds via a stable CDN endpoint
- The smaller component download (rust-std for musl) goes through a different endpoint that may route through an overloaded proxy node
- 10s delay between retries gives time for proxy load balancing to switch nodes

**Important:** `cargo build --release --package=easytier --features ...` is REQUIRED, not optional. Without `--package`, cargo builds ALL workspace members. With `--package`, only the specified package is built — and **all `[[bin]]` targets within that package** (both `easytier-core` and `easytier-cli`) are compiled in a single invocation. See Pitfall 20.

**⚠️ Diagnostic pitfall:** Do NOT conclude "HTTPS is blocked for containers" based on `curl` timeout inside the build image. `rust:*-slim-bookworm` images lack `curl`, `wget`, and `python3`. Use an `alpine:3.20` container to test container networking first — Alpine has `wget` and network tools built-in. If Alpine reaches HTTPS but the slim image doesn't, install `curl` via `apt-get` in the slim image and retest before assuming network issues. See `references/container-network-diagnostics.md` for the full layered diagnosis methodology.

#### Option F: Proxy bypass on the router

Add the NAS IP to mihomo's `bypass` or `direct` list:

```yaml
# mihomo rules.yaml
rules:
  - "SRC-IP-CIDR,192.168.0.30/32,DIRECT"  # NAS LAN IP
```

Then the NAS -> internet traffic bypasses TPROXY entirely.

### Checkout URL: Internal vs External

For co-hosted runners (runner + Gitea on same Docker host), CI containers are on the same Docker network as Gitea. Use the **internal Docker hostname**:

```yaml
# gitea:3000 resolves via Docker DNS (co-hosted runner) - RECOMMENDED
git clone "http://git:${GIT_TOKEN}@gitea:3000/owner/repo.git" .

# Also for artifact upload:
curl -F "attachment=@$f" "http://gitea:3000/api/v1/repos/owner/repo/actions/artifacts?run_id=..."
```

For separate-host runners, use the external URL:

```yaml
git clone "https://git:${GIT_TOKEN}@git01.example.org/owner/repo.git" .
```

**Tip:** The NAS host itself cannot resolve `gitea` (only Docker containers on the `gitea_default` network can). Push operations must use `localhost:3000` instead.

## 10. GFW / China Network Considerations

Docker Hub and crates.io are frequently blocked. Apply these configurations:

### 1. Container Registry Mirrors

Create `/etc/containers/registries.conf.d/99-mirrors.conf`:

```ini
unqualified-search-registries = ["docker.io"]

[[registry]]
prefix = "docker.io"
location = "docker.m.daocloud.io"

[[registry.mirror]]
location = "docker.1ms.run"
```

Verification:
```bash
podman pull hello-world
# Should pull via mirror, not direct to docker.io
```

### 2. Cargo Mirror

For `cargo build` inside CI containers, add a `.cargo/config.toml` to the repo:

```toml
[source.crates-io]
replace-with = "rsproxy"

[source.rsproxy]
registry = "https://rsproxy.cn/crates.io-index"
```

Or configure system-wide on the runner host, which Propagates to containers via volume mounts.

### 3. Rust Musl Cross-Compilation

Building static binaries (musl) inside the `rust:latest` container:

```bash
apt-get install -y musl-tools
rustup target add x86_64-unknown-linux-musl
cargo build --release --target x86_64-unknown-linux-musl
```

## 11. Verification Checklist

After setup, verify the pipeline is healthy:

```bash
# 1. Runner daemon running
sudo systemctl is-active act_runner

# 2. Runner registered in Gitea
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/admin/actions/runners"

# 3. Container runtime accessible
sudo docker ps   # Should work (via Podman compat)

# 4. CI build triggered (push to main branch)
# Check Gitea UI: repo → Actions tab
# or via API:
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/repos/owner/repo/actions/runs?limit=3"

# 5. Container can pull images
sudo podman pull rust:latest   # Pre-cache build image
```

## 12. Troubleshooting CI Failures

### 0. Golden Rule: Diagnose Before Fixing

### 0b. Monitoring In-Progress CI Builds

When a CI run is actively building (especially a long Rust compilation), check real‑time progress instead of waiting for completion:

```bash
# Latest output — what's currently compiling / which step is active
docker logs act_runner 2>&1 | tail -20

# Compilation progress gauge — count compiled crates
docker logs act_runner 2>&1 | grep -c 'Compiling'

# Reach milestones — Finished or compilation errors
docker logs act_runner 2>&1 | grep -E 'Finished|error\[|warning\['

# Step-level progress — which workflow step is currently executing
docker logs act_runner 2>&1 | grep '\[\S.*\S\]' | tail -5
```

**Container lifecycle clues:**

```
Container naming pattern:
  GITEA-ACTIONS-TASK-<N>-WORKFLOW-<name>-JOB-<hash>
  N    = sequential task number assigned by runner
  name = workflow file name (sanitised)
  hash = job instance ID

Entrypoint: /bin/sleep 10800  (= 3‑hour default timeout)

A container that has been running 44+ min on a Rust build is normal.
First musl compile downloads + compiles ~200 crates — expect 30-40 min.
```

**What to look for in live output:**

| What you see | Means | Action |
|:-------------|:------|:-------|
| `Compiling X vY.Z` scrolling steadily | Build is making progress | Wait — no action needed |
| `Compiling` count rising but no new output for >5 min | May be stuck or doing LTO silently | Check container processes via `/proc/*/cmdline` (see below) |
| `Finished release profile` | GNU target compiled ✅ | Musl target begins next (fresh build, may take as long again) |
| `error[E...]` | Build error | Wait for run to finish, then diagnose |
| `SSL_ERROR_SYSCALL` / `error decoding response body` | Transient HTTPS corruption through TPROXY | Retry loop in the workflow handles this automatically |
| `apt-get` commands running | Install‑deps step | Quick — usually done in <30s |

**LTO silence trap:** After the last `Compiling atomic_refcell v0.1.13` (or similar leaf dependency) line, the build may go silent for 20+ minutes while `rustc` does LTO (link-time optimization). The build is NOT stuck — it's doing the heaviest work.
- `-C lto -C codegen-units=1 -C opt-level=3` means rustc optimises the ENTIRE crate as one unit. On NAS-class CPUs (Celeron J3455), this takes 20–40 minutes per target.
- During LTO, the host shows rustc at 100% CPU on one core, 2+ GB RAM.
- To confirm it's LTO not stuck: check inside the container via `/proc/*/cmdline` (see proc-based diagnosis below).

**Caution:** Only **read** the logs of a running CI container — never modify it. act_runner manages the container lifecycle; interfering can corrupt the run state.

### Proc‑based Diagnosis for Minimal Containers

When `rust:*-slim-bookworm` (or any minimal image) has no `ps`, `top`, or `curl`, use `/proc` to see what's actually running:

```bash
# From the Docker host, inside the CI container:
docker exec <container-id> sh -c '
  for p in /proc/*/cmdline; do
    pid=$(echo $p | cut -d/ -f3)
    cmd=$(tr "\0" " " < $p 2>/dev/null)
    echo "$pid: $cmd"
  done
'

# What to expect for a healthy LTO build:
#   1: /bin/sleep 10800          ← container keeper (always present)
#   13624: /usr/local/rustup/.../rustc --crate-name easytier_core ... -C lto ...
#   1651: bash --noprofile --norc -e -o pipefail /var/run/act/workflow/3
#   1680: /usr/local/rustup/.../cargo build --release --package=easytier ...
```

Key indicators:
- **rustc with `--crate-name easytier_core` and `-C lto`** → actively doing LTO, NOT stuck
- **Only `/bin/sleep` and cargo** → cargo is between steps or waiting for rustc output
- **No rustc process at all** → the build command may have exited (check for errors)
- **Multiple rustc processes in parallel** → `codegen-units > 1` or parallel crate compilation

### 1. Golden Rule: Diagnose Before Fixing

**Do NOT fix CI failures trial-and-error style** (push → fail → tweak → push → fail → repeat). Each iteration takes 5+ minutes of build time and wastes the user's patience.

Instead, collect ALL failure data before making any changes:

```
1. GET the run overview (status, conclusion)
   → curl .../actions/runs/<ID>
2. GET the job steps (which step failed?)
   → curl .../actions/runs/<ID>/jobs
3. READ the act_runner logs for the ERROR MESSAGE
   → docker logs act_runner | grep -A10 'Failure'
4. ANALYSE what fixes are needed (may be multiple issues)
5. APPLY ALL FIXES in one commit
6. PUSH once — not once per fix
```

The act_runner container stores full step-level output including the exact command failure. Access it via:

```bash
# On the runner host
docker logs act_runner 2>&1 | grep -A15 'Failure' | grep -v DEBUG

# Filter for specific errors
docker logs act_runner 2>&1 | grep -E 'error|Error|panicked|not found|exitcode.*1[0-9][0-9]'
```

The Gitea API's zstd-compressed log download endpoint (`/actions/runs/<ID>/logs`) may return 404 in some versions — the act_runner container logs are the authoritative source.

### How to Diagnose

When a CI run fails:
1. **Identify the failing step** via the API: `curl .../actions/runs/<ID>/jobs` → look for `"conclusion": "failure"` on any step
2. **Get the error message** from act_runner docker logs: `docker logs act_runner | grep -A10 'Failure'` or search for the step name
3. **Distinguish between three failure types:**
   - **`|| true` masking** — step reports "success" but packages weren't actually installed → subsequent steps fail mysteriously. Fix: remove `|| true` so failures are visible; verify critical binaries with `which`.
   - **Missing package** — e.g. `upx-ucl` not found on Debian bookworm (Ubuntu name), or `make` not pre-installed in slim images. Fix: install the right package or adapt to the distro's naming.
   - **Network/proxy corruption** — `rustup` downloads 200MB of toolchain successfully but fails on a small component with `error decoding response body`. This is transient HTTPS corruption through TPROXY. Fix: add a retry loop.
4. **Apply all identified fixes in one commit** — never fix one thing at a time and wait for CI to retry each.

For systematic network-level diagnosis (distinguishing host vs container vs image issues), see `references/container-network-diagnostics.md`.

### 1. Enable Runner Debug Logging

Add `log.level: debug` to config.yaml to see detailed per-step output (the exact error messages from each action):

```yaml
log:
  level: debug
```

Without debug logging, you only see step names and exit codes. Debug logs reveal `OCI runtime exec failed: exec: \"node\": not found` and similar hidden failures.

### 2. Check Job Steps via API

Gitea's REST API exposes job-level detail including which steps ran and which failed:

```bash
TOKEN="your-api-token"

# List jobs for a specific run
curl -s -H "Authorization: token $TOKEN" \
  "http://gitea:3000/api/v1/repos/owner/repo/actions/runs/<RUN_ID>/jobs"

# Download full logs (zstd compressed)
curl -s -H "Authorization: token $TOKEN" \
  "http://gitea:3000/api/v1/repos/owner/repo/actions/runs/<RUN_ID>/logs"
```

The `/jobs` endpoint shows each step's `status` and `conclusion` — use this to find exactly where the build failed.

### 3. Gitea CLI Quirks

The `gitea actions` subcommand is NOT available in all versions. If `gitea actions run list` fails with "No help topic for 'run'", use the REST API instead:

```bash
# Direct API query (works everywhere)
curl -s -H "Authorization: token $TOKEN" \
  "http://gitea:3000/api/v1/repos/owner/repo/actions/runs?limit=5"
```

Token generation: some Gitea versions don't support `--token-name`. Use bare:
```bash
docker exec -u git gitea gitea admin user generate-access-token -u <user> --scopes all
# Returns: Access token was successfully created: <SHA1_TOKEN>
```

### 4. Common Failure Patterns

| Log Snippet | Root Cause | Fix |
|:------------|:-----------|:----|
| `exec: "node": not found` | Container has no Node.js; JS actions fail | Install `nodejs` in apt-get step, or replace JS actions with run: commands |
| `actions/checkout@v4` → failure, exit 1 | Same as above — actions/checkout is a JS action | Add nodejs to build deps |
| Total CI runs < expected count | Gitea auto-cleaned old runs (retention policy) | Check total_count in API; runs may be pruned |
| `curl: (35) SSL_ERROR_SYSCALL` | mihomo TPROXY blocks container HTTPS | Pre-cache toolchain, or add router bypass rule for NAS IP |
| `error decoding response body` during rustup | Intermittent HTTPS corruption through TPROXY — large downloads succeed but small ones fail | Add retry loop around `rustup target add` (see GFW Option E) |
| `error: could not download nonexistent rust version` | TUNA/rsproxy mirror doesn't have the pinned toolchain version | Remove `RUSTUP_DIST_SERVER` env var, use official source |
| `"Only signed in user is allowed to call APIs."` | API call without auth token (e.g. plain `curl http://gitea:3000/api/v1/...`) | Add `-H \"Authorization: token $TOKEN\"` header. This message distinguishes auth issues from network/hostname problems. |

**Critical issue:** `actions/checkout@v4`, `actions/cache@v4`, and `actions/upload-artifact@v4` are JavaScript actions that require `node` inside the job container. Standard Linux images (`rust:latest`, `ubuntu:24.04`, `alpine`) do NOT have Node.js, causing:

**⚠️ `|| true` is dangerous on install steps.** A `|| true` suffix on apt-get install swallows failures silently — the step reports `success` even when a package (like `nodejs`) fails to install. The Checkout step then fails with `node: not found` and the root cause is invisible without debug logs. **Fix:** Remove `|| true` from install steps, or at minimum verify critical binaries post-install:

```yaml
- name: Install build deps
  run: |
    apt-get update -qq
    apt-get install -y -qq nodejs
    which node || echo "WARNING: node not found after installing nodejs"

```
Error: runc: exec failed: unable to start container process:
  exec: "node": executable file not found in $PATH
```

### Root Cause

- GitHub-hosted runners use special pre-built images with Node.js pre-installed
- Self-hosted runners (Gitea Actions) run whatever container image you specify — standard distros don't include Node.js
- `run:` steps work fine (shell commands); only `uses:` steps with JS-based actions fail
- Docker-based actions (those citing `image:` in their action.yml) work fine

### Quick Fix: Install nodejs via apt

Instead of replacing all JS actions with manual commands, simply add `nodejs` to your `apt-get install` step. This works for Debian/Ubuntu-based images (`rust:latest`, `ubuntu:24.04`):

```yaml
- name: Install build deps
  run: |
    apt-get update -qq
    apt-get install -y -qq \
      protobuf-compiler pkg-config libssl-dev musl-tools upx-ucl \
      nodejs     # ← this one line enables actions/checkout@v4 etc.
```

Then `actions/checkout@v4` and other JS actions will work normally. This is the simplest fix when using standard Linux images — no need to rewrite workflow steps.

### Multi-Binary Release (Template — Core+CLI + Web + Web-Embed)

For Rust workspaces with multiple packages producing separate binaries, build each in dependency order so cargo's incremental cache speeds up subsequent invocations. **Build order matters:**

1. Primary package (e.g. `easytier`) → produces 2 binaries from `[[bin]]` entries in a single invocation
2. Secondary package (e.g. `easytier-web`) standalone
3. Same package with alternate features (e.g. `easytier-web --features embed`) — rename output to avoid overwrite

```yaml
name: Build Release from Upstream Tag
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Upstream tag to build"
        required: true
        type: string

jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - name: Install build deps & Rust
        run: |
          apt-get update -qq
          apt-get install -y -qq git curl gcc protobuf-compiler libprotobuf-dev \
            pkg-config libssl-dev musl-tools libclang-dev clang make nodejs
          which node || ln -sf /usr/bin/nodejs /usr/bin/node || true
          curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
          . "$HOME/.cargo/env"
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Checkout & switch to upstream tag
        env:
          GIT_TOKEN: ${{ github.token }}
        run: |
          git clone --depth 1 "https://git:${GIT_TOKEN}@gitea:3000/owner/repo.git" .
          git remote add upstream https://github.com/Upstream/Project.git 2>/dev/null || true
          git fetch upstream --tags 2>&1
          git checkout refs/tags/${{ inputs.version }} 2>/dev/null || \
            git checkout upstream/${{ inputs.version }} 2>/dev/null || {
            echo "ERROR: Tag ${{ inputs.version }} not found"
            exit 1
          }

      - name: Add musl target
        run: |
          . "$HOME/.cargo/env"
          for i in 1 2 3 4 5; do
            rustup target add x86_64-unknown-linux-musl && break
            sleep 10
          done

      - name: 🏗️ Build core + cli (primary package)
        run: |
          . "$HOME/.cargo/env"
          cargo build --release --package=easytier \
            --features "magic-dns,jemalloc" --target x86_64-unknown-linux-musl

      - name: 🏗️ Build web (standalone)
        run: |
          . "$HOME/.cargo/env"
          cargo build --release --package=easytier-web --target x86_64-unknown-linux-musl

      - name: 🏗️ Build web-embed (alt features)
        run: |
          . "$HOME/.cargo/env"
          cargo build --release --package=easytier-web \
            --features embed --target x86_64-unknown-linux-musl
          cp target/x86_64-unknown-linux-musl/release/easytier-web \
            target/x86_64-unknown-linux-musl/release/easytier-web-embed

      - name: UPX compress (optional)
        run: upx --lzma --best target/x86_64-unknown-linux-musl/release/easytier-* || true

      - name: Package
        run: |
          VERSION="${{ inputs.version }}"
          mkdir -p dist
          cp target/x86_64-unknown-linux-musl/release/easytier-core      dist/easytier-core-x86_64-${VERSION}
          cp target/x86_64-unknown-linux-musl/release/easytier-cli       dist/easytier-cli-x86_64-${VERSION}
          cp target/x86_64-unknown-linux-musl/release/easytier-web       dist/easytier-web-x86_64-${VERSION}
          cp target/x86_64-unknown-linux-musl/release/easytier-web-embed dist/easytier-web-embed-x86_64-${VERSION}
          cd dist && sha256sum * > CHECKSUMS-${VERSION}.txt

      - name: Create Gitea Release
        id: create_release
        env:
          GITEA_TOKEN: ${{ github.token }}
        run: |
          VERSION="${{ inputs.version }}"
          RELEASE_JSON=$(curl -s -X POST \
            -H "Authorization: token ${GITEA_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{"tag_name":"'"${VERSION}"'-custom","name":"EasyTier '"${VERSION}"' (custom features)","body":"Build of upstream '"${VERSION}"'","draft":false,"prerelease":false}' \
            "http://gitea:3000/api/v1/repos/owner/repo/releases")
          RELEASE_ID=$(echo "$RELEASE_JSON" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
          echo "release_id=$RELEASE_ID" >> $GITHUB_OUTPUT

      - name: Upload Release Assets
        env:
          GITEA_TOKEN: ${{ github.token }}
        run: |
          RELEASE_ID=${{ steps.create_release.outputs.release_id }}
          for f in dist/*; do
            [ -f "$f" ] || continue
            curl -s -X POST \
              -H "Authorization: token ${GITEA_TOKEN}" \
              -F "attachment=@$f" \
              "http://gitea:3000/api/v1/repos/owner/repo/releases/${RELEASE_ID}/assets?name=$(basename "$f")"
          done
```

The key invariants:
- **`--package=<workspace-member>`** builds all `[[bin]]` targets inside that package — one command, multiple binaries
- **`--features` are package-scoped** — `easytier-web` doesn't have `magic-dns` or `jemalloc` features
- **`--features embed` produces different binary** with same filename — rename it before UPX/packaging
- **Gitea Release tag** uses `{VERSION}-{suffix}` pattern (e.g. `v2.6.4-magicdns`) to stay distinct from upstream tags
- **`GITEA_TOKEN` env var** is auto-injected by Gitea Actions — use `${{ github.token }}`

**⚠️ `node` binary vs `nodejs` binary:** On some Debian-based images (particularly `rust:*-slim-bookworm`), `apt-get install nodejs` installs the binary as `/usr/bin/nodejs`, NOT `/usr/bin/node`. The `actions/checkout@v4` runner looks for `node` in PATH and fails with `exec: \"node\": executable file not found`. **Fix:** Verify the binary after install, and create a symlink if needed:

```yaml
- name: Install build deps
  run: |
    apt-get update -qq
    apt-get install -y -qq protobuf-compiler pkg-config libssl-dev musl-tools upx-ucl nodejs
    which node || ln -sf /usr/bin/nodejs /usr/bin/node
```

**Trade-off:** Adds ~30MB to the container (nodejs runtime) and a few seconds to the install step. The alternative (replacing all JS actions with manual `run:` steps) saves this overhead but requires more workflow maintenance. Choose based on whether you prefer simpler workflows or smaller containers.

### Workflow Template: No JavaScript Actions (for minimal containers)

When using `rust:latest` or `ubuntu:24.04`, replace all JS `uses:` steps with plain `run:` commands:

```yaml
steps:
  # ─── Debian/Ubuntu base: install everything first ───
  - name: Install build deps & Rust toolchain
    run: |
      apt-get update -qq
      # ubuntu:24.04 minimal has NO git, curl, or gcc!
      apt-get install -y -qq git curl gcc protobuf-compiler libprotobuf-dev \
        pkg-config libssl-dev musl-tools upx-ucl || true
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
      . "$HOME/.cargo/env"            # ← MUST source in same step!
      echo "$HOME/.cargo/bin" >> $GITHUB_PATH
      rustup target add x86_64-unknown-linux-musl

  # ─── Manual checkout (replaces actions/checkout@v4) ───
  - name: Checkout
    env:
      GIT_TOKEN: ${{ github.token }}
    run: |
      # Use external URL — container bridge can't reach LAN IPs
      # (especially if 10.20.x.x is routed through EasyTier overlay)
      git clone --depth 1 \
        "https://git:${GIT_TOKEN}@git01.wrt.astra-lab.org/owner/repo.git" .
      echo "Checked out: $(git log --oneline -1)"

  # ─── Build (replaces actions/cache@v4) ───
  - name: Build
    run: |
      cargo build --release --features "magic-dns,jemalloc" \
        --target x86_64-unknown-linux-musl

  # ─── Upload via Gitea API (replaces actions/upload-artifact@v4) ───
  - name: Upload artifacts
    env:
      GITEA_TOKEN: ${{ github.token }}
    run: |
      for f in dist/*; do
        [ -f "$f" ] || continue
        curl -s -X POST \
          -H "Authorization: token ${GITEA_TOKEN}" \
          -F "attachment=@$f" \
          "https://git01.wrt.astra-lab.org/api/v1/repos/owner/repo/actions/artifacts?run_id=${{ github.run_id }}"
        echo "Uploaded: $f"
      done
```

## 13. Container Networking

**This is the #1 gotcha with self-hosted runners.** Depending on deployment architecture, the CI container may not be able to reach the Gitea server. The symptom:

```
fatal: unable to access 'http://10.20.3.10:3000/...'
Couldn't connect to server after 135604 ms
```

### There are two fundamental deployment strategies:

### Strategy A: Runner on Same Docker Host as Gitea (EASY) ✅ RECOMMENDED

When act_runner runs as a Docker container on the **same Docker daemon as Gitea**:

1. Join the runner container to Gitea's Docker network
2. CI job containers are also spawned on that network
3. Checkout/upload use Docker DNS: `http://gitea:3000`

```yaml
# docker run --network gitea_default ...

# In build.yml checkout step:
    run: |
      git clone --depth 1 \
        "http://git:${GIT_TOKEN}@gitea:3000/owner/repo.git" .

# In build.yml upload step:
    run: |
      GITEA_URL="http://gitea:3000"
      curl -F "attachment=@file" \
        "${GITEA_URL}/api/v1/repos/.../actions/artifacts?run_id=..."
```

**Pros:** No routing issues, no external dependencies, fast (same host), simple.
**Cons:** Requires Docker on the Gitea host; not possible if Gitea runs on a machine without Docker.

### Strategy B: Runner on Separate Host (HARDER)

When runner and Gitea are on different physical machines or different Docker daemons, the CI containers must reach Gitea through the network.

### Root Cause: EasyTier Overlay Routing

On hosts with EasyTier mesh VPN, the `10.20.0.0/16` subnet is routed through the `easytier0` virtual interface, NOT through the physical network:

```
ip route show | grep 10.20
→ 10.20.0.0/16 dev easytier0 proto kernel scope link src 10.20.40.1
```

When the CI container (on Podman bridge `10.88.x.x`) tries to reach `10.20.3.10:3000` (DS425Plus Gitea), the traffic goes through `easytier0` → EasyTier mesh → fails because DS425Plus isn't on EasyTier.

The same issue applies to any LAN subnet routed through overlay VPNs.

### The Fix: Use External Public URL

Since the CI container **can** reach the internet (it downloaded apt packages and Rust toolchain via NAT), use the Gitea instance's public/external URL:

```yaml
- name: Checkout
  env:
    GIT_TOKEN: ${{ github.token }}
  run: |
    git clone --depth 1 \
      "https://git:${GIT_TOKEN}@git01.wrt.astra-lab.org/owner/repo.git" .
```

This traffic goes: container → host NAT → router → reverse proxy → Gitea server.

### Alternative Fixes (if external URL is not available)

**A. Configure act_runner extra_hosts** — maps hostname to router IP (not Gitea IP, since the router does SSL termination):

```yaml
# /etc/act_runner/config.yaml
container:
  extra_hosts:
    - "git01.wrt.astra-lab.org:192.168.0.1"   # ← router, not NAS IP!
```

Then `systemctl restart act_runner`.

**B. Use host networking** — containers share host's full network stack:
```yaml
container:
  network_mode: "host"
```
⚠️ Security: containers bypass all network isolation.

**C. Use internal HTTP URL** — only if the host has a direct physical route to the Gitea server (not via overlay VPN):
```yaml
run: |
  git clone "http://git:${GIT_TOKEN}@10.20.3.10:3000/owner/repo.git"
```
⚠️ Do NOT use this if `10.20.x.x` is routed through EasyTier. Verify with: `ip route get <Gitea-IP>`

## 14. Known Issues

### cgroup v2 fork() Failure with rust:latest + Podman

- **Symptom:** `Cannot fork` error when running shell commands inside `rust:latest` container on Podman with cgroup v2:
  ```
  /var/run/act/workflow/0.sh: 2: Cannot fork
  ```
- **Root cause:** `rust:latest` (Debian bookworm-based) + Podman cgroup v2 have a process-forking compatibility issue in isolated bridge networks. The container's PID 1 (`/bin/sleep 10800`) can't fork children for `git init`, `apt-get`, etc.
- **Fix:** Do NOT use `container: image: rust:latest`. Use the runner's default label image (`ubuntu-24.04` from `ubuntu:24.04`) and install Rust via rustup.

### ubuntu:24.04 Minimal Image Missing Core Tools

- **Symptom:** `git: command not found`, `curl: command not found`
- **Root cause:** Docker's `ubuntu:24.04` is a minimal image with only `apt` and basic libraries. No `git`, `curl`, `gcc`, or other dev tools.
- **Fix:** Add ALL of these to `apt-get install`:
  ```yaml
  - name: Install build deps
    run: |
      apt-get update -qq
      apt-get install -y -qq git curl gcc protobuf-compiler libprotobuf-dev \
        pkg-config libssl-dev musl-tools upx-ucl || true
  ```

### Runner Picks Up Tasks But Never Executes

- **Symptom:** `task N repo is alrcatraz/easytier` appears in logs but no container starts
- **Check:** Is `DOCKER_HOST` set correctly? Does the socket exist?
  ```bash
  sudo curl -s --unix-socket /run/podman/podman.sock http://localhost/_ping
  ```
- **Fix:** If `OK`, verify the service env var is loaded:
  ```bash
  sudo systemctl cat act_runner | grep DOCKER_HOST
  ```

### Docker Hub Pull Fails Behind GFW

- **Symptom:** `failed to resolve reference "docker.io/library/rust:latest": failed to authorize: ... EOF`
- **Fix:** Configure registry mirrors (see GFW section above)
- **Verification:** After configuring mirrors, try pulling directly:
  ```bash
  sudo podman pull docker.io/library/hello-world
  ```

### SELinux Blocking

- **Symptom:** `kill -9` returns `EPERM` even as root on SELinux-enforcing systems
- **Cause:** SELinux `unconfined_service_t` processes (systemd services) have restricted signal delivery from `unconfined_t` (shell) contexts
- **Workaround:** Use a compiled C program with `sudo`, or use `systemctl kill`
- **Runner impact:** If act_runner runs as root systemd service, SELinux context is `unconfined_service_t:s0` and container operations should work — but signal delivery from debug shell may fail.

### Tag Pushes Trigger Wrong Workflow

- **Symptom:** CI runs `ohos.yml` or other upstream workflow files when you push tags
- **Cause:** The tag commit contains upstream `.github/workflows/` files. Gitea runs workflow files found in the **commit being pushed**, not the default branch
- **Fix:** Remove tag triggers from your workflow. Use `workflow_dispatch` + a separate cron job for tag builds.

### Git Push Fails: \"unable to migrate objects to permanent storage\"

- **Symptom:** `git push` returns `remote rejected: unable to migrate objects to permanent storage` even though the HTTP response is a normal 200. The push succeeds at the transport layer but fails at Gitea's storage backend.
- **Root cause:** Gitea's storage backend (filesystem by default) fails to finalise the new objects. Usually disk space, filesystem permissions, or a transient NFS/volume issue on the host running Gitea.
- **Diagnosis:**
  ```bash
  # Check Gitea host disk space
  ssh user@nas \"df -h /docker/gitea\"

  # Check repo permissions
  ssh user@nas \"ls -la /docker/gitea/git/repositories/owner/repo.git/objects/\"

  # Check Gitea container logs
  docker logs gitea --tail 50 | grep -i error

  # Verify Gitea cron tasks (git_gc_repos may be disabled)
  curl -s -H \"Authorization: token $TOKEN\" \\
    \"$GITEA_URL/api/v1/admin/cron\" | python3 -c \"import sys,json; [print(f'{c[\\\"name\\\"]}: next={c[\\\"next\\\"]}') for c in json.load(sys.stdin)]\"
  ```
- **Emergency push workaround** — push directly from the Gitea container (bypasses the HTTP transport layer):
  ```bash
  # From the Gitea host
  mkdir -p /tmp/emergency-push
  cd /tmp/emergency-push

  # Clone the remote bare repo
  docker exec -u 0 gitea git clone --bare \\
    file:///data/git/repositories/owner/repo.git repo.git

  # Push your new commits from the working clone
  cd /path/to/working-clone
  git push file:///tmp/emergency-push/repo.git main

  # Sync back to Gitea's storage
  docker cp /tmp/emergency-push/repo.git/. \\
    gitea:/data/git/repositories/owner/repo.git/

  # Set correct ownership
  docker exec -u 0 gitea chown -R git:git \\
    /data/git/repositories/owner/repo.git/
  ```
- **Prevention:** Ensure `git_gc_repos` cron is enabled in Gitea config, and monitor disk space on the Gitea host. For Docker-based Gitea, ensure the volume backing the git data has sufficient inodes.

### Permission Errors After `docker exec git gc`

- **Symptom:** After running `docker exec gitea git gc --aggressive` via SSH to diagnose storage issues, subsequent `git push` returns `cannot update the ref: unable to append to ./logs/refs/heads/main: Permission denied`.
- **Root cause:** `docker exec` runs as `root` by default inside the Gitea container. `git gc` rewrites pack files, reflogs, and other metadata with root ownership (`root:root` instead of `git:git`). Gitea's web service runs as user `git` and cannot write to root-owned files.
- **Fix:** Reset ownership:
  ```bash
  docker exec gitea chown -R git:git /data/git/repositories/owner/repo.git/
  ```
  **Always** run `chown -R git:git` after any `docker exec` git command on the repo directory.
- **Prevention:** Run git commands inside the container as the git user to begin with:
  ```bash
  docker exec -u git gitea git -C /data/git/repositories/owner/repo.git gc
  ```

## 15. Pitfalls

1. **`--features` overrides default features in Cargo.** `cargo build --features=jemalloc` **replaces** the `default` features set (which includes `magic-dns`). Always explicitly include both: `--features "magic-dns,jemalloc"`.
2. **Tag push triggers run tag-commit workflows.** Your `.gitea/workflows/` only exists on your default branch — tag commits point to upstream commits that don't have your workflow files.
3. **Podman socket permissions.** Rootful Podman socket (`/run/podman/podman.sock`) is root:root, mode 660. Only root can use it. The act_runner systemd service runs as root, so this is fine.
4. **`DOCKER_HOST` env var.** Without this, act_runner looks for `/var/run/docker.sock` (Docker's socket). After removing Docker and installing podman-docker, you must set this env var.
5. **First build is slow.** `cargo build` downloads all crate dependencies on first run (~5-10 minutes). Without `actions/cache` (no Node.js in container), every fresh container does a full download.
6. **Runner labels must match workflow.** If your workflow says `runs-on: ubuntu-24.04`, the runner must have `ubuntu-24.04` in its labels. Labels are defined at registration time.
7. **JS actions fail silently in minimal containers.** `actions/checkout@v4` (and cache, upload-artifact) need `node` in the container. `rust:latest` and `ubuntu:24.04` don't have it. Replace with manual `git clone` + `curl` API upload, or use a `node:*` base image.
8. **`rustup` not in PATH after curl install.** The `curl sh.rustup.rs | sh` installs to `$HOME/.cargo/bin`. `$GITHUB_PATH` only affects subsequent steps. In the same `run:` block, source the env explicitly: `. "$HOME/.cargo/env"`.
9. **`ubuntu:24.04` minimal is missing git, curl, gcc.** These are not installed. Add all three to `apt-get install`.
10. **Container bridge can't reach Gitea hostname.** Podman's isolated bridge network blocks hostname resolution and LAN IP access. Fix: configure act_runner `extra_hosts`, use host networking, or use internal HTTP URLs in clone commands.
11. **`:host` labels default when no config.yaml exists.** act_runner v0.6.1 defaults to `:host` mode for all labels if no `runner.labels` section is defined in config.yaml. In `:host` mode, job steps run directly on the runner's host OS (not in Docker). On Synology DSM, this fails with `apt-get: command not found`. **Fix:** Always provide a config.yaml with `docker://` format labels.
12. **Env-var labels get `:host` appended.** `GITEA_RUNNER_LABELS="ubuntu-latest,ubuntu-24.04"` env var causes the runner to internally transform labels to `ubuntu-latest:host ubuntu-24.04:host`. To prevent this, use config.yaml with explicit `docker://` labels instead of env vars.
13. **Synology DSM: Docker group doesn't exist by default.** To grant Docker access to a user on DSM:
    ```bash
    # Create docker group and add user
    sudo /usr/syno/sbin/synogroup --add docker Alrcatraz
    # Fix socket permissions to group
    sudo chown root:docker /var/run/docker.sock
    ```
    On DSM, `usermod` and `groupadd` are not available — use `synogroup` instead.
14. **`rust-toolchain.toml` overrides default Rust channel.** When a repo has a `rust-toolchain.toml` file (e.g. pinning to 1.95), `rustup target add` done in the install step (for the default stable) is LOST when the toolchain switches after checkout. Build step fails with `can't find crate for core`. **Fix in build:** Re-run both `. "$HOME/.cargo/env"` AND `rustup target add x86_64-unknown-linux-musl` before `cargo build`. **Better fix:** Set `RUSTUP_TOOLCHAIN=stable` env var before running cargo — this bypasses `rust-toolchain.toml` entirely and keeps the currently installed stable toolchain active. The env var works in both CI and docker-run environments: `docker run -e RUSTUP_TOOLCHAIN=stable ...` or as a step-level env in CI:
    ```yaml
    - name: Build
      env:
        RUSTUP_TOOLCHAIN: stable
      run: |
        . "$HOME/.cargo/env"
        cargo build --release
    ```
15. **CI containers behind transparent proxy cannot reach external HTTPS.** On a NAS/Docker host behind mihomo TPROXY, CI containers on `gitea_default` bridge network may fail to download Rust toolchain with `SSL_ERROR_SYSCALL`. **Fix:** Pre-cache the toolchain in a custom runner image, use `network_mode: host`, or add a router bypass rule (see "GFW / CI Container Egress" section).
16. **`docker exec` git commands change file ownership to root.** Running `docker exec gitea git gc` (or any git command via `docker exec` without `-u git`) runs as root, causing Gitea to later fail writing to reflogs/pack files. **Always** follow with `docker exec gitea chown -R git:git /data/git/repositories/...` or use `docker exec -u git gitea git ...` from the start.
17. **`upx-ucl` package is Ubuntu-specific; Debian bookworm uses `upx`.** The `rust:*-slim-bookworm` images are Debian-based. `apt-get install upx-ucl` fails with `E: Unable to locate package upx-ucl` on bookworm. Use `upx` instead, or skip it (the UPX step already has `|| true`). In templates targeting Ubuntu (e.g. `ubuntu:24.04`), `upx-ucl` is correct.

18. **`--package=<name>` only works for workspace-level packages, not for `[[bin]]` targets within a package.** When a `Cargo.toml` defines `[[bin]]` entries (e.g. `easytier-cli`), those are binaries WITHIN the enclosing package, not separate packages. `cargo build --package=<enclosing-package>` builds ALL binaries defined inside it. A separate `cargo build --package=<binary-name>` fails with `cannot specify features for packages outside of workspace` because cargo looks for a workspace member named `<binary-name>`, which doesn't exist. **Never** write a separate build command for each `[[bin]]` — one `cargo build --package=<package>` covers all of them.

19. **`--features` are package-scoped, not workspace-scoped.** When building a workspace member like `easytier-web`, passing features that belong to a different package (e.g. `--features "magic-dns,jemalloc"` from the `easytier` package) causes cargo to fail. Each workspace member defines its own `[features]` — only those features are valid for that package. For `easytier-web`, valid features are `default = []` and `embed = ["dep:axum-embed"]`.

20. **`easytier-web` with `embed` feature produces a behaviorally different binary with the same filename.** Building `cargo build --package=easytier-web --features embed` compiles the web frontend assets into the binary via `axum-embed`. The output filename is identical (`easytier-web`), but the embedded-variant binary is self-contained. Distinguish them via build flags, not filename.

21. **`curl` is missing in `rust:*-slim-bookworm` images.** The Upload step fails with `curl: command not found` (exit code 127) when using `curl` to post artifacts to Gitea API. Always add `curl` to the `apt-get install` line in the Install build deps step. Without it, compiled binaries are built but cannot be uploaded as artifacts.

22. **`rust:alpine` cannot compile proc-macros for musl target.** When using `rust:alpine` (musl-based), `cargo build --release --package easytier-web` fails with `error: cannot produce proc-macro for 'async-recursion v1.1.1' as the target 'x86_64-unknown-linux-musl' does not support these crate types`. Proc-macro crates compile to shared libraries that must be loadable by the host compiler — Alpine's musl libc conflicts with the proc-macro ABI. **Fix:** Use `rust:latest` (Debian-based, glibc) with explicit `--target x86_64-unknown-linux-musl` for musl cross-compilation. The Debian image's glibc toolchain correctly handles proc-macro compilation for musl targets.

23. **Runner-only-on-NAS constraint means CI job containers share Docker with Gitea.** When act_runner runs as a Docker container on the same host as Gitea (DS425Plus NAS), CI containers are spawned on the `gitea_default` bridge network. Implications:
    - `curl` must be explicitly installed in the build image — `rust:*-slim-bookworm` lacks it
    - Upload API uses internal Docker DNS: `http://gitea:3000/...` (works because both are on the same Docker network)
    - The NAS CPU (J3455) is slow — a musl+LTO build takes ~25 minutes, vs ~5-10 min on a modern laptop
    - Container networking on the NAS goes through the router's mihomo TPROXY — retry loops are needed for `rustup target add`

24. **`cargo build --package=<pkg>` builds ALL `[[bin]]` targets within that package.** One invocation compiles every binary defined in the `[[bin]]` sections of that package's `Cargo.toml`. Do NOT add separate build commands for each binary — they're redundant and may trigger spurious errors (see Pitfall 18). For `easytier`, `cargo build --package=easytier` produces both `easytier-core` and `easytier-cli` in one pass.

25. **`libclang-dev clang` are required for bindgen-based crates.** When building `easytier-web` (or any crate using `bindgen` for FFI bindings), `rust:latest` (Debian) and `rust:*-slim-bookworm` do NOT include `libclang-dev` or `clang`. The build fails with: `Unable to find libclang: "couldn't find any valid shared libraries matching: ['libclang.so', ...]"`. **Fix:** Always add `libclang-dev clang` to `apt-get install` in the build deps step:
    ```yaml
    apt-get install -y -qq protobuf-compiler pkg-config libssl-dev musl-tools \\
      libclang-dev clang make curl nodejs
    ```
    Without these, `bindgen` cannot parse C headers for FFI crates like `kcp-sys`, `libdbus-sys`, and `tikv-jemalloc-sys`.

26. **Gitea 1.26.x artifact upload API silently fails.** `POST /api/v1/repos/{owner}/{repo}/actions/artifacts?run_id=...` returns HTTP 200 but files are never stored on disk. The `actions_artifacts` directory stays empty and the API lists 0 artifacts. **Fix:** Replace artifact upload with Gitea Release creation (`POST /releases` → `POST /releases/{id}/assets`). See the "Gitea Artifact Upload Caution" section above.

27. **`--features` are package-scoped, not workspace-scoped.** When building a workspace member like `easytier-web`, passing features that belong to a different package (e.g. `--features "magic-dns,jemalloc"` from the `easytier` package) causes cargo to fail. Each workspace member defines its own `[features]`. For `easytier-web`, valid features are `default = []` and `embed = ["dep:axum-embed"]`.

28. **`cargo build -p <pkg>` builds ALL `[[bin]]` targets within that package.** Do NOT add a separate build step for each binary — it's redundant and can trigger `cannot specify features for packages outside of workspace`. One `--package` invocation covers all `[[bin]]` entries.

29. **Persistent podman volumes for rustup cache prevent re-download.** Without a volume mount for `/usr/local/rustup`, every `podman run --rm` container loses the musl target and re-downloads ~50MB. Use `podman volume create rustup-cache` and mount it as `-v rustup-cache:/usr/local/rustup` for persistent toolchain caching. See `references/easytier-ci-pipeline.md` for the full setup.

26. **Gitea 1.26.x artifact upload API silently fails.** `POST /api/v1/repos/{owner}/{repo}/actions/artifacts?run_id=...` returns HTTP 200 but files are never stored on disk — the `actions_artifacts` directory stays empty. **Fix:** Replace artifact upload with Gitea Release creation (`POST /releases` → `POST /releases/{id}/assets`). See "Workflow Template: Upstream Tag → Gitea Release" section.

27. **Podman volume mount over `/usr/local/cargo` overwrites rustup/cargo binaries.** When running `rust:latest` in podman with a cargo mirror config, do NOT mount a directory over `/usr/local/cargo`:
    ```bash
    # ❌ WRONG — overwrites rustup AND cargo binaries from the container image
    -v /tmp/cargo-config:/usr/local/cargo:Z

    # ✅ CORRECT — mount individual config file only
    -v /tmp/cargo-tuna-config.toml:/usr/local/cargo/config.toml:Z
    ```
    `rust:latest` has `rustup` at `/usr/local/cargo/bin/rustup` and `cargo` at `/usr/local/cargo/bin/cargo`. Mounting a directory over `/usr/local/cargo` removes these binaries, causing `sh: rustup: not found` in subsequent steps. Mount individual files to add config without losing the toolchain.

28. **`runs-on: rust` custom label for Rust CI.** Define a label like `"rust:docker://rust:1.84-slim-bookworm"` in config.yaml. This image has cargo/rustc pre-installed, so you skip the rustup curl step. Still need `apt-get install musl-tools libclang-dev clang make curl nodejs` for cross-compilation and bindgen.

29. **Rust minor version bumps in Cargo.lock can break API compatibility.** When a Cargo.lock resolves to a newer minor version of a dependency (e.g. `rust-embed` 8.5.0 → 8.11.0), the new version may rename traits (`Embed` → `RustEmbed`), breaking dependent crates like `axum-embed`. **Fix:** Pin the dependency in Cargo.toml with `=` prefix:
    ```toml
    # Before (resolves to latest 8.x, may break)
    rust-embed = { version = "8.5.0", features = ["debug-embed", "include-exclude"] }

    # After (locked to exactly 8.5.0)
    rust-embed = { version = "=8.5.0", features = ["debug-embed", "include-exclude"] }
    ```
    **Diagnosis:** If a Rust build fails with `the trait bound X: Y is not satisfied` pointing to a dependency's source in the cargo registry, and the version was auto-resolved from Cargo.lock, check if a minor version bump changed the trait/API. Delete the package's entries from Cargo.lock and pin the version in Cargo.toml.

    **Root cause:** `rust-embed` v8.x made multiple breaking changes in minor versions (renaming the trait from `Embed` to `RustEmbed`). Cargo's semver resolution treats this as compatible, but the dependent crate (`axum-embed`) expects the old API. This is a crate author error (should have been a major version bump), but the fix is pinning.

30. **`rustup target add x86_64-unknown-linux-musl` succeeds but cargo still can't find the target.** In `rust:latest` image with Rust 1.96+/1.97+, `rustup target add x86_64-unknown-linux-musl` exits with code 0 (confirmed by `set -euo pipefail` not aborting), but `cargo build --target x86_64-unknown-linux-musl` immediately fails with `error[E0463]: can't find crate for 'core'`. The command downloads and installs the target's std library, but cargo's sysroot lookup doesn't find it — possibly a path inconsistency in the Docker image's pre-configured toolchain layout. **Diagnosis:** Run `rustc --print target-list | grep musl` to verify the target strings rustc knows, and check `rustup show` for the active toolchain path. **Fixes:** (a) Try `rustup target add --toolchain stable x86_64-unknown-linux-musl` to be explicit, (b) Use Alpine-native `apk add rust cargo` instead (see Pitfall #31), (c) Use `debian:12-slim` + install rustup manually (skipping the `rust:latest` image entirely).

31. **Alpine-native `apk add rust cargo` avoids rustup target issues.** Instead of using `rust:latest` (Debian) with `rustup target add x86_64-unknown-linux-musl`, build MUSL static binaries directly on Alpine using its native Rust packages. The key advantage: Alpine's `rust` and `cargo` packages are themselves compiled against MUSL, so no cross-compilation target is needed — `cargo build --release` natively produces fully static MUSL binaries. **Setup:**

32. **`RUSTUP_TOOLCHAIN=stable` overrides `rust-toolchain.toml` channel pinning.** When a repo has `rust-toolchain.toml` (e.g. `channel = "1.95"`) and the CI image has a different Rust version, cargo detects the mismatch and tries to download/switch to the pinned channel. If that channel's artifacts are no longer served (e.g. Rust 1.95 superseded by 1.96/1.97), the download fails with `error decoding response body` or `component download failed`. **Fix:** Set `RUSTUP_TOOLCHAIN=stable` before cargo runs:
    ```yaml
    - name: Build
      env:
        RUSTUP_TOOLCHAIN: stable    # ← bypasses rust-toolchain.toml
      run: |
        . "$HOME/.cargo/env"
        rustup target add x86_64-unknown-linux-musl
        cargo build --release --target x86_64-unknown-linux-musl
    ```
    This tells rustup to use the currently installed stable toolchain regardless of what `rust-toolchain.toml` says. The env var is available to any child process — works with both `docker run -e` and CI runner env injection. **Also works with the BlackDex/rust-musl image** — pass `-e RUSTUP_TOOLCHAIN=stable` to the docker run command so the build container uses its pre-installed stable Rust instead of trying to install a specific channel.

33. **`BlackDex/rust-musl` image solves both rustup target add failures and OOM from compiling OpenSSL from source.** This Docker image (Ubuntu 26.04 base with crosstool-ng toolchain) pre-compiles static OpenSSL v3.5.7, ZLib, cURL, SQLite, and MariaDB/PostgreSQL libs — all linked statically against MUSL. The key advantages over `rust:latest` + `--target musl`:
    - **No `rustup target add` needed** — the MUSL target is the default
    - **Pre-compiled OpenSSL** — avoids ~5min+ source compilation and ~1GB+ RAM spike from compiling openssl-sys
    - **Works on memory-constrained hosts** (NAS, 4GB RAM VPS) where compiling OpenSSL from source causes OOM
    - **Simple usage:** just mount source to `/home/rust/src` and run `cargo build --release`
    
    Usage:
    ```bash
    docker run --rm \
      -v "$(pwd)":/home/rust/src \
      -e RUSTUP_TOOLCHAIN=stable \
      ghcr.io/blackdex/rust-musl:x86_64-musl-stable \
      cargo build --release --features=embed
    ```
    Tags: `x86_64-musl-stable`, `x86_64-musl-stable-1.96.0` (pinned version), `aarch64-musl-stable` (ARM64). Available on GitHub Container Registry (`ghcr.io/blackdex/rust-musl`), Docker Hub (`blackdex/rust-musl`), and Quay.io.
    
    **Caveat:** The image is ~1GB (larger than `rust:latest`'s ~1.2GB but similar). The first pull takes time — use a persistent volume for the image layer cache. The pre-compiled OpenSSL saves enough build time to offset the larger image size on repeated builds.
    
    **⚠️ Critical: `CARGO_BUILD_TARGET` env var changes target directory to workspace root.** The blackdex image sets `CARGO_BUILD_TARGET=x86_64-unknown-linux-musl` in its environment. This causes all build artifacts to land at `/app/target/x86_64-unknown-linux-musl/release/` (relative to workspace root `/app/`), NOT at the per-crate `target/` directory inside each crate. In a multi-crate workspace (like easytier's), `WORKDIR /app/easytier` followed by `cargo build` still puts binaries at `/app/target/...` not `/app/easytier/target/...`. **Docker COPY must use `/app/target/x86_64-unknown-linux-musl/release/<binary>` paths.** Verify with `find /app -name <binary> -type f` inside the builder container.

34. **`frontend/dist/` must exist before building `easytier-web --features embed`.** The `easytier-web` crate uses `#[derive(RustEmbed)]` with `#[folder = "frontend/dist/"]`. The derive macro is a proc-macro that runs at compile time and REQUIRES the directory to exist. If missing, the proc-macro raises "folder not found" — a COMPILE ERROR. This error appears in the build log but gets truncated in CI output, leaving only the CASCADING errors visible: `E0277: the trait bound 'Assets: RustEmbed' is not satisfied` plus `E0599`. These look like trait mismatch bugs but the real cause is the missing folder. **Fix:**
    ```yaml
    - name: 🏗️ Build web-embed
      run: |
        mkdir -p easytier-web/frontend/dist
        cargo build --release --package=easytier-web --features embed
        cp target/.../release/easytier-web target/.../release/easytier-web-embed
    ```
    An empty directory is sufficient — the Vue SPA frontend is compiled separately. The `axum-embed` crate that provides the `ServeEmbed` wrapper requires `rust-embed >= 8` (specified in `axum-embed/Cargo.toml`), so you CANNOT downgrade `rust-embed` to 6.x to fix this — the two crates would use different versions and the trait impl would still mismatch.
