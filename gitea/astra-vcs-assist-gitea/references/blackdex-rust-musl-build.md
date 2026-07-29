# BlackDex/rust-musl — MUSL Static Build Reference

## Purpose

Pre-built Docker image for compiling fully static Rust binaries against MUSL libc. Based on Ubuntu 26.04 + crosstool-ng toolchain + pre-compiled C libraries (OpenSSL, ZLib, cURL, SQLite, PostgreSQL, MariaDB).

## Why Not rust:latest + --target musl

| Failure | rust:latest approach | BlackDex/rust-musl |
|:--------|:---------------------|:-------------------|
| `rustup target add` succeeds but cargo can't find target | Known issue with Rust 1.96+/1.97+ on `rust:latest` — sysroot mismatch | Default target is already MUSL — no target add needed |
| OOM during OpenSSL source compilation | `openssl-sys` build script compiles OpenSSL from source (~1GB+ RAM) | Pre-compiled OpenSSL v3.5.7 as static library — zero compilation |
| `lld`/`mold` linker not found | Rust 1.97+ defaults to LLD/Mold, failing on minimal images | Ubuntu 26.04 has all linkers pre-installed |
| Alpine proc-macro failure | `rust:alpine` fails with `cannot produce proc-macro for musl target` | Uses GLIBC host → proc-macros work normally, targets MUSL |

## Session Trail: Approaches That Failed

This documents the actual session history that led to the BlackDex/rust-musl solution.

### ❌ Approach 1: rust:alpine (Rust 1.97 via rustup)

```
image: rust:alpine
error: cannot produce proc-macro for 'async-recursion v1.1.1'
       as the target 'x86_64-unknown-linux-musl' does not
       support these crate types
```

Proc-macro crates compile to shared libraries; Alpine's MUSL-only host can't produce them. Known Rust 1.97 issue.

### ❌ Approach 2: debian:12-slim + rustup (GLIBC 2.36)

```
image: debian:12-slim + curl sh.rustup.rs
error: collect2: fatal error: cannot find 'ld'
```

`debian:12-slim` has no `build-essential` (no gcc, no ld). Rust 1.97's default linker flags (`-fuse-ld=lld`, `-fuse-ld=mold`) fail because neither is installed. Fix would be `apt-get install build-essential lld` — but this is GLIBC-targeted, not MUSL.

### ❌ Approach 3: alpine:3.21 + apk add rust (native Alpine rust)

```
image: alpine:3.21 + apk add rust cargo musl-dev openssl-dev build-base
exit code: 137 (SIGKILL / OOM)
```

Alpine's Rust packages are correctly compiled for MUSL and handle proc-macros. But `apk add rust cargo` installs ~300MB of toolchain, and compiling easytier-web (with its ~1800 crate dependency tree, plus OpenSSL FFI compilation) exceeds the container's default memory limit. OOM-killed.

### ❌ Approach 4: rust:1.83-bookworm + --target musl

```
image: rust:1.83-bookworm
rustup target add x86_64-unknown-linux-musl → success
cargo build --release --target x86_64-unknown-linux-musl
→ downloads Rust 1.95 toolchain (from rust-toolchain.toml)
→ error: component download failed for rust-std
```

### ✅ Approach 5: BlackDex/rust-musl + protoc (winning approach)

```bash
podman run --name easytier-build-musl --rm \
  -v "$(pwd)":/home/rust/src \
  -e RUSTUP_TOOLCHAIN=stable \
  ghcr.io/blackdex/rust-musl:x86_64-musl-stable \
  bash -c "apt-get update -qq && apt-get install -y -qq protobuf-compiler libprotobuf-dev && cargo build --release --features=embed"
```

Reasons it works:
1. MUSL target is the default — no `rustup target add` needed
2. `RUSTUP_TOOLCHAIN=stable` overrides `rust-toolchain.toml` — no toolchain download
3. Pre-compiled OpenSSL avoids OOM
4. Ubuntu 26.04 base has all linkers pre-installed
5. GLIBC host handles proc-macros correctly
6. `protobuf-compiler` + `libprotobuf-dev` provides `protoc` AND standard `.proto` includes

### ⚠️ Approach 5a: Missing libprotobuf-dev

First attempt with only `protobuf-compiler` — protoc binary was present but `prost-wkt-types` build script failed:

```
thread 'main' panicked at .../prost-wkt-types-0.6.1/build.rs:47:10:
  called `Result::unwrap()` on an `Err` value:
  Custom { kind: Other, error: "protoc failed:
    google/protobuf/duration.proto: File not found.
    google/protobuf/timestamp.proto: File not found.
    pbtime.proto:3:1: Import \"google/protobuf/duration.proto\"
      was not found or had errors." }
```

The `libprotobuf-dev` package provides `/usr/include/google/protobuf/*.proto` files. Without them, `protoc` can't resolve standard imports even though the compiler binary itself is present.

## Environment Variables

| Variable | Value | Purpose |
|:---------|:------|:--------|
| `RUSTUP_TOOLCHAIN` | `stable` | Override `rust-toolchain.toml` — prevents toolchain download |
| `OPENSSL_NO_VENDOR` | `0` | Use pre-compiled OpenSSL (default, set automatically) |
| `PQ_LIB_DIR` | `/usr/local/musl/pq17/lib` | PostgreSQL lib path override (v17 default) |

## Available Tags

| Tag | Rust version |
|:----|:-------------|
| `x86_64-musl-stable` | Latest stable |
| `x86_64-musl-stable-1.96.0` | Pinned to 1.96 |
| `x86_64-musl-nightly` | Latest nightly |
| `x86_64-musl-nightly-2026-07-10` | Pinned nightly date |

Other architectures: `aarch64-musl-*`, `armv7-musleabihf-*`, `arm-musleabi-*`

## Registries

- GitHub Container Registry: `ghcr.io/blackdex/rust-musl`
- Docker Hub: `blackdex/rust-musl`
- Quay.io: `quay.io/blackdex/rust-musl`

## Tested Workflow (Podman on SUSETLearn00)

**Important:** Projects using `prost` / `prost-wkt-types` need both `protobuf-compiler` (the `protoc` binary) AND `libprotobuf-dev` (Google standard `.proto` includes). Without `libprotobuf-dev`, protoc fails with `google/protobuf/duration.proto: File not found`.

```bash
podman run --name easytier-build-musl --rm \
  -v /home/alrcatraz/tmp/easytier-src:/home/rust/src:Z \
  -e RUSTUP_TOOLCHAIN=stable \
  ghcr.io/blackdex/rust-musl:x86_64-musl-stable \
  bash -c "apt-get update -qq && apt-get install -y -qq protobuf-compiler libprotobuf-dev && cargo build --release --features=embed"
```

Build output: 28MB static-pie linked binary, compiled in ~5 min on 32-core i9-13980HX.
