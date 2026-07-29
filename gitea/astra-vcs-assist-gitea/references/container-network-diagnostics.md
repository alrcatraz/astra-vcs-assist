# Container Network Diagnostics

Methodology for diagnosing why a CI job container cannot reach external network resources.

## Layer-by-Layer Testing

When a container fails to download packages or toolchain components, do NOT assume the cause. Test each layer systematically:

### 1. Host-level connectivity

First confirm the Docker HOST itself can reach the target:

```bash
# Basic connectivity
curl -sI https://deb.debian.org
curl -sI http://deb.debian.org

# Compare with a Chinese site (control test)
curl -sI https://baidu.com
```

If the host can reach HTTPS but the container cannot → the issue is Docker networking.
If the host also cannot reach HTTPS → the issue is upstream (router, GFW, proxy).

### 2. Container-level connectivity (Alpine test)

Use `alpine:3.20` as the test image — it has `wget`, `nc`, and `nslookup` built-in:

```bash
# DNS
docker run --rm --network gitea_default alpine:3.20 \
  nslookup deb.debian.org

# TCP port check
docker run --rm --network gitea_default alpine:3.20 \
  sh -c 'nc -zv deb.debian.org 443'

# Full HTTP/HTTPS test
docker run --rm --network gitea_default alpine:3.20 \
  sh -c 'wget -q -O /dev/null https://deb.debian.org && echo HTTPS_OK'
```

Alpine works reliably because it uses musl + a clean network stack. If Alpine works but your build image doesn't → the issue is specific to your build image, not the network.

### 3. Compare network modes

Test the same thing across different Docker network modes:

```bash
for mode in "" "--network gitea_default" "--network host"; do
  echo "=== Mode: ${mode:-default bridge} ==="
  docker run --rm $mode alpine:3.20 sh -c 'timeout 10 wget -q -O /dev/null https://deb.debian.org && echo OK || echo FAIL'
done
```

- **Default bridge** → container uses Docker's default NAT. May have limited DNS.
- **`gitea_default`** (user-defined bridge) → shares network with Gitea. Docker DNS at 127.0.0.11.
- **`host`** → shares host's network stack completely. If this fails too, the host itself can't reach the target.

### 4. Inside the specific build image

Test with the actual image used in CI (e.g. `rust:1.84-slim-bookworm`). These slim images lack networking tools — install them first:

```bash
docker run --rm --network gitea_default rust:1.84-slim-bookworm bash -c '
  apt-get update -qq && apt-get install -y -qq curl ca-certificates
  curl -sI https://deb.debian.org
'
```

## Common Findings

| Finding | Meaning | Action |
|:--------|:--------|:-------|
| Host HTTPS ✅, Alpine ✅, Rust image ❌ | Issue is specific to the build image (certs, DNS, or proxy env) | Check ca-certificates, resolv.conf, proxy env vars |
| Host HTTPS ✅, Alpine ✅, all modes ✅ | Network is fine — failure is from something else | Check package names, apt sources, disk space |
| Host HTTPS ✅, Alpine ❌ on `gitea_default`, ✅ on `host` | Docker bridge network has limited egress | Use `network_mode: host` for CI containers |
| Host HTTPS ❌ | Router/proxy/gateway blocks outbound 443 | Use HTTP mirrors (TUNA), or add bypass rule |
| Host HTTPS ✅, but `docker build` hangs | Docker build's network stack differs from `docker run` | Use `docker commit` from a running container instead of `docker build` |

## Docker Build vs Docker Run

`docker build --network host` does NOT work the same as `docker run --network host` in all Docker versions. If `docker build` hangs but `docker run` works, the builder's network mode may be ignored. Workaround: use a running container + `docker commit`:

```bash
# Start a container
docker run -d --name builder-tmp rust:1.84-slim-bookworm sleep 3600

# Install packages inside
docker exec builder-tmp bash -c '
  apt-get update -qq && apt-get install -y -qq protobuf-compiler make
'

# Commit to image
docker commit builder-tmp my-custom-builder:latest

# Clean up
docker rm -f builder-tmp
```
