# Rename audit (concrete worked example) (Concrete Example)

Seeded from [<UpstreamName>](https://github.com/diegosouzapw/<UpstreamName>) v3.8.50
(MIT) into independent project `<our-project>`. Full audit results.

## Tier 1 — Renamed (user-visible)

| Source | Target | Files |
|--------|--------|-------|
| `<UPSTREAM>_BUILD_MEMORY_MB` | `<OURPROJECT>_BUILD_MEMORY_MB` | Dockerfile |
| `<UPSTREAM>_MEMORY_MB` | `<OURPROJECT>_MEMORY_MB` | Dockerfile |
| `<UPSTREAM>_USE_TURBOPACK` | `<OURPROJECT>_USE_TURBOPACK` | Dockerfile, .env.example |
| `<UPSTREAM>_BASE_PATH` | `<OURPROJECT>_BASE_PATH` | Dockerfile, next.config.mjs |
| `<UPSTREAM>_MITM_STUB` | `<OURPROJECT>_MITM_STUB` | Dockerfile |
| `<UPSTREAM>_MIGRATIONS_DIR` | `<OURPROJECT>_MIGRATIONS_DIR` | Dockerfile |
| `<UPSTREAM>_BUILD_PROFILE` | `<OURPROJECT>_BUILD_PROFILE` | next.config.mjs |
| `<UPSTREAM>_SERVER_ACTIONS_BODY_LIMIT` | `<OURPROJECT>_SERVER_ACTIONS_BODY_LIMIT` | next.config.mjs |
| `<UPSTREAM>_DATA_DIR` | `<OURPROJECT>_DATA_DIR` | .env.example |
| `<UPSTREAM>_INSTANCE_ID` | `<OURPROJECT>_INSTANCE_ID` | .env.example |
| `<UPSTREAM>_PEER_URLS` | `<OURPROJECT>_PEER_URLS` | .env.example |
| `<UPSTREAM>_PORT` | `<OURPROJECT>_PORT` | .env.example |
| `<UPSTREAM>_CLI_SALT` | `<OURPROJECT>_CLI_SALT` | .env.example |
| `<UPSTREAM>_WS_BRIDGE_SECRET` | `<OURPROJECT>_WS_BRIDGE_SECRET` | .env.example |
| OCI labels (`<upstream>` → `<our-project>`) | — | Dockerfile |
| `bin/<upstream>.mjs` | `bin/<our-project>.mjs` | — |
| `.env.example` docs referencing <UpstreamName> | Updated | .env.example |

## Tier 2 — To rename (internal aliases)

| Source | Target | Files |
|--------|--------|-------|
| `@<upstream>/open-sse` | `@<our-project>/open-sse` | tsconfig.json, vitest configs, next.config.mjs |
| Workspace name | Rename | package.json |

## Tier 3 — Untouched (source internals)

100+ source files under `src/` containing `<upstream>` in:
- Type names and interfaces
- Enum values
- Function names (`<upstream>Fetch`, `resolve<UpstreamName>BaseUrl`)
- Comments and documentation blocks

Kept as evidence of provenance per open-source conventions.

---

## Build OOM Resolution

The <UpstreamName> codebase (~10,500 files) exceeds V8's default ~2 GB heap
when building with Turbopack + Carbon + Tailwind.

**Fix:** `NODE_OPTIONS=--max-old-space-size=4096`

| Machine | RAM | Result |
|---------|-----|--------|
| <host-a> (9 GB free) | Exit 137 (OOM) | ❌ |
| <host-b> (19 GB free, 32 cores) | Build in ~5 min | ✅ |

This is **not a hack** — it's proper configuration for the build
environment. The multi-stage Dockerfile already sets this via
`<UPSTREAM>_BUILD_MEMORY_MB=4096` (→ `<OURPROJECT>_BUILD_MEMORY_MB`).

---

## Verification with CodeGraph

Use `codegraph` CLI to audit rename completeness:

```bash
# Check full scope of <UPSTREAM>_ env vars
grep -rn '<UPSTREAM>_' . --include='*' | grep -v 'node_modules' | grep -v '.codegraph' | grep -v '.build'

# Verify Tier 1 only (config/build files, not docs/tests)
grep -rn '<UPSTREAM>_' . | grep -v 'node_modules' | grep -v 'docs/' | grep -v 'tests/' | grep -v '.git/'

# Initialize CodeGraph index for deep symbol search
cd project && codegraph init && codegraph query "<upstream>"
```

**Rationale:** Users never see these. Renaming risks bugs in core LLM
routing logic. Rename naturally during page/component rewrites (Phase 2+).

## Key Metrics

- 10,522 files in source tree
- ~40 env vars with `<UPSTREAM>_` prefix (Tier 1)
- 3 config files for `@<upstream>/open-sse` alias (Tier 2)
- 100+ source files with internal references (Tier 3)
