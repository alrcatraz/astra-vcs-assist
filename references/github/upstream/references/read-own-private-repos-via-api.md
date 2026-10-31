# Reading your OWN private GitHub repos via the REST API (non-clone)

Use when a user references one of their own GitHub repos that 404s anonymously
(it is private) and you need to inspect its contents — architecture docs, old
code, notes — WITHOUT cloning hundreds of MB.

## Account selection

`gh auth status` lists every logged-in account; ONE is Active. The active
account may not own the repo → anonymous/plain-token access 404s. Fetch a
specific account's token without switching the active account:

```bash
TOKEN=$(gh auth token --hostname github.com --user <Owner>)   # never echo it
```

Then use the REST API with `Authorization: Bearer $TOKEN`. This is read-only
and leaves `gh auth status` untouched — prefer it over `gh auth switch` for
inspection tasks.

## Efficient content survey (skip the clone)

1. Metadata first — confirms existence/private/size/language before any fetch:
   `GET /repos/<owner>/<repo>` → `private`, `size` (KB), `default_branch`,
   `pushed_at`.
2. Full file inventory in ONE call:
   `GET /repos/<owner>/<repo>/git/trees/<branch>?recursive=1`
   Check the `truncated` flag; if true, fall back to per-directory trees.
3. Classify before downloading. Engine projects commit auto-generated bloat —
   Unity `Library/PackageCache/` + `Packages/`, Godot `.godot/`+`.mono/`, Node
   `node_modules/`, build `obj/` dirs. Filter path noise (`/Library/`,
   `/PackageCache/`, `/obj/`, `/Temp/`) out of "real source" counts, or keyword
   searches drown in third-party code and you will misjudge the design.
4. Fetch only chosen blobs via `GET /repos/<o>/<r>/contents/<path>?ref=<branch>`
   (base64 `content`). URL-encode the path but keep `/` unescaped
   (`urllib.parse.quote(path, safe='/')`) — filenames containing spaces break a
   naive f-string URL ('URL can't contain control characters').
5. Look for hand-written architecture docs beside the code: `Writerside/topics/*.md`,
   `docs/`, planning notebooks. These state the author's INTENT, which raw code
   does not — often the highest-value files in the whole repo.

## Why this beats 'just clone it'

A coursework/engine repo is routinely 100–300 MB of caches and assets you never
need; the tree API answers "what exists and how big" in seconds, and selective
contents fetches pull only the few KB that matter.
