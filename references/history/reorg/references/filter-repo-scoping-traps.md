# git-filter-repo: choosing the right rewrite mode

`git filter-repo` exposes several modes that look interchangeable and are not. Picking
the wrong one silently produces a repo that *looks* rewritten (command exits 0, history
changes) while the target file is gone, or unrelated files are destroyed, or the branch
topology has collapsed. Decide by intent, then verify the intent — never verify only
that the command succeeded.

## Mode selection

| Intent | Use | Never use for this |
|:--|:--|:--|
| Change an author/committer identity | `--mailmap <file>` (rewrites name AND email) | bare `--email-callback` — it rewrites only the address, so a rejected display name (`"Angelia (Hermes Agent)"`) survives while every email looks clean |
| Delete a file from all history | `--invert-paths --path <file>` | combining with a keep-filter |
| Substitute literal strings inside blobs | `--replace-text <rules>` | path scoping (`--path`) |
| Replace one whole file's content | `--replace-text` with full-context rules, or a fresh start (`--orphan` / squash import) when the file is fork-only infra | content-substring tests in `--blob-callback`, `--path` scoping, `--file-info-callback` |

Two modes that look like the right answer for "rewrite one file's content" are NOT
available, so do not spend attempts discovering this:

- **`--file-info-callback` cannot substitute content.** It is documented for *decisions*
  (keep / drop / rename / delete a change) and is explicitly rejected when combined with
  `--blob-callback`, `--filename-callback` or `--stdin`. Its `insert_file_with_contents()`
  helper crashes fast-import with `stream ends early` because using this mode alone sets
  `skip_blobs = True`, so blob data never enters the stream to be written back.
- **`--blob-callback` + `--path` collapses history.** The combination the table above once
  recommended was tested against a sandbox containing a merge commit and two files holding
  the same marker substring: it rewrote every revision of the target, kept unrelated files
  byte-identical, and preserved merges — then deleted every commit that did not touch the
  named path, wiping whole branches. There is no supported way to bound a content rewrite
  to one path without pruning history, so treat "replace one file across all history" as
  `--replace-text` work with precisely-matched rules.

## The traps, each with its mechanism

**`--blob-callback` cannot see paths.** Blobs are content-addressed and a callback
receives bytes only, so a test like `if b"7890" in blob.data: blob.data = new` matches
every file that happens to contain those characters — data tables, SVG coordinates, test
constants, lockfile hashes — and overwrites each one with the replacement text.
Mechanism: content-addressed matching has no notion of which file it is rewriting. Guard:
narrow the test to a string that can only occur in the intended file (a full path plus its
attribute name, not a bare port), and keep a shape assertion (`blob.data.startswith(b"{")`)
as a second line of defence.

**`--invert-paths` negates the ENTIRE path set, not the nearest `--path`.** Writing
`--path A --path B --invert-paths --path C` reads as "keep A and B, drop C" but actually
drops everything except B — the kept file disappears and the delete-list becomes the
keep-list. Mechanism: path options accumulate into one set and the inversion applies to the
set. Guard: run a deletion as its own invocation; never mix keep and drop in one.

**`--invert-paths` and `--path-rename` cannot be used in the same invocation.** A purge that
both deletes files and renames one needs TWO passes (delete first, then rename + replace),
each verified on its own; filter-repo refuses the combination outright. This matters because
`--replace-text` rewrites blob CONTENT and never filenames: a file whose name carries the
term keeps exposing it in every tree listing, diff header and `ls-tree` output even after a
perfect content scrub. Rename it across history with one `--path-rename old:new` per path,
including the pre-reorganisation path if the file ever moved and its generated sidecars
(`Foo.cs` plus `Foo.cs.uid`), then prove it with
`git log --all --name-only --pretty=format: | sort -u | grep -iE '<term>'` — the leak
surfaces in that listing, not in any content grep.

**`--path` is a history FILTER, not a rewrite scope.** It prunes every commit that does
not touch the named path, which can collapse a long history down to a single commit and
discard branches that never touched it. Mechanism: path filtering selects a sub-history,
it does not bound which blobs get modified. Guard: check commit and merge counts
immediately after any invocation that mentions `--path`, and verify each branch you intend
to publish still exists.

