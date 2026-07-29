# Podman Rust Compilation on openSUSE

## When to Use

Compiling Rust binaries in podman containers on openSUSE Tumbleweed (or other non-Docker environments) when:
- Docker is not available (Podman as drop-in) or you want daemonless containers
- You need container isolation without root privileges or a Docker daemon
- Cross-compiling musl targets on a fast laptop (32 cores) that has no Docker

## Setup

```bash
# Install podman + docker compat
sudo zypper install podman podman-docker

# Verify
podman info | grep -E "hostname|kernel|cgroupVersion"
# Expected: cgroupVersion: v2 (openSUSE default)
```

## Image Choice: Debian (NOT Alpine)

**Use `rust:latest` (Debian-based), NOT `rust:alpine`.**

| Image | Works for easytier? | Reason |
|:------|:-------------------|:-------|
| `rust:latest` (Debian) | ✅ | Supports proc-macros for musl target via `--target` |
| `rust:alpine` | ❌ | `error: cannot produce proc-macro for ... as the target 'x86_64-unknown-linux-musl' does not support these crate types` |

Alpine's musl libc conflicts with proc-macro ABI requirements. Debian's glibc toolchain handles proc-macro cross-compilation correctly.

## TUNA Mirrors for China Network

When building behind GFW, add TUNA mirrors for both apt and crates.io. **Must mount individual config files — never mount a directory over `/usr/local/cargo`** (it overwrites rustup and cargo binaries from the container image).

```bash
# Create standalone TUNA cargo config — use sparse protocol
# (git-based index clone takes 2+ hours at ~75KB/s behind GFW)
cat > /tmp/cargo-tuna-config.toml << 'CARGOEOF'
[source.crates-io]
replace-with = "tuna"
[source.tuna]
registry = "sparse+https://mirrors.tuna.tsinghua.edu.cn/crates.io-index/"
[http]
timeout = 60
CARGOEOF

# Mount config.toml as individual file, NOT directory mount
podman run --rm --network host \
  -v /tmp/cargo-tuna-config.toml:/usr/local/cargo/config.toml:Z \
  -v /path/to/repo:/app:Z -w /app \
  rust:latest sh -c '
    # TUNA HTTP mirror for apt
    sed -i "s|http://deb.debian.org|http://mirrors.tuna.tsinghua.edu.cn|g" \
      /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
    apt-get update -qq
    apt-get install -y -qq musl-tools protobuf-compiler \
      libclang-dev clang make curl pkg-config libssl-dev

    # With CARGO_NET_RETRY for transient GFW dropouts
    CARGO_NET_RETRY=5 cargo build ...
  '
```

**Sparse vs git protocol — critical difference:**

| Protocol | First resolution behind GFW | cargo version required |
|:---------|:---------------------------|:----------------------|
| `sparse+https://...` | **Seconds** — fetches only needed index entries | ≥ 1.68 |
| `https://...git/...` | **2–4 hours** — full ~700MB git clone at ~75KB/s | any |

When cargo hangs on `Updating \`tuna\` index` for more than 5 minutes, it's using the git protocol — switch to `sparse+https://`.

## Build Commands

### All four musl binaries (one pass, sequential, with TUNA mirrors + retry + sparse index)

```bash
# Create standalone TUNA cargo config (sparse protocol)
cat > /tmp/cargo-tuna-config.toml << 'CARGOEOF'
[source.crates-io]
replace-with = "tuna"
[source.tuna]
registry = "sparse+https://mirrors.tuna.tsinghua.edu.cn/crates.io-index/"
[http]
timeout = 60
CARGOEOF

podman run --rm --network host \
  -v /tmp/cargo-tuna-config.toml:/usr/local/cargo/config.toml:Z \
  -v /path/to/repo:/app:Z -w /app \
  rust:latest sh -c '
    set -e

    # TUNA HTTP mirror for apt
    sed -i "s|http://deb.debian.org|http://mirrors.tuna.tsinghua.edu.cn|g" \
      /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

    echo "=== Step 1: Install deps ==="
    apt-get update -qq
    apt-get install -y -qq musl-tools protobuf-compiler \
      libclang-dev clang make curl pkg-config libssl-dev 2>&1 | tail -3

    echo "=== Step 2: musl target (with retry) ==="
    for i in 1 2 3 4 5; do
      rustup target add x86_64-unknown-linux-musl && break
      echo "Retry $i/5..."; sleep 10
    done

    echo "=== Step 3: core+cli (MagicDNS) ==="
    CARGO_NET_RETRY=5 cargo build --release --package easytier \
      --features "magic-dns,jemalloc" \
      --target x86_64-unknown-linux-musl

    echo "=== Step 4: web (standalone) ==="
    CARGO_NET_RETRY=5 cargo build --release --package easytier-web \
      --target x86_64-unknown-linux-musl

    echo "=== Step 5: web-embed === (Note: may fail if Cargo.lock has incompatible rust-embed version)"
    CARGO_NET_RETRY=5 cargo build --release --package easytier-web \
      --features embed --target x86_64-unknown-linux-musl
    cp target/x86_64-unknown-linux-musl/release/easytier-web \
       target/x86_64-unknown-linux-musl/release/easytier-web-embed

    echo "=== Done building ==="
    ls -lh target/x86_64-unknown-linux-musl/release/easytier-*
  '
```

