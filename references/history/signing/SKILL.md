---
name: git-history-signing
description: "Use when commits are unsigned or authorship is unclear."
version: 1.0.0
author: alrcatraz
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [git, gpg, signing, provenance, rewrite]
    related_skills: [astra-vcs-assist, git-remote-auth-diagnosis, git-history-reorg]
---

# Git history signing

## When to Use

Load when commits are unsigned and must be signed, when a rewrite has to
preserve authorship, or when the question is which author or account a commit
belongs to. This covers the REWRITE and the PROOF. For key creation, import,
passphrase caching and `gpg failed to sign`, load `astra-vcs-assist` → `references/gpg/key-lifecycle/`.

## Order of operations

Decide identity → configure signing → replay with `-S` → verify locally →
push with lease → verify the remote → repair anything that pinned the old SHAs.

### 0. Routine commits: the pairing check costs seconds

Rewrites are rare; ordinary commits are not, and the same rule applies to them:
the author must be the account that owns the repository. Check the pairing before
touching the index:

```bash
git remote -v | head -1                        # owner appears in the URL
gh repo view --json owner -q .owner.login      # authoritative on GitHub
git config --get user.name; git config --get user.email
```

If they disagree, set the identity **repo-locally** (`git config user.name` /
`user.email`, no `--global`): a global value silently re-authors every other
project the next time you commit there.

A session that spans several repositories has one identity per repository. A
public GitHub repo owned by the real-name account and a private forge repo owned
by the personal handle legitimately differ, and the local config of one says
nothing about the other — check each repo rather than assuming the identity you
just used carries over.

Prove it on what actually landed, signature state included:

```bash
git log --show-signature -3 --format="%h %G? %an <%ae> %s"
```

`%G?` must read `G` and the address must be the owner's. With
`commit.gpgsign=true` and a mismatched `user.signingkey` this single line shows
either a missing signature or one made by the wrong key.

### 1. Decide the identity BEFORE rewriting

Rewriting is the moment the author name, email and signing key become one
committed choice, and changing it later costs another rewrite. Settle three
things first:

- which name/email the commits carry (personal handle vs real name);
- that the chosen key's UID contains that email — a signature whose key does
  not match the commit email verifies as bad or unassociated;
- that the public key is uploaded to the forge account that should own the
  commits, not merely present on the machine.

Never sign with an agent identity (an address allocated to tooling). Use the
human identity that owns the repository.

Ownership decides, not preference: a repository owned by the real-name account
takes real-name authorship signed with the key registered on THAT account, and a
repository owned by a personal handle takes the handle. Mixing them is what
produces commits that link to a different account than the one hosting the repo.
When the owner is a real-name account, also expect the sanitisation bar to rise —
see skill `repo-language-convention`, its
`../reorg/references/public-repo-sanitisation.md`.

Check which account a given email resolves to before choosing, rather than after
the rewrite:

### 2. Configure, then replay

```bash
git config user.signingkey <key-id>
git config commit.gpgsign true
git config tag.gpgsign true
git config pull.ff only
```

Whole history, when every commit in the repository is yours:

```bash
git rebase --root -x 'git commit --amend --no-edit -S'
```

Fork branch — sign only your own commits; replaying the upstream range would
re-commit thousands of upstream commits under your name:

```bash
git log --oneline master..<branch> | wc -l        # scope check first
GIT_SEQUENCE_EDITOR=true git rebase master -x 'git commit --amend --no-edit -S'
git log --format='%h %G?' master..<branch>        # every line must read G
```

`--no-edit` preserves message, author, author date and tree; only the committer
date and the signature change. The signing agent must hold the passphrase — a
batch signs in seconds once it is cached, and prompts (or silently fails) when
it is not.

### 2b. Changing the authorship itself

Signing and reauthoring are different rewrites; do them together when both are
needed. Whole history, keeping the original author dates:

```bash
git rebase --root -x 'git commit --amend --no-edit --author="<Name> <email>" -S'
```

`--reset-author` also overwrites the author DATE with now — use it only when the
date should move too, never as a shorthand for changing the name.

Mixed history — some commits already carry the target identity, one arrived
through the forge's web editor, and upstream commits must not move — needs a
conditional filter rather than a replay:

```bash
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --commit-filter '
  if [ "$GIT_AUTHOR_NAME" = "<old-name>" ]; then
    GIT_AUTHOR_NAME="<new-name>"; GIT_AUTHOR_EMAIL="<email>"
    export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL
  fi
  case "$GIT_COMMITTER_NAME" in
    <old-name>|GitHub)
      GIT_COMMITTER_NAME="<new-name>"; GIT_COMMITTER_EMAIL="<email>"
      export GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL ;;
  esac
  git commit-tree -S "$@"
' -- --all
```

`-- --all` also rewrites the remote-tracking refs, which makes the next
`--force-with-lease` think the remote moved. Delete `refs/original/*` afterwards
and re-read the real remote head with `git ls-remote`.

