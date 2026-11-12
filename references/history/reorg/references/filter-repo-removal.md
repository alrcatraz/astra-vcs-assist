# Removing a term, file or artefact from a full history

One home for every variant of the same operation. Pick the case, then follow its section — each section
is written to be copy-paste complete on its own, so the backup/verify/push blocks repeat by design
rather than sending you to another file mid-operation.

## Which case

| Situation | Case | Mode |
|:--|:--|:--|
| A term must disappear from messages **and** content everywhere | A — term purge | `--replace-text` + `--replace-message` |
| The term also leaked into file **names** | B — scrub term or artefact | adds `--invert-paths`/`--path-rename` |
| Whole files must go (a memo, a credential file, a directory) | C — purge file or term | `--invert-paths --path …` |
| One named artefact (a trace, a dataset) must be removed from every commit | D — artefact removal | `--invert-paths` on the exact path, then verify counts |
| You need the mechanics: what filter-repo does, where it rewrites, how to scope | E — mechanics | reference, not a recipe |

## Non-negotiables, whatever the case

- **Back up the whole repo first** — a bundle with `--all` is the only rollback that survives a rewrite.
- **Decide the disclosure plan before the first rewrite commit**, not after: the rewrite is the clip.
- **A rewrite renumbers every commit** — propagate to clones, pins, submodule pointers and documented SHAs
  in the same pass; nothing in the error messages points back to the rewrite.
- **`--force-with-lease`, never `--force`**, and prove the remote head with `ls-remote` afterwards.

## Where each case lives

| Case | File |
|:--|:--|
| The filter-repo mechanics every case shares (Case E) | `filter-repo-mechanics.md` |
| Case A — purge a banned term or a superseded approach | `case-a-banned-term.md` |
| Case B — scrub a term or artefact out of every commit | `case-b-scrub-artefact.md` |
| Case C — purge a term or file from an entire history | `case-c-full-history.md` |
| Case D — remove a named artefact from every commit | `case-d-named-artefact.md` |