**`--network host` is CRITICAL behind GFW.** Without it, the container bridge network may be extremely slow for apt-get and crate downloads.

### Known Cargo.lock issue: rust-embed version breakage

When building `easytier-web --features embed`, the `rust-embed` crate had breaking changes in minor versions (8.5.0 → 8.11.0 renamed `Embed` trait to `RustEmbed`). If Cargo.lock resolves to a newer minor, the build fails with:

```
error[E0277]: the trait bound `web::Assets: Embed` is not satisfied
```

**Fix:** Pin `rust-embed` in `easytier-web/Cargo.toml` with the `=` prefix:

```toml
rust-embed = { version = "=8.5.0", features = ["debug-embed", "include-exclude"] }
```

Then remove the old entries from Cargo.lock and regenerate:

```bash
# Remove old entries (but CAREFUL — sed can leave empty [[package]] headers)
# Use python for safe cleanup:
python3 -c "
import re
with open('Cargo.lock') as f:
    c = f.read()
c = re.sub(r'\[\[package\]\]\n\n?\[\[package\]\]', '[[package]]', c)
with open('Cargo.lock', 'w') as f:
    f.write(c)
"
```

## Binary Output

After the container exits, binaries are in `target/x86_64-unknown-linux-musl/release/`:

| Binary | Path | Notes |
|:-------|:-----|:------|
| `easytier-core` | `target/.../release/easytier-core` | From `--package easytier`, `[[bin]]` entry |
| `easytier-cli` | `target/.../release/easytier-cli` | Same `cargo build`, different `[[bin]]` |
| `easytier-web` | `target/.../release/easytier-web` | Default features (no embed) |
| `easytier-web` (embed) | `target/.../release/easytier-web` | Same filename, different binary. Rename on copy: `easytier-web-x86_64-musl-embed` |

## Output Organization

```bash
mkdir -p ~/easytier-release
cp target/x86_64-unknown-linux-musl/release/easytier-core \
  ~/easytier-release/easytier-core-x86_64-musl
cp target/x86_64-unknown-linux-musl/release/easytier-cli \
  ~/easytier-release/easytier-cli-x86_64-musl
cp target/x86_64-unknown-linux-musl/release/easytier-web \
  ~/easytier-release/easytier-web-x86_64-musl
cp target/x86_64-unknown-linux-musl/release/easytier-web \
  ~/easytier-release/easytier-web-x86_64-musl-embed
cd ~/easytier-release && sha256sum * > CHECKSUMS.txt && ls -lh
```

## Caching

Podman containers run in isolation — each `podman run` starts fresh with no `~/.cargo` cache. To share cache between runs:

```bash
# Create a persistent cargo cache volume
podman volume create cargo-cache

# Use in subsequent runs
podman run --rm --network host \
  -v cargo-cache:/root/.cargo:Z \
  -v /path/to/repo:/app:Z -w /app \
  rust:latest ...
```

Without shared cache, the first compilation downloads all dependencies (~1800 crates, ~200MB).

## Key Dependencies (missing from minimal images)

| Package | Required by | Missing in |
|:--------|:------------|:-----------|
| `libclang-dev clang` | `bindgen` (FFI crate: kcp-sys, dbus, jemalloc) | `rust:latest`, all slim images |
| `musl-tools` | `--target x86_64-unknown-linux-musl` linking | `rust:latest` |
| `protobuf-compiler` | `prost-build` in Cargo build script | `rust:latest` |
| `curl` | Gitea API upload step | `rust:*-slim-bookworm` |

## GLIBC Targeting with Specific Debian Releases

When you need to match a target system's GLIBC version (e.g., deploying to a Debian 12 server with GLIBC 2.36), use the matching Debian release as the build container base instead of `rust:latest` (Debian 13 / GLIBC 2.41).

### When to Use

- **MUSL doesn't work** — some Rust features (proc-macros for specific targets, certain FFI crates) may fail under MUSL cross-compilation
- **Target requires specific GLIBC** — e.g., deploying to an embedded system or NAS running Debian 12 (GLIBC 2.36), where `rust:latest`'s GLIBC 2.41 would cause `version GLIBC_2.38 not found` errors at runtime
- **Intermediate step before MUSL** — validate the build works before investing in MUSL toolchain setup

