# Graphlint C++ Backend Patterns (PR #7)

Session-specific knowledge from PR #7 owner review. Useful when working on any
graphlint language backend or fixing similar issues in the C++ adapter.

## IncludeInfo dataclass pattern (shared across backends)

The framework expects `IncludeInfo` objects with an `include_path` attribute,
NOT dicts. All backends that track `#include` edges must use this shape:

```python
from dataclasses import dataclass

@dataclass
class IncludeInfo:
    include_path: str  # NOT "target" — framework reads getattr(imp, "include_path", "")
    is_system: bool
    line: int
```

In `parser.py`, append `IncludeInfo(...)` objects to `result.imports`, not dicts.
C backend uses `CIncludeInfo` — follow the same class name convention per language.

## Test-file detection pattern (follow C/C# precedent)

Three-tier detection, no config dependency for core behavior:

1. **Exact basename match** — `frozenset({"test.cpp", "test.h"})` for `test.cpp`/`test.h`
2. **Suffix endswith** — `("_test.cpp", "_tests.cpp", "_test.h", "_tests.h")` for `_test.cpp` etc.
   Note: suffixes MUST include the extension. `"my_test.cpp".endswith("_test")` is False.
3. **Prefix match** — `("test_",)` for `test_foo.cpp`
4. **Directory pattern** — files under `tests/` directory

Config `test_patterns.file_patterns` is only a fallback/additional source, never the
primary detection mechanism. The C backend (`_is_test_file`) and C# backend both
use this pattern. Entry detector (`_check_test_file`) should mirror the path-based
detection, NOT require test-named functions in the file.

## Destructor special-name handling

Destructors produce names like `"~Service"` (real class name with leading `~`).
Special-name checks must be **pattern-aware**, not exact membership:

```python
def is_special_name(self, name: str) -> bool:
    return name.startswith("~")  # destructor
    # OR match against enclosing class name for constructor collision
```

Never use placeholders like `"~CLASS_NAME"` as actual values in `_SPECIAL_NAMES`.
If you need placeholder semantics, use pattern matching (startswith, regex).

## Out-of-class member definition resolution

When a `function_definition` has a qualified declarator name containing `::`
(e.g., `A::f`), extract the scope prefix and attach the method node to the
enclosing class scope:

- Parse `qualified_identifier` / `nested_name_specifier` to split into class parts
- Build qname as `<module>.Class1.Class2.method` (flat dots, not `::`)
- Handle nested classes: `Outer::Inner::method` → `<module>.Outer.Inner.method`

The key insight: the function's qname must reflect the class it belongs to, not
the current parse scope. For `void A::f() {}` at file scope, the module qname is
`main`, so the method qname becomes `main.A.f` (not `main.f` or `main.A::f`).

## Approach A receiver-type resolution

For `obj.method()` calls, the framework documents "resolve receiver type → find method →
emit call edge." Implementation requires:

1. In `_visit_call`, before skipping the `function` child, dispatch `field_expression`
   through the Approach-A path
2. Extract receiver type from the field_expression base
3. Look up the method in the receiver's class
4. Emit proper call edge; fall back to name-based if type unknown

Without this wiring, method-call edges are missing entirely for field expressions.

## `.h` extension-split routing: C vs C++ adapters

C and C++ are SEPARATE adapters. The C adapter declares
`file_extensions = {".c", ".h"}`; the C++ `_CPP_EXTENSIONS` does NOT include `.h`. The
registry maps each extension to exactly ONE adapter (`self._by_extension[ext] = adapter`,
last-registered wins); registration order is C then C++. Result: a `.h` is ALWAYS routed to
the C adapter, so a C++ header `class Engine { void start(){} void stop(){} };` is silently
parsed with C grammar → corrupted graphs for mixed C/C++ projects.

**Fix — content-sniff `.h` routing (Approach B; picked with the user over a full adapter merge):**

The ONE place that picks the adapter for PARSING a file is `Indexer._parse_batch` in
`graphlint/incremental/indexer.py` (~L323):
```python
adapter = self.registry.adapter_for_file(fp) if self.registry else None
```
`adapter_for_file(path)` only reads the extension. For `.h` files, read the content and
pick the adapter HERE (the file is on disk).

