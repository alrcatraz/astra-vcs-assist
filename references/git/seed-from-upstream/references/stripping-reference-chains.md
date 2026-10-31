# Stripping Reference Chains (<our-project> Phase 1 cleanup, 2nd pass)

Second-pass lessons from stripping upstream-only machinery (Electron shell,
42-locale docs mirrors, upstream CI jobs) AFTER the initial workflow prune.
Each item is a "grep for it" step — the reference chain always runs deeper
than the first grep. Companion to `upstream-baggage-pruning.md`.

## 1. CI job deletion residuals (inside a kept workflow)

Deleting a job from `ci.yml` left three dangling references, each a separate
failure mode:

- `needs:` entry in a downstream job → workflow parse/run failure
- step-summary echo table row (`| Electron Package Smoke | ...`) → undefined
  status in the summary
- PR-check echo text mentioning the deleted path (`` `electron/` ``) → stale
  gate text

Grep after deletion: `grep -n "<job-name>" .github/workflows/ci.yml`.

## 2. npm script ↔ workflow contract (bootstrap-dropped script)

`build:cli` was dropped from package.json during bootstrap, but ci.yml's
package-artifact job AND `build:release` still ran `npm run build:cli` — CI
would fail at first run. Recovery: restore the upstream definition
(`"build:cli": "node --import tsx scripts/build/prepublish.ts"`) instead of
rewriting workflows. Rule: after any package.json script surgery, grep
`.github/` for every `npm run <name>` and reconcile.

## 3. Orphan-script test is three-way

A script is only orphaned if NONE of these reference it:

- package.json `scripts`
- `.github/workflows/*` (`run:` or `uses:`)
- `tests/unit/*` — tests import release tooling directly
  (`sync-next-cycle.mjs` is imported by its test, so it is NOT orphaned even
  though no npm script calls it)

Check all three before `git rm`.

## 4. Doc-mirror removal (42-locale docs/i18n tree)

Reference chain for a multi-locale mirror tree — every link must be cut:

- scripts: walk filters (`!rel.startsWith("docs/i18n/")`), exclude lists
  (add-frontmatter, fix-internal-links), dedicated mirror scripts
  (run-translation, sync-llm-mirrors, move-i18n-mirrors,
  sync-changelog-i18n)
- release tooling that regenerates mirrors (sync-next-cycle.mjs: mirror merge
  block + `npm run release:sync-changelog-i18n` calls)
- tests: `readdirSync(docs/i18n)` iteration, sync-changelog-i18n assertions
- package.json scripts (`i18n:run`, `i18n:run:dry`,
  `release:sync-changelog-i18n`) + `lint:md` excludes
- `.dockerignore` entries, husky pre-commit hook lines
- docs-route fallback code: `tryI18nFallback` + path helper
  (`docsI18nPath.ts`) + its security test
- i18n message keys only the removed UI used (e.g.
  `startOnLogin`/`startOnLoginDesc` in every locale file)

Final check: `grep -rn "docs/i18n" src/ scripts/ tests/ package.json .github/`
→ only harmless comments may remain.

## 5. Electron / desktop-shell removal

- Delete `electron/` dir + dedicated build scripts
  (prepare-electron-standalone, smoke-electron-packaged)
- Grep src/ for the hook import chain — electron integration hides in: layout
  window-control body classes (`electron-macos`), settings autostart toggles,
  auth-page data-dir prefills, dashboard update banners with upstream download
  URLs (brand leak: `github.com/<upstream>/releases`), and the shared hook
  file itself
- Collapse the shared hook file to the one generic helper that survives
  (e.g. `useOpenExternal`), using `(window as any).electronAPI` to drop the
  dead type dependency
- Delete now-unused i18n keys from ALL locale files (they carry upstream
  brand strings)

## 6. Self-hosted runner configs

`runs-on: ${{ (vars.USE_VPS_RUNNER == 'true' && ...) && fromJSON('["self-hosted","omni-release"]') || 'ubuntu-latest' }}`
→ replace with plain `runs-on: ubuntu-latest` when the fork has no runner
fleet. Grep: `USE_VPS_RUNNER|omni-release|self-hosted`.

## 7. Verification after bulk edits

- Line-number deletion on TSX/JS leaves dangling closures and duplicate
  `</div>` that `tsc` misreports at a far line. Fast check:
  `npx esbuild <file> --loader:.tsx=tsx --outfile=/dev/null` (parses in ms)
  before the full `tsc --noEmit`.
- After every patch on a `.mjs` script, `node --check <file>` — the patch
  tool's fuzzy matching can swallow an adjacent line (e.g. an opening
  `push(`) and still report success.
- Re-run affected unit tests: `node --import tsx/esm --test <files>` — tests
  referencing removed mechanisms fail with the exact error
  (`readdirSync` ReferenceError = orphaned import; assertion on a deleted npm
  script = stale test to delete).
