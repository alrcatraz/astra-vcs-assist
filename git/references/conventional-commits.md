# Conventional Commits Reference

> Companion reference for `astra-vcs-assist-git-dev` and
> `astra-vcs-assist-git-release` sub-skills. Full specification
> at [conventionalcommits.org](https://www.conventionalcommits.org/).

## Specification

```
<type>(<scope>): <description>          ← header (50 chars max)
                                        ← blank line
<body>                                  ← why, not just what (72 char wrap)
                                        ← blank line
<footer>                                ← breaking changes, issue refs
```

### Header

The header is mandatory. Format:

```
type(scope): description
│      │       │
│      │       └── Imperative, lowercase, no full stop
│      └── Optional context (module, area)
└── Required, lowercase
```

**Type values:**

| Type | Meaning | Release bump | Changelog section |
|:-----|:--------|:-------------|:------------------|
| `feat` | New feature | MINOR | Added |
| `fix` | Bug fix | PATCH | Fixed |
| `refactor` | Code restructuring | — | Changed |
| `docs` | Documentation | — | Documentation |
| `test` | Test addition/change | — | Tests |
| `chore` | Maintenance (deps, tooling) | — | Miscellaneous |
| `ci` | CI/CD configuration | — | CI/CD |
| `perf` | Performance improvement | PATCH | Performance |
| `style` | Formatting (no logic change) | — | Style |
| `wip` | Work in progress (temporary) | — | — (squash before merge) |

**Scope** provides context:

```
feat(auth): add user login endpoint
fix(parser): handle empty input
refactor(db): extract connection pool
docs(api): add endpoint reference
```

**Description rules:**
- Imperative mood ("add" not "added" or "adds")
- Lowercase (unless proper noun)
- No full stop at the end
- 50 character maximum

### Body

The body is optional but **strongly recommended** for non-trivial changes.
Use it to answer **why** the change was made.

```text
fix(auth): handle null token in middleware

Middleware crashed on missing Authorization header because the token
decoder returned None instead of raising an exception. Added early
return guard before the decoder call.
```

Body rules:
- Wrap at 72 characters
- Separate from header by one blank line
- Explain motivation, not implementation ("why" not "what")

### Footer

Optional. Used for:

**Breaking changes:**

```
feat(api): change pagination response format

BREAKING CHANGE: The `total` field has been renamed to `totalCount`.
All API clients must update their response parsers.
```

BREAKING CHANGE in a commit message bumps the MAJOR version regardless
of the `type` prefix. The `!` notation is also accepted:

```
feat(api)!: change pagination response format
```

**Issue references:**

```
fix(auth): handle null token in middleware

Closes #42
```

## Common Patterns

### Single atomic change

```bash
git commit -m "feat: add user login endpoint" \
           -m "POST /api/auth/login validates credentials and returns JWT."
```

### Multi-paragraph body

```bash
git commit -m "refactor: extract database connection pool" \
           -m "Creating a new connection per request was causing 400ms
latency on high-traffic endpoints. Pool reuses up to 10 connections.

This also makes connection monitoring easier—the pool exposes
active/idle/total counts that the health check can report." \
           -m "Closes #38"
```

### Breaking change with explanation

```bash
git commit -m "feat: redesign authentication flow" \
           -m "Replace implicit session cookies with explicit JWT tokens.

BREAKING CHANGE: All existing API clients must include
Authorization: Bearer <token> header. Session cookies are
no longer accepted."
```

## Commit Message Examples

| Good ✅ | Bad ❌ |
|:--------|:-------|
| `feat: add user login endpoint` | `feat: Added User Login Endpoint` |
| `fix: handle null token in auth` | `fix: fixed bug` |
| `refactor: extract db pool from auth` | `Big refactor` |
| `docs: add api endpoint reference` | `updated docs` |
| `chore: update lodash to 4.17.21` | `chore: update` |
| body: "Why the change was made" | body: "What the code does" |

## Tools

### Check commit message format

```bash
# Check the last N commits conform to Conventional Commits
git log --format="%s" -10 | grep -vE '^(feat|fix|refactor|docs|test|chore|ci|perf|style|wip)(\(.+\))?: ' \
  && echo "❌ Some commits don't follow Conventional Commits" \
  || echo "✅ All commits follow Conventional Commits"
```

### Generate changelog from commits

```bash
# Between two tags
git log v1.0.0..v1.1.0 --format="%s" | \
  while read line; do
    case "$line" in
      feat*) echo "### Added\n- $line";;
      fix*)  echo "### Fixed\n- $line";;
      refactor*) echo "### Changed\n- $line";;
      docs*) echo "### Documentation\n- $line";;
      *) ;;
    esac
  done
```