- Add a module-level PICKLABLE sniff helper (do NOT bind to `self` / close over the
  indexer — `_parse_batch` runs under ProcessPool, so the helper must be picklable), e.g.
  `sniff_header_language(path)`.
- Heuristic (conservative): scan the first N KiB for a C++-only construct
  (`class`+ident, `namespace`, `template`, `operator`, `::`, `->`, `std::`, `#include <iostream>`,
  `.hpp`-style) → C++ adapter; a genuinely-C header with NO signal → C (backward compatible).
  Use word-bounded token regex so `class` inside a comment/string doesn't false-trigger.
- Only sniff ambiguous extensions. `.c/.cpp/.cc/.cxx/.hpp/.hh/.hxx` keep extension
  routing as today — no sniff, so both backends' existing behavior is untouched.
- Do NOT change the post-parse `adapter_for_file` call sites in `graph.py`
  (module_qname, is_special_name) — they consume already-parsed results; keep their
  extension-based behavior to minimize blast radius.

**Owner requirement: BOTH the C and C++ backends must keep working** (pure-C projects keep
.h on C; pure-C++ and mixed C/C++ projects route each .h by content). Add tests verifying
BOTH `tests/unit/test_c.py` (UNBROKEN) and `test_cpp.py` still pass, plus a new
`test_header_sniff.py` asserting routing decisions only (no parse).

This is a smaller, lower-risk alternative to FULLY MERGING C/C++ into one adapter
(Approach A), which the owner acknowledged is a larger undertaking; when the user's
constraint is "don't break either backend", content-sniffing `.h` is the right default.

## Verify-a-write-landed-before-dispatch pitfall

When dispatching an executor, the brief/dispatch scripts are written to a repo path. If the
write lands in the WRONG dir (a non-existent path, or a stale past-project path), the
executor runs nothing and you burn a round trip. BEFORE dispatching:

```bash
cd <intended-fork-path> && pwd && ls -la .task-brief-pr7-*.md pr7-r2-*.sh   # do the files exist HERE?
# then, and only then, dispatch
```

A quick `pwd` + `ls -la` + `git branch --show-current` before placing the executor
zeros in on the real repo and avoids a silent no-op dispatch.

## Round-3 lesson: parse-time sniffing is not enough

Content-sniff routing of `.h` only in `Indexer._parse_batch` is insufficient when
C and C++ remain separate adapters. Downstream graph stages may still call
extension-only `adapter_for_file`, so the same header is parsed as C++ but then
gets C semantics for:

- module qualification (`_file_to_module` must recognise `.h` when C++-owned),
- special-name and public-API checks,
- entry-rule filtering (`_adapter_parse_results` and C++ `_is_cpp_file` gates),
- cross-file constructor/destructor containment and symbol identity.

The durable fix is a **single C-family routing/identity decision** reused by parse,
module qname, special-name, public API, entry detection, and result filtering.
Do not patch only the indexer and claim the mixed-project blocker is solved. Either
introduce a cached/propagated per-file language map or make the registry's routing
helper authoritative for all consumers. Keep `.c` C and unambiguous C++ extensions
C++; plain-C `.h` must remain C. Add a cross-file `Service.h` + `main.cpp` fixture
that proves module-qualified qnames, constructor/destructor liveness, method-call
resolution, and no same-named-header collisions.

The same review exposed C++ correctness issues that should be tested independently:
- anonymous namespaces must walk their body even when no namespace node is created;
- template field qnames must apply the same template-prefix normalisation as classes
  and methods;
- `_var_types` needs scope-aware lookup (flat file-global last-writer-wins maps
  misresolve shadowed receivers);
- member-call receivers need a read usage as well as the call edge, otherwise
  `s.run()` produces false `write_only` warnings;
- constructor recognition must survive across header/source files, not rely on
  same-file name collision.

Before delegating a large round-3 refactor, write a persistent PLAN and a private
executor contract. The private contract must explicitly supersede stale local
`AGENTS.md` files, define orchestrator-only git/commit/push responsibilities, and
require C, C++, header-sniff, Ruff, and full-suite validation. Separate the work
into a routing/identity stage and visitor-correctness stages to avoid concurrent
edits to shared C++ files.