**`--replace-text` matches LITERALLY by default; only lines prefixed `regex:` or `glob:`
are patterns.** The belief that it is "regex-ish" is wrong and leads to needless escaping.
The real corruption mechanism is rule design, not syntax:
- A rule whose search string is a SUBSTRING of another occurrence on the same line will
  hit both, so two `http://127.0.0.1:7890` on one line splice into one mangled token when
  the replacement has different length. Write one rule per distinct surrounding form
  (`/dev/tcp/127.0.0.1/7890` uses slashes, `http://127.0.0.1:7890` uses colon+port — they
  need separate rules) rather than a loose common substring.
- Rules that do not match the file's actual text silently replace nothing, so the run
  exits 0 while the marker survives. Extract the exact surviving strings from the file
  first (`grep -nE '<marker>' <file>`), then build rules from what grep printed — never
  from memory of the wording.
- **Measure each rule's hit count in the source before writing it.** A rule that matches
  nothing looks identical to a successful rewrite (exit 0, no error). Count occurrences of
  every search string against the real pre-rewrite blob (`git show <ref>:<path> |
  grep -oF -- "$token" | wc -l`) and require each rule to fire at least once; a zero-count
  rule means the token's actual form differs (slashes vs colons, different spacing) and
  must be rewritten from the grep output.
- **A rule line without `==>` is not a comment — it is a match with an EMPTY replacement, and
  filter-repo writes the literal `***REMOVED***` there.** A rules file assembled from a
  multi-line literal (a wrapped sentence pasted as the search string) splits into one real
  rule plus an orphan line; the orphan matches its own text and blanks it, leaving
  `***REMOVED***` in EVERY revision of that file. Keep every rule on one line, and gate the
  rules file before the run: a `grep -vn '==>' rules.txt` that prints anything means a rule
  will mangle text. After the run, scan the rewritten tree for `***REMOVED***` explicitly —
  it is not a term your term-scan will catch. If it appears, do NOT patch the artefacts: the
  first pass already substituted some revisions and a second pass cannot restore them.
  Rebuild the rewrite from the pristine bundle.
Guard: after any `--replace-text` run, diff the affected file against its pre-rewrite
revision line by line and read the changed lines, and re-scan every revision for the
marker. For a heavily syntax-sensitive file, prefer replacing the whole file's content and
asserting the result parses.

**filter-repo requires a clean, single-purpose clone.** It rewrites all refs present,
including backup branches and tags, so a clone carrying leftover scratch branches or
`refs/backup/*` will rewrite those too — destroying the very backups you rely on. Guard:
clone fresh from the real remote for each rewrite attempt, and keep the rollback artifact
outside the repo (a mirror clone or bundle elsewhere on disk).

- **A recovery clone from a bundle silently omits every branch but the default.**
`git clone <bundle>` maps only the ref HEAD points at into `refs/heads/`; the rest land as
remote-tracking refs, and even then only for names the clone deems default-branch siblings.
The tell is an object count lower than the bundle recorded (`git rev-list --all --count`
82 vs 85) with NO error anywhere — the "missing" commits are simply unreachable locally, so
per-branch author audits come back clean for branches that were never there. Recover every
ref explicitly: `git fetch <bundle> '+refs/heads/*:refs/heads/*'
'+refs/tags/*:refs/tags/*'` (drop any pattern naming a checked-out branch — fetch refuses
to move it), then create missing locals from their remote-tracking twins
(`git branch dev origin/dev`) and RE-COUNT against the pre-rewrite ledger before trusting
any scan result. Same trap when restoring after an aborted rewrite: verify per-ref counts,
not just `--all`.