### Approach

Instead of `rust:latest` (Debian 13 / GLIBC 2.41), use the Debian release that matches your target:

```bash
# debian:12-slim → GLIBC 2.36 (matches Debian 12 / Ubuntu 22.04)
# debian:11-slim → GLIBC 2.31 (matches Debian 11 / Ubuntu 20.04)
```

### Critical: Rust 1.97+ LLD/Mold Linker Requirement

Rust 1.97+ defaults to LLD or Mold as the linker for faster builds. Minimal Debian images (`debian:12-slim`) do NOT include these — Rust's linker flags `-fuse-ld=lld` then `-fuse-ld=mold` both fail with:

```
collect2: fatal error: cannot find 'ld'
```

**Fix:** Install `lld` in the build container:

```bash
apt-get install -y -qq lld
```

Without it, every crate's build script or linking step fails with `compilation terminated`.

### Full Build Script (Debian 12)

```bash
#!/bin/bash
set -euo pipefail

echo "=== Install deps ==="
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  build-essential \
  lld \
  pkg-config \
  libssl-dev \
  curl \
  ca-certificates

echo "=== Install Rust ==="
export RUSTUP_HOME=/opt/rust
export CARGO_HOME=/opt/rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
  | sh -s -- -y --no-modify-path --default-toolchain stable
. /opt/rust/env
rustc --version

echo "=== Build ==="
cd /easytier-src
cargo build --release --package=easytier-web --features=embed
```

### GLIBC Version Comparison

| Base Image | GLIBC Version | Compatible Targets |
|:-----------|:--------------|:-------------------|
| `rust:latest` (Debian 13 trixie) | 2.41 | Debian 13+, Ubuntu 24.10+, latest distros |
| `debian:12-slim` + rustup | 2.36 | Debian 12, Ubuntu 22.04–24.04 |
| `debian:11-slim` + rustup | 2.31 | Debian 11, Ubuntu 20.04 |
| `rust:alpine` | MUSL (none) | Any Linux (fully static) |

### Trade-offs vs MUSL

| Aspect | GLIBC-targeted (debian:12 + rustup) | MUSL (rust:latest + --target musl) |
|:-------|:------------------------------------|:-----------------------------------|
| Binary size | ~28MB (dynamically linked) | ~60MB (statically linked, incl. libc) |
| Portability | Tied to GLIBC version | Any Linux kernel |
| Build speed | Faster (native glibc) | Slower (LTO + full static linking) |
| Container image size | ~130MB (debian:12-slim) | ~1.2GB (rust:latest) |
| Setup complexity | Install rustup + deps | Pre-installed |
| Dep compatibility | Full (all crates work) | Some proc-macro + FFI issues |

## Alpine-native MUSL Builds (Alternative to rust:latest)

Instead of using `rust:latest` (Debian-based, ~1.2GB) with `--target x86_64-unknown-linux-musl`, build MUSL static binaries directly on Alpine using its native Rust packages. This avoids the `rustup target add` dance entirely — Alpine's `rust` and `cargo` packages are themselves compiled against MUSL, so `cargo build --release` natively produces fully static binaries without any cross-compilation target.

### Architecture

```
┌──────────────────────────────────────────────────┐
│  alpine:3.21 (~7MB base)                         │
│  ┌─────────────────────────────────────────────┐ │
│  │  apk add rust cargo musl-dev openssl-dev    │ │
│  │  build-base pkgconfig                       │ │
│  │  → ~300MB total image (~1/4 of rust:latest) │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  cargo build --release ...                   │ │
│  │  → MUSL static binary (no .so dependencies)  │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Key Differences from Debian-based Approach

| Aspect | `rust:latest` (Debian) | `alpine:3.21` + apk |
|:-------|:-----------------------|:--------------------|
| Image size | ~1.2GB | ~300MB |
| Rust version | Latest stable (via rustup) | Alpine's packaged version (may be 1–2 minor versions behind) |
| MUSL target | `rustup target add` needed | Native — default target is already MUSL |
| Proc-macros | Works (glibc host) | Works (Alpine apk rust, NOT rust:alpine which fails) |
| Linker | May need `lld`/`mold` for Rust 1.97+ | MUSL's native linker works |
| C cache | Podman volume needed for persist | Podman volume still needed |

### Dockerfile

```dockerfile
FROM alpine:3.21

# Install Rust toolchain and build deps
RUN apk add --no-cache \
    rust \
    cargo \
    musl-dev \
    openssl-dev \
    pkgconfig \
    build-base

COPY . /src
WORKDIR /src

# Build MUSL static binary
RUN cargo build --release --package=easytier-web --features=embed

