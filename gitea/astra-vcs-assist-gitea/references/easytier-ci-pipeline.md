# EasyTier CI Pipeline Reference

## Purpose

CI pipeline for building EasyTier upstream releases into Gitea Releases with `magic-dns` and `jemalloc` features as statically-linked musl binaries.

## Four Binary Targets (all musl static, 3 build invocations)

| # | Binary | Package | Cargo features | How produced |
|:--|:-------|:--------|:---------------|:-------------|
| 1 | `easytier-core` | `easytier` | `--features "magic-dns,jemalloc"` | Single `cargo build -p easytier` |
| 2 | `easytier-cli` | `easytier` | (same invocation — `[[bin]]` within package) | Same `cargo build -p easytier` |
| 3 | `easytier-web` | `easytier-web` | default (no features) | `cargo build -p easytier-web` |
| 4 | `easytier-web-embed` | `easytier-web` | `--features embed` | `cargo build -p easytier-web --features embed` then `cp` to rename |

**`easytier-cli` is NOT a separate package.** It is defined as `[[bin]] name = "easytier-cli" path = "src/easytier-cli.rs"` inside the `easytier` package. One `cargo build --package=easytier` compiles both `easytier-core` and `easytier-cli`.

## Workflow: Upstream Tag → Gitea Release

### Trigger

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Upstream EasyTier tag (e.g. v2.6.4)"
        required: true
        type: string
```

No `push` trigger — mirrored repos should detect new tags via a separate cron job and dispatch this workflow.

### Fetching and Checking Out the Tag

```yaml
- name: Checkout
  uses: actions/checkout@v4
- name: Fetch upstream tag
  run: |
    git remote add upstream https://github.com/EasyTier/EasyTier.git 2>/dev/null || true
    git fetch upstream --tags 2>&1
    git checkout refs/tags/${{ inputs.version }} 2>/dev/null || \
      git checkout upstream/${{ inputs.version }} 2>/dev/null || {
      echo "ERROR: Tag ${{ inputs.version }} not found upstream"
      exit 1
    }
```

### Build Commands (in order)

```yaml
# 1. core + cli (includes magic-dns)
cargo build --release --package=easytier \
  --features "magic-dns,jemalloc" \
  --target x86_64-unknown-linux-musl

# 2. web (standalone)
cargo build --release --package=easytier-web \
  --target x86_64-unknown-linux-musl

# 3. web-embed (rename to avoid overwrite)
cargo build --release --package=easytier-web \
  --features embed \
  --target x86_64-unknown-linux-musl
cp target/x86_64-unknown-linux-musl/release/easytier-web \
  target/x86_64-unknown-linux-musl/release/easytier-web-embed
```

**Do NOT add a separate `--package=easytier-cli` line** — this causes `error: cannot specify features for packages outside of workspace`.

**Do NOT pass easytier features (`magic-dns,jemalloc`) to `easytier-web`** — each package has its own `[features]`. easytier-web only has `default = []` and `embed = ["dep:axum-embed"]`.

### Gitea Release — python3 script (not inline JSON)

`${{ github.token }}` lacks release creation scope **and** inline JSON/`printf` in YAML `run: |` 
can silently produce malformed JSON (HTTP 200, no release). Use a PAT + python3 script instead.

Place `scripts/ci-release.py` from this skill into the repo's `.gitea/ci-release.py`:

```yaml
- name: Create Gitea Release & Upload
  env:
    GITEA_PAT: b6cf278ea8bccf224b2c85e76e06a61fd12389a7
  run: |
    python3 .gitea/ci-release.py
```

**Tag naming convention:** `{VERSION}-magicdns` — distinct from upstream tags.

### ⚠️ Release JSON Failure Pattern (Runs #104-#107)

The inline JSON approach is **brittle and silently fails** — the API returns HTTP 200 but no release:

| Run | Approach | Failure |
|:----|:---------|:--------|
| #104 | `${{ github.token }}` | PAT scope missing |
| #105 | PAT + `printf` multi-line JSON | Shell escaping broke YAML |
| #106 | PAT + `printf` single-line | YAML `\n` from `\|` scalar → real newlines in JSON → HTTP 200, no release |
| **#107** | **PAT + `python3` script** | **✅ All 5 assets released** |

**The printf trap:** YAML `run: |` preserves literal newlines. `printf` format strings insert
REAL newlines instead of `\\n` — malformed JSON the API silently drops. `python3 json.dumps()`
is the only robust approach.

### CI Run Duration Guidance

Rust CI builds on the DS425Plus (J3455) take **~35 min** (see build time baselines below).
Each failed-then-retry cycle costs this time. Apply ALL fixes in one commit before pushing
a new tag — never one fix per attempt (lessons from Runs #104-#107).

### Cron: Auto-Detect New Upstream Tags

Run every 6h on HomeCentre01 via Hermes cron:

```bash
# 1. Fetch upstream tags
cd ~/Projects/easytier-src
git fetch origin --tags 2>&1