**A partially-applied rewrite leaves a mixed repo whose counts look plausible.** When a
first filter-repo pass succeeded on email only (or was otherwise mis-scoped) and you must
redo, do NOT keep operating in the half-rewritten clone: its tags already carry rewritten
SHAs, so re-fetching "the original state" from inside it restores nothing. Rebuild the
authoritative baseline OUT of band — clone the untouched bundle to a scratch dir, assert
per-ref commit counts and `%an <%ae>` identity sets against the pre-rewrite ledger there —
and prove content preservation by comparing the rewritten tip's TREE
(`git rev-parse <branch>^{tree}`) against the bundle clone's tree for the same branch.
Tree equality across two independent repos is the one check that survives both partial
rewrites and ref aliasing.

**A dirty worktree silently drops commits from the rewrite.** filter-repo rewrites
REACHABLE commits; changes that live only in the working tree are not commits, so they
vanish from the rewritten history without an error (exit 0 throughout). Mechanism: the
rewrite walks the commit graph, never the index or worktree. Before rewriting, run
`git status --short` and either commit or stash every modification; after the run, compare
the commit count against the pre-run record (`git rev-list --count HEAD` before vs after —
a drop means work was lost, not pruned).

**It rewrites remote-tracking refs AND any ref you fetched into the repo.** After a run,
`origin/<branch>` no longer shows the pre-rewrite state, so "diff against origin" compares
the rewritten history to itself and reports an empty — vacuous — diff. Worse, a comparison
ref fetched into the SAME working clone (`git fetch <url> '+refs/heads/*:refs/pristine/*'`)
is itself rewritten by the run, because filter-repo operates on all local refs — so the
guard added to defeat the vacuous-diff silently becomes part of the rewritten set and also
collapses to empty. Guard: snapshot the baseline OUTSIDE the repo being rewritten — record
`git ls-remote <url> refs/heads/*` SHAs to a file before cloning, or keep the mirror clone
in a separate directory — and compare against that external record (or resolve the remote
SHA's tree via `git rev-parse <sha>^{tree}`), never against a ref living inside the clone.
Symptom of falling into it: a verification step prints an empty `git diff --name-only
pristine dev` yet its `grep -vc ''` counts 1 (the empty string matches once), reporting a
collateral change that does not exist.

**A history rewrite fixes blobs in PAST revisions, not necessarily every branch TIP.**
`--replace-text`/`--mailmap` rewrite what each commit stores, but two things live at a
branch's current tip and need their own pass on EVERY branch that carries them, not just
the one you happened to check out first:
- A file you want gone from tips (junk, a stray editor scratch file): deleting it on `dev`
  leaves it still tracked at `main`'s tip if `main` diverged before the delete — verify
  with `git ls-tree -r --name-only <each-branch> | grep <junk>` across ALL branches.
- A whole-file replacement (desensitised build config): the rewrite substitutes tokens
  inside old blobs, but the tip may still hold the pre-desensitisation form; copy the
  verified clean file onto every branch that has the path and commit it there.
Guard: loop the tip fixes over the full branch list (`for B in dev main development …`),
checking `git cat-file -e HEAD:<path>` per branch so branches lacking the path are skipped,
and re-scan `ls-tree` at every tip afterwards. Branches sharing a pre-rewrite SHA stay
identical after an identical fix — confirm they still point at the same commit.

**Combine identity and content modes in ONE invocation, and chain commands only when each
is safe to skip.** Two mechanics learned the hard way:
- `--mailmap` and `--replace-text` compose cleanly in a single filter-repo call (one clone,
  one rewrite, both effects verified together). Running them as separate passes doubles the
  exposure to the ref-clobbering and baseline-collapse traps above for no benefit.
- In a `cmd1 && cmd2 && cmd3` chain, a failed `cd`/`checkout`/`fetch` does NOT stop the
  later steps the way people assume when the failure prints to stderr and the shell keeps
  going on the *current* branch — a mis-placed commit landed on the pull-request head
  branch exactly this way because `git checkout main` aborted on a dirty worktree and the
  chained `git commit` ran anyway. Before any state-changing command, assert the location:
  `git branch --show-current`. Recovery of a mis-placed unpushed commit: `git reset --hard
  <correct-sha>` on the wrong branch, then redo the commit on the right one, then prove the
  wrong branch matches its remote (`git rev-parse` both sides).

## Scoping a leak BEFORE rewriting: grep refs, not just the pickaxe

When the task is "find every ref that carries this leaked value", start from the refs
and work inward — do not lead with `git log -S`. The pickaxe reports commits where the
OCCURRENCE COUNT changed, so a value introduced via a merge (or present since a merge
brought it in) can sit in `HEAD` while `git log -S '<value>'` prints nothing at all. A
session that trusted that empty result would have concluded "not in history" about a
string plainly visible in the current tree.

```bash
# 1. which refs actually carry it right now — this is the authoritative set
for r in HEAD origin/main gitea/main origin/dev gitea/dev; do
  printf '%-16s ' "$r"; git grep -cF '<value>' "$r" -- 2>/dev/null | wc -l
done
# 2. only then ask history, and read an empty result as "inconclusive", not "absent"
git log --all --oneline -S '<value>' -- '<path>'
# 3. the refs that matter after a rewrite include the ones you did not create
#    (stale side branches, PR refs, tags, refs/tmp-*) — enumerate them
git for-each-ref --format='%(refname)' | sort
```

Enumerate side refs explicitly: a leaked value survives a branch rewrite as long as ANY
ref still reaches a commit holding it, so the ref census is part of the scope, not an
afterthought. A staging/temp ref (`refs/tmp-fix/...`) counts.

### `refs/pull/*` — the ref census entry that no branch rewrite reaches

Every pull request ever opened leaves a server-managed ref on the forge:
`refs/pull/<n>/head` (plus `/merge` on some forges). It pins the PR branch's commit **as
it stood when the PR last updated**, so force-pushing the rewritten branch does NOT move
it. After a rewrite that leaves every branch and tag clean, the leaked blob is still
fetchable by its old SHA through that ref — the rewrite looks complete from every
client-side check (`git log --all`, `git for-each-ref`, a clean working tree) because the
ref lives only on the server.

A forge that still hosts such a ref will happily serve the dirty tree:

```bash
# proves the leak is still live — run this AFTER the rewrite, not before
git init -q /tmp/probe && cd /tmp/probe
git remote add o <repo-url>
git fetch o <old-sha>        # succeeds ⇒ purge incomplete
```

**Client-side deletion is refused on both major forges, for different reasons:**

| Forge | Response | Client-side remedy |
|:--|:--|:--|
| GitHub | `! [remote rejected] refs/pull/1/head (deny updating a hidden ref)` | none — support request or recreate the repo |
| Gitea | hook decline on push; `405 Method Not Allowed` on `DELETE`/`PATCH /git/refs/...` | none via API or git protocol; purge server-side |

Gitea's copy is reachable and removable because the PR refs belong to records in the
server's own repository store. On a containerised Gitea (e.g. the `gitea/gitea` image on a
NAS) the store is a bind mount, so the purge runs through the container's git:

```bash
D=/usr/local/bin/docker        # absolute path: non-interactive ssh often lacks it in PATH
docker inspect gitea --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
#   → /some/volume/gitea/data -> /data   ⇒ bare repo at <mount>/git/repositories/<owner>/<repo>.git
R=/data/git/repositories/<owner>/<repo>.git

# the store is owned by the container's git user, not the caller → otherwise every command
# dies with "detected dubious ownership in repository"
$D exec -u git gitea git config --global --add safe.directory "$R"

$D exec -u git gitea git -C "$R" for-each-ref refs/pull --format='%(refname) %(objectname)'
for n in <pr-numbers>; do $D exec -u git gitea git -C "$R" update-ref -d "refs/pull/$n/head"; done
$D exec -u git gitea git -C "$R" reflog expire --expire=now --all
$D exec -u git gitea git -C "$R" gc --prune=now --aggressive
```

Access-shape notes that make this work when a plain `ssh <host> git ...` does not: the
**container's** git must run (a minimal NAS/host often ships no git binary at all), and
`-u git` is required because the store's owner differs from the SSH login user. Passing a
script over the pipe (`cat script.sh | ssh host 'cat > ~/s.sh && bash ~/s.sh'`) is more
robust than inlining — a non-interactive login shell's PATH frequently omits both git and
docker.