# Verify fully static
RUN ldd target/release/easytier-web 2>&1 || echo "(fully static - no dynamic deps)"
```

### Podman One-shot Build

```bash
podman run --rm \
  -v /path/to/source:/src:Z \
  -w /src \
  alpine:3.21 sh -c '
    apk add --no-cache rust cargo musl-dev openssl-dev pkgconfig build-base
    cargo build --release --package=easytier-web --features=embed
    ls -lh target/release/easytier-web
    file target/release/easytier-web
  '
```

### Cargo Cache Volume (for repeated builds)

```bash
podman volume create cargo-cache-alpine

podman run --rm \
  -v cargo-cache-alpine:/root/.cargo:Z \
  -v /path/to/source:/src:Z \
  -w /src \
  alpine:3.21 sh -c '
    apk add --no-cache rust cargo musl-dev openssl-dev pkgconfig build-base
    cargo build --release --package=easytier-web --features=embed
  '
```

### Caveats

1. **⚠️ OOM risk for large projects (important):** `apk add rust cargo` installs ~300MB of toolchain. When building a large workspace like `easytier-web` (~1800 crates, including OpenSSL FFI which compiles from source), total memory usage can exceed podman's container limit, causing exit code 137 (SIGKILL). **Fix:** Use `--memory=4g` with podman, or switch to `BlackDex/rust-musl` which pre-compiles OpenSSL as a static library (see `references/blackdex-rust-musl-build.md` in the `gitea-actions-ci-cd` skill).

2. **Rust version lag:** Alpine's `rust` package is usually 1–2 minor versions behind the latest stable. On 2026-07-10, Alpine 3.21 had Rust ~1.83 while latest was 1.97. For most projects this is fine — the Rust compiler is backward-compatible. If you need a specific nightly or very recent stable, use `rust:latest` instead.

3. **Crate compatibility:** Not all crates compile cleanly on MUSL. Common issues:
   - FFI crates that link against glibc-specific symbols
   - Crates using `libc::` APIs only available in glibc
   - Some `bindgen`-based crates assuming glibc headers
   - Most pure-Rust crates work fine (the vast majority)

3. **Proc-macro on rustup-installed Alpine Rust:** The `rust:alpine` Docker image (which uses rustup) fails on proc-macros. But Alpine's `apk add rust cargo` packages work correctly — they are compiled as MUSL-native and handle proc-macros properly. This is a key distinction.

4. **Bindgen + clang:** If the project uses `bindgen` (e.g., for `kcp-sys`, `libdbus-sys`), Alpine needs `clang-dev` and `clang-static` in addition to `build-base`:
   ```dockerfile
   RUN apk add --no-cache clang-dev clang-static
   ```

### When to Choose Alpine vs Debian

| Scenario | Choose |
|:---------|:-------|
| Need latest Rust (nightly/beta) | `rust:latest` (Debian) |
| Small container image is priority | Alpine `apk add rust cargo` |
| `rustup target add` fails in CI | Alpine native MUSL |
| Crate has glibc-specific FFI | `rust:latest` + `--target musl` |
| Building for scratch/Alpine deployment | Alpine native MUSL |
| First-time MUSL setup | Alpine (simpler, no target add) |

## DNS Consideration (Tailscale interference)

When the podman host runs Tailscale with MagicDNS (100.100.100.100), the container inherits the host's `/etc/resolv.conf`. Tailscale's DNS may fail to resolve `static.rust-lang.org` and other CDN endpoints, causing `dns error: Temporary failure in name resolution` in `rustup` and `cargo`.

To diagnose:
```bash
# Inside the container
host static.rust-lang.org 114.114.114.114  # Should resolve (Chinese DNS)
host static.rust-lang.org 8.8.8.8           # Should resolve (global DNS)
host static.rust-lang.org 100.100.100.100   # May FAIL (Tailscale DNS)
```

**Fix:** If Tailscale DNS is the problem, add `--dns 114.114.114.114` to the podman run command, or disable MagicDNS on the host with `tailscale set --accept-dns=false` (affects tailscale resolution too).

## SSH Access via SD-WAN

SUSETLearn00 has multiple network interfaces:
- **LAN:** `192.168.0.20` (unreliable — may be down)
- **EasyTier:** `10.20.60.11` (preferred for reliability)
- **Tailscale:** `100.64.60.11` (fallback)

**Always use overlay addresses for SSH** — LAN IPs may fail when the ethernet cable is disconnected or the switch port is down:

```bash
# ✅ Preferred: via EasyTier (most stable)
ssh alrcatraz@10.20.60.11 -p 2222

# ✅ Fallback: via Tailscale
ssh alrcatraz@100.64.60.11 -p 2222

# ❌ Unreliable: LAN IP
ssh alrcatraz@192.168.0.20 -p 2222
```