### 3. Verify locally

```bash
git log --format='%h %G? %an <%ae>' -5      # G good, B bad, N unsigned
```

Do **not** run `%G?` over a large upstream fork: it verifies every signature,
and SSH-signed upstream commits abort the walk with
`gpg.ssh.allowedSignersFile needs to be configured`. Scope to the range you own.

Authorship consistency — the author/committer split is where an accidental
"committed by the automation account" shows up:

```bash
git log --format='%an <%ae>' | sort | uniq -c
git log --format='%cn <%ce>' | sort | uniq -c
git log --format='%an|%ae|%cn|%ce' | awk -F'|' '$1!=$3 || $2!=$4' | wc -l   # expect 0
```

### 4. Push and prove the remote took it

```bash
git push --force-with-lease origin <branch>
git ls-remote origin refs/heads/<branch>; git rev-parse HEAD   # must match
```

`--force-with-lease`, never bare `--force`: it refuses when the remote moved,
which is the only guard against clobbering work you cannot see. The push output
(`+ aaa...bbb main -> main (forced update)`) proves only that the local ref was
accepted — compare the remote head explicitly.

### 5. Repair everything that pinned the old SHAs

A rewrite renumbers every commit. Channel pins, submodule pointers, documented
`(commit "<sha>")` entries and CI references to the old hashes stop resolving,
and nothing in the error points back to the rewrite:

```bash
git grep -nE '<old-sha-prefix>|<other-old-prefix>'    # in every dependent repo
```

Update them in the same pass, as a signed commit, and re-check that the grep
returns nothing.

### 6. Prove attribution on the forge

Local `%G?` says the object is signed; it says nothing about which account the
forge links it to:

```bash
gh api users/<account>/gpg_keys        # key_id ↔ email binding, public view
gh api "repos/<owner>/<repo>/commits?sha=<branch>&per_page=1"
#   .commit.verification.verified   → forge accepted the signature
#   .commit.author.email            → email on the commit
#   .author.login                   → ACCOUNT the commit is attributed to
```

A repo owned by account A whose commits carry account B's verified email links
every commit to B. That is legitimate but confusing in collaboration — decide
deliberately, per repository class (personal handle for personal projects, real
name for academic or organisation-facing ones).

## Pitfalls

- **`gh api user/emails` returns 404** without the `user` scope; that is not a
  missing token. Use the commits API's `.author.login` and `.verification`
  fields instead of trying to enumerate emails.
- **Rewriting a public branch is not free.** Force-pushed public history breaks
  other clones and forks. Only do it while the repository is young with no
  forks or stars, and tell the user that any existing clone needs
  `git fetch --prune && git reset --hard origin/<branch>`.
- **Do not re-sign upstream commits in a fork.** Their provenance is the point
  of a fork; replay only `master..<branch>`.
- **A green local `%G?` with an unlinked forge account looks like success and is
  not.** Check `.author.login` before reporting attribution.
- **The forge verifies the signature against the COMMITTER email.** A commit
  written in the web editor carries committer `GitHub <noreply@github.com>`;
  re-signing it with your key leaves `verification.verified=false` with
  `reason=unknown_key` even though author, author email and signing key all
  match. Normalise the committer in the same rewrite, then re-check the API.
- **`--force-with-lease` refusing with `stale info` means the remote moved.**
  Do not escalate to `--force`. `git fetch origin <branch>` and inspect the new
  head first: committer `GitHub <noreply@github.com>` is the owner editing
  through the web UI, and that content must be preserved — rebase your work onto
  it instead of replacing it.
- **Inside a rebase, `--ours` and `--theirs` are swapped** relative to a merge:
  `--ours` is the upstream side you are replaying onto, `--theirs` is the commit
  being applied. Confirm with `git show <ref>:<file>` before resolving, or you
  silently keep the wrong side of every conflict.
- **Signing is a per-repository convention, not a reflex.** Read the existing
  state before choosing: `git config --get commit.gpgsign` plus
  `git log --format='%h %G?' -5`. A run of `G` means sign with `-S`; all `N` with
  no config means the repository's convention is unsigned — commit unsigned, in
  keeping with its history, and state that in the report rather than leaving one
  isolated signed commit in an otherwise unsigned line. Never flip a repository's
  signing configuration to make a single commit pass, and never let "did it get
  signed?" be something the user has to guess.
- **A commit whose message is yours but whose content is someone else's is a
  provenance failure.** In worktrees that other actors also write (the skills
  tree with its background curator, a checkout another session is mid-way
  through, machine-wide dotfiles), `git status` shows unrelated dirty files and
  `git add -A` sweeps them into your commit — usually noticed only after the
  commit exists. Always stage explicit paths, then assert the staged set with
  `git status --porcelain` before committing; a directory argument is safe only
  when every file under it is yours. If the sweep already happened, redo without
  losing edits: `git reset --soft HEAD~1 && git restore --staged .` — never
  `--hard`.