Success signatures, all four:

```bash
$D exec -u git gitea git -C "$R" for-each-ref refs/pull | wc -l   # 0
$D exec -u git gitea git -C "$R" cat-file -t <old-sha>            # "Not a valid object name"
$D exec -u git gitea git -C "$R" rev-parse main                  # tip untouched
$D exec -u git gitea git -C "$R" count-objects -v                 # object count drops
```

Then re-run the fetch probe above: it must fail with `upload-pack: not our ref`. Do the
same against every other remote; where the platform refuses client-side removal, record the
residual explicitly for the owner (purged here, outstanding there) rather than reporting
the repo clean.



Before force-pushing over, or deleting, a remote branch whose history diverges from yours,
compare by PATCH CONTENT rather than by SHA — rebases duplicate the same change under new
hashes, so "ahead N / behind M" counts overstate divergence and "ours is newer" is not an
argument:

```bash
# patch-id set for our whole lineage
git log --format=%H <our-branch> | while read h; do
  git show "$h" | git patch-id --stable | cut -d' ' -f1
done | sort -u > /tmp/pids-ours.txt

# every commit unique to the doomed branch: is its diff already represented?
while read h rest; do
  pid=$(git show "$h" | git patch-id --stable | cut -d' ' -f1)
  [ -z "$pid" ] && continue           # merge/empty commit — no diff to match
  grep -qx "$pid" /tmp/pids-ours.txt || echo "UNIQUE: $h $rest"
done < <(git log --format="%H %s" <other-branch> ^<our-branch>)
```

Zero UNIQUE lines = safe. Then check the tree level too, and **read the direction of the
diff before interpreting it**: `comm -13 <(ls-tree ours) <(ls-tree theirs)` lists files
present THERE but not HERE, which usually means the other branch is STALE (older upstream
base missing a rename our line already carries), not that we lost anything. Confirm by
finding the commit that changed the file (`git log --oneline -- <path>`) and reading its
stat — if upstream itself deleted those paths, the other branch is simply behind.

**Patch-id mismatch is not evidence of unique content — resolve it by subject + file-level
diff before retiring anything.** A lineage duplicated by a merge/rebase era produces commits
with identical subjects but different patch-ids (context drift changes the hash). The full
sequence for each apparently-unique commit: match its SUBJECT against the surviving branch
(`git log <ours> --format='%h %s' | grep -F "$subj"`), then diff the touched paths between
the two tips (`git diff <their-sha> <ours> -- <paths>` — empty means the content already
landed via later commits or squashing). Only a commit with no subject twin AND a non-empty
file diff is genuinely unique. Parallel orphan lineages (merge-base empty = zero shared
ancestry) are usually historical duplicates, not divergent work.

Tag the doomed state before deleting it (`git push <remote> <sha>:refs/tags/archive/<what>`)
so the decision stays reversible and auditable. Ordering trap: create such tags BEFORE any
force-push that makes the pointed-at commits unreachable — GitHub rejects a tag ref for an
object it no longer holds.

## Checks that actually prove the rewrite

**Your local remote-tracking ref is the OLD history until you fetch after the force-push —
verifying against it manufactures a false failure.** A force-push rewrites the server's
view; nothing updates `refs/remotes/<remote>/<branch>` locally, so it keeps pointing at the
pre-rewrite commit (its reflog shows the last pull/push, hours or days earlier). Scanning
that ref therefore reports the leak you just purged, and the natural — wrong — conclusion is
"the rewrite did not take". Always `git fetch <remote> --prune --tags --force` before any
verification, then re-read the SHA and confirm it equals the rewritten tip. Recognising the
tell saves the whole false alarm: a local tracking ref whose SHA still matches the
pre-rewrite ledger IS stale by definition, no matter how clean the rewrite was.