When cleaning a reviewed PR, verify claims independently: inspect the actual diff,
run the named Ruff checks, grep for stale review-marker docstrings, compare
`.gitignore` against upstream main, and test the exact owner repro rather than
trusting an executor summary. Avoid restoring local dispatch/probe/task files into
`.gitignore` when upstream deliberately removed that scaffolding block.

## Executor handoff and completion verification

For a large review-repair refactor, the orchestrator must write the PLAN, a
private executor contract, and a scope-specific brief **before** dispatching any
implementation agent. The private contract should explicitly supersede stale
repository `AGENTS.md` files, define that the orchestrator owns commit/rebase/push/
review replies, and split shared routing work from visitor work so agents do not
edit the same files concurrently.

Before dispatch, verify the handoff in the intended worktree with an absolute
root path, `pwd`, `git branch --show-current`, `git log -1`, `git status --short`,
and existence of the brief/contract. Put the same absolute root in the executor's
`--dir`; add a first-command `pwd` guard so a different workspace root fails fast.
A process exiting with code 0, or a scheduler saying it completed normally, is
**not** evidence that the task completed. Independently inspect `git diff --stat`
and the actual diff, run the named targeted tests and Ruff checks, and treat a
missing final report, permission denial, or analysis-only transcript as incomplete.
If an executor stopped with a partial diff, preserve it and give the next executor
an explicit continuation brief; never silently reset or assume the partial changes
are correct.

## Cross-file C++ constructor recognition

`CppAdapter.is_special_name(name)` cannot identify a plain constructor because it
receives only the method name and cannot know the enclosing class. Do not broaden
it so every method with a matching-looking name becomes special. At graph level,
a C++ method node whose normalised qname ends in the same two segments is a
constructor: `engine.Service.Service` means class `Service`, method `Service`.
Gate this predicate on `adapter.language_name == "cpp"` (from registry routing, NOT
the file suffix) and keep the adapter's existing `~Service` destructor and operator
predicates. Apply in every special-name callback used for component containment
and warning suppression. Test with separate `Service.h` + `main.cpp` files; a
same-file name clash does not prove cross-file correctness.

## Orchestrator vs executor on detail-heavy rounds (PR review fix loops)

When an executor stalls out on the same reasoning-heavy blocker across SEVERAL
dispatches (e.g. tracing graph reachability of a cross-file constructor), stop
re-dispatching and finish the tail yourself, but ONLY the surgical bits clearly
in your lane:

- **Strip executor debug residue.** An executor that "stalls to reason" often
  leaves `print("DEBUG ...", file=sys.stderr)` (or breakpoint/pdb) blocks inside a
  production file — here in `graphlint/analyzer/_graph_algo.py`. Always grep the
  final diff for `DEBUG|print(.*stderr|breakpoint|pdb|probe` before commit;
  remove those lines as orchestrator cleanup, not as implementing logic.
- **Strengthen the owner-regex test yourself when it is test-only.** Add the
  missing assertions (destructor not dead, `run` call edge resolves from
  `main.cpp`, no header-member dead_code warnings) using the real
  `GraphBuildResult`/`node_id_map`/`edges` fields of the existing test, then run
  the targeted suite. Test-hardening is fine for the orchestrator after an
  executor has shown it won't finish.
- After ANY clean-up, re-run the targeted C/C++/header + full suite and report
  real counts.

**Executors can still type the HOME path wrong even with an absolute `--dir`.**
In this session the executor kept producing `/home/alcatraz/...` (dropped the 'r'),
triggering `external_directory` auto-rejects on every read (`✗ Read ... failed`),
even though the dispatch script's own `cd` + `pwd` showed the correct path. The
`pwd` guard helps only the *first* command; the executor's in-reasoning reads
were typed by hand. Mitigations that actually work: (1) put the exact absolute
root in the prompt AND in the brief as a "stop if pwd differs" line, (2) if an
executor repeatedly mis-roots, stop burning dispatches and do executor-independent
verification (read the diff yourself, run the named tests), (3) prefer passing
the executor a precise recipe (exact function + qname predicate) instead of a
"figure out the API" exploration task.