# 2. Get latest upstream tag and latest built tag
UPSTREAM=$(git tag --list 'v*' --sort=-version:refname | head -1)
GITEA_MAGICDNS=$(git -c credential.helper= ls-remote --tags gitea \
  | grep -o 'refs/tags/[^^]*' | sed 's|refs/tags/||' \
  | grep 'magicdns' | sed 's/-magicdns//' | sort -V | tail -1)

# 3. Compare and trigger
if [ "$UPSTREAM" != "$GITEA_MAGICDNS" ] && [ -n "$UPSTREAM" ]; then
  git -c credential.helper= push gitea "refs/tags/$UPSTREAM"
  curl -X POST \
    -H "Authorization: token b6cf278ea8bccf224b2c85e76e06a61fd12389a7" \
    -H "Content-Type: application/json" \
    -d "{\"ref\":\"main\",\"inputs\":{\"version\":\"$UPSTREAM\"}}" \
    "http://192.168.0.30:3000/api/v1/repos/alrcatraz/easytier/actions/workflows/build.yml/dispatches"
fi
```

## Key Configuration

### Runner

| Property | Value |
|:---------|:------|
| Host | DS425Plus (NAS, J3455, 4GB RAM) |
| Runner name | `ds425plus` |
| Engine | Docker (Synology ContainerManager) |
| Network | `gitea_default` |
| Image | `gitea/act_runner:latest` (v0.6.1) |
| Config | `/data/config.yaml` via `CONFIG_FILE` env var |
| Docker CLI path (SSH) | `/var/packages/ContainerManager/target/usr/bin/docker` |

### Labels

```yaml
runner:
  labels:
    - "rust:docker://rust:1.84-slim-bookworm"
```

The `rust` label image has cargo/rustc pre-installed but lacks `musl-tools`, `libclang-dev`, `curl`, and `nodejs`.

## Build Time Baselines (DS425Plus, Celeron J3455, 4GB RAM)

| Phase | Time | Notes |
|:------|:-----|:------|
| `apt-get install` (all deps) | ~30s | TUNA HTTP mirror |
| `rustup target add musl` | ~1-3 min | ~50MB download via proxy (225 KB/s) |
| `cargo build -p easytier` (first) | ~22 min | ~1800 crates, LTO 10-15min |
| `cargo build -p easytier-web` | ~5 min | Deps cached |
| `cargo build -p easytier-web embed` | ~5 min | Deps mostly cached |
| **Total** | **~35 min** | |

**LTO silence trap:** After the last `Compiling` line, the build goes silent for 10-20 min while rustc does LTO. NOT stuck — check via `/proc/*/cmdline` inside the container for `rustc --crate-name easytier_core ... -C lto`.

## Persistent Podman Volume for Rustup Cache

When building locally via podman (not CI), each container loses its rustup cache on exit. Avoid re-downloading the musl target every time:

```bash
# Create persistent volume
podman volume create rustup-cache

# One-time: download musl target into volume (slow first time)
podman run --rm --network host \
  -v rustup-cache:/usr/local/rustup \
  rust:latest rustup target add x86_64-unknown-linux-musl

# Subsequent builds: volume has cached target — instant
podman run --rm --network host \
  -v rustup-cache:/usr/local/rustup \
  -v /path/to/source:/app:Z -w /app \
  rust:latest sh -c '
    for i in 1 2 3 4 5; do
      rustup target add x86_64-unknown-linux-musl && break
      sleep 10
    done
    cargo build --release --package=easytier \
      --features "magic-dns,jemalloc" \
      --target x86_64-unknown-linux-musl
  '
```

The volume path `/usr/local/rustup` is the default rustup home in the `rust:latest` image. Verify with `rustup show home`.

## Known Failure Modes (Easytier-specific)

| Error | Root Cause | Fix |
|:------|:-----------|:----|
| `cannot specify features for packages outside of workspace` | `--package=easytier-cli` used but CLI is a `[[bin]]` within easytier package | Remove the redundant `--package=easytier-cli` line |
| `failed to run custom build command for prost-wkt-types` → `Could not find protoc` / `google/protobuf/duration.proto: File not found` | `protobuf-compiler` and/or `libprotobuf-dev` not installed — the latter supplies Google's standard `.proto` includes | Add BOTH `protobuf-compiler libprotobuf-dev` to `apt-get install` |
| `error decoding response body` during rustup | Transient HTTPS corruption through TPROXY proxy | Retry loop around `rustup target add` |
| `can't find crate for core` | `rust-toolchain.toml` switches channel after checkout, losing musl target | Re-run `. "$HOME/.cargo/env"` and `rustup target add` in build step |
| `exec: "node": not found` | `nodejs` installs as `/usr/bin/nodejs` not `/usr/bin/node` | `which node \|\| ln -sf /usr/bin/nodejs /usr/bin/node` |
| `|| true` on install swallows failures | apt-get exits non-zero but RC masked | Remove `|| true`; verify with `which` after install |
| `collect2: fatal error: cannot find 'ld'` (openSUSE host) | `ld -> alts` symlink broken in alternatives system | Install `mold`: `sudo zypper install mold` |
| `could not compile libc (build script)` → linker error | Missing linker on host | Set up `~/.cargo/config.toml` with `rustflags = ["-C", "link-arg=-fuse-ld=mold"]` |