Three follow-on traps in the same fetch:
- `--tags` alone is refused with `would clobber existing tag` for every rewritten tag —
tags are not fast-forwarded. Add `--force` to accept the new (rewritten) tag SHAs; without
it the tag updates silently do not happen and a later scan still sees old tag content.
- Side branches based on the pre-rewrite base keep the OLD base commit, so their trees still
carry the purged values even though nothing about them is "dirty". They are not broken
work — they are unrebased work. Move them with
`git rebase --onto <new-base> <old-base> <branch>`, and treat "this branch still shows the
leak" as "this branch has not been rebased", never as "the rewrite failed".
- Local branches (including `main`) are NOT updated by fetch. After a force-push the local
`main` can sit dozens of commits "behind" in count while being a different history, not an
older one — `git log main..<remote>/main | wc -l` reports inflated divergence. Decide
explicitly whether to reset locals onto the rewritten line; do not let a stale local branch
be the base for new work.

An empty diff is a red flag, not a pass: it usually means the comparison baseline was
already rewritten or the target file no longer exists. Assert existence first, then
cleanliness.

```bash
# target still exists (guards against a vacuous pass)
test -f <file> || echo 'FAIL: target missing after rewrite'

# exactly the intended paths changed, nothing else
git diff --name-status refs/pristine/<branch> <branch>
```

**Never count lines of an empty string to decide "nothing extra changed".** `git diff
--name-only A B | grep -vcE '<expected>'` on an EMPTY diff reports 1 — the empty string is
one line — so the guard that looks strictest silently inverts into a false alarm, and its
inverse (`grep -c`) equally reports 0 for both "clean" and "baseline broken". Branch on the
variable being literally empty instead:

```bash
d=$(git diff --name-only A B)
if [ -z "$d" ]; then echo 'baseline suspect: expected at least the target path'; \
elif ! printf '%s\n' "$d" | grep -qvE '^(flake\.nix|junk/path)$'; then echo PASS; \
else echo 'collateral:'; printf '%s\n' "$d"; fi
```

```bash
# per-file size sanity — catches a whole-file clobber
for F in $(git diff --name-only refs/pristine/<branch> <branch>); do
  printf '%-40s %s -> %s\n' "$F" \
    "$(git show refs/pristine/<branch>:"$F" | wc -l)" "$(git show <branch>:"$F" | wc -l)"
done

# the secret/marker is gone from EVERY revision, not just HEAD
for R in $(git rev-list --all); do
  git cat-file -e $R:<file> 2>/dev/null && git show $R:<file> | grep -c '<marker>'
done | paste -sd+ | bc        # expect 0

# nothing but the target differs, and topology survived
printf 'commits %s merges %s\n' \
  "$(git rev-list --count <branch>)" "$(git rev-list --min-parents=2 --count <branch>)"
git log --format=%s refs/pristine/<branch> | md5sum; git log --format=%s <branch> | md5sum
```

**Prove the scoping before touching the real repo, in a throwaway `git init`.** Build a
sandbox history that reproduces the hard cases — a merge commit whose parents both edit the
target file, a branch that never touches it, and two unrelated files containing the same
marker substring — then run the exact command and assert all four outcomes: every revision
of the target rewritten, the unrelated marker-bearing files byte-identical
(`git hash-object` compare), merge and commit counts unchanged, the non-touching branch
still present. A mode that fails any of these is unusable regardless of how plausible its
documentation reads; four of this class of failure were only caught because the check was
run on a sandbox rather than on the real clone.

**Grep the whole history, not the working tree.** History is cumulative: replacing the
file at HEAD leaves the old content in every earlier commit, and every one of those
commits ships on push. A follow-up commit therefore never un-publishes a leak — only a
rewrite does. Conversely, do not over-match: a marker list containing ordinary technical
vocabulary or the author's own commit email will produce hundreds of false hits. Confirm
each surviving hit is really the leaked token (read the matching line) before concluding
the rewrite failed.

Three false-positive shapes that make an audit look like a failed purge:

- **A short token matches inside a hash.** Dumping `git log --format='%H%n%B'` and grepping
  a two-letter token hits forty-character SHAs on nearly every commit; drop the hash lines
  (`grep -vE '^[0-9a-f]{40}$'`) or read `%B` alone before counting hits.
- **A token matches inside an ordinary word.** `imitation` sits inside `limitation`, so an
  unanchored audit reports clean files as dirty at scale. Anchor with `\b` on both sides.
- **A rule covers one spelling of the term and misses its variants** — hyphenated vs spaced,
  British vs American, backticked `` `x` `` vs bare `x`, quoted `"x"` vs assignment
  `=x`. Expect two or three convergence passes: audit, read the surviving lines, extend the
  rules from what the grep actually printed, re-run. Declaring the purge done after one pass
  is the usual way a variant survives. Audit what a history exposes as legitimate attribution versus actual
leakage before publishing: an upstream contributor named in `Co-authored-by` trailers, or
the user's own public account email, is ordinary attribution; an agent-internal address, a
hostname or a local port baked into a build file is not.

**Scan BLOB OBJECTS, not the tip tree, and carry a positive control.** A tip-tree grep
answers "is it in the current revision", which is the one place a rewrite is guaranteed to
have worked. Enumerate every blob in every pack and scan those:

```bash
git cat-file --batch-all-objects --batch-check='%(objectname) %(objecttype)' \
  | grep ' blob$' | awk '{print $1}' > /tmp/blobs.txt
git cat-file --batch < /tmp/blobs.txt > /tmp/blobdata.bin   # -a: binary output
```

Run the identical scan against the PRE-rewrite mirror FIRST. A scan that reports zero hits
on the original is broken, not triumphant — and would report zero on anything. Two real
broken shapes: an empty object list (``0 blobs`` printed, no error), and a binary
`--batch` dump scanned with a line-oriented grep that misses every match. Print the object
count and the extracted byte count before reading a clean result as a pass. Also scan
commit messages (`git log --all --format='%B'`) and ref names
(`git for-each-ref --format='%(refname)'`) — the `--replace-message` channel and renamed
refs are separate surfaces from blob content.

**Never let a check pass vacuously.** Several failures here looked like successes because
the assertion iterated over an empty set: a file deleted by the rewrite makes "no private
markers in any revision" trivially true, and a pristine ref that filter-repo also rewrote
makes "diff against the original" report nothing changed. Assert existence and
non-emptiness first — target path resolves, diff lists at least the expected entries —
then assert cleanliness.

**A clean sweep proves only that the pattern list covers the classes it knows — feed every
hand-found leak back into the list in the same pass.** A repo-scoped scanner reports hits
per category (forge FQDN, absolute home path, private IP ranges, personal version suffix),
so when a leak surfaces from an AD-HOC grep rather than from the scanner, the finding is
twofold and both halves are work: the artefact leaks, AND the list has a class hole. Redact
the hit, then add the class to the scanner's pattern table and re-run to confirm the hit
count actually changed. Skipping the second half means the identical leak in a sibling file
stays invisible to every later sweep — a value survives a pass that reported its own class
clean, and the next session re-derives the same ad-hoc grep from scratch.

This is not a hypothetical shape. A scanner carrying forge, path, IP and attribution
classes reported `total leaks: 0` while a bare machine name sat in a file that IS projected
to the public end; only a hand-written `git grep -E '<hostname-family-alternation>'` found
it. Machine/host names are the class most often missing, because they do not look like the
kinds of value a secret-scanner expects — add them as a bounded alternation of the fleet's
own naming stems (`\b(<host-stem>\d+|site-[a-z]+\d+|gw\d+|...)\b`), not as
free text. Prefer a scanner that lives in the repo over a shell one-liner: regex
alternation is quoted differently by sh, bash and python, so a pipeline silently reports
wrong counts (the scanner's own header makes this point — it is why the patterns belong in
the script).

**Read the scanner's own source as part of reading its output.** Two of its reported hits
are its pattern definitions and its own docstring (the literal `<home>` and the
host-name stems written into `PATTERNS`), and the attribution class legitimately matches
every version string (`…+<owner>.<segment>`) in every SKILL.md. A future session that treats
`total leaks: N` as N leaks will "fix" the tooling and the version scheme. Triage each
reported category against the repo's own allowlist before acting on the count.
