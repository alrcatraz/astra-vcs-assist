# Squashing a feature's local commits before pushing

Use when the user asks to tidy the commits (整理 commit), or when one feature
accumulated fix-ups and generated artefacts that were never pushed.

## Before touching anything: re-read the repo, not your memory

```bash
git status --short && git branch -vv && git log --oneline -3
```

After a context handoff or a gap of a day, the remembered `HEAD` may no longer
exist (someone rewrote history) and the checked-out branch may not be the one you
left. Uncommitted work from another workstream is a paused task, not an empty
workspace: never stage it with `git add -A`, never squash underneath it, and say
which paths you left untouched.

## Preconditions

```bash
git log --oneline origin/development..HEAD   # range must be local-only
git status --short                            # know what is dirty before rewriting
```

Never squash a commit that exists on a remote; rewriting it forces a force-push
the user has to approve.

If the tree is dirty with work you did not make, stop and ask. A day-old dirty
tree on a side branch is a paused workstream; squashing underneath it mixes two
tasks into one history. Either commit that work separately (with the owner's
agreement) or commit only your own paths first.

## Recipe

```bash
git format-patch -q origin/development..HEAD -o /tmp/patch-backup   # escape hatch
git rev-parse HEAD > /tmp/before
git reset --soft origin/development
git commit -F /tmp/msg.txt
git diff "$(cat /tmp/before)" HEAD --stat | wc -l                  # must print 0
```

The zero-line diff is the proof that only history changed: the squashed tree is
byte-identical to what the branch held before. Report it — it is what makes a
history rewrite safe to push.

## What belongs in the single commit

- The feature as a whole, including the generated documentation/API pages that
  changed only because the feature changed a public surface.
- The bug found on the way, described by mechanism (not as a separate commit):
  "services were built in the constructor, so configuration never reached
  them" is one line inside the feature, not its own `fix:` entry.
- Measured before/after evidence for each claim the message makes.

Docs-only regeneration commits are noise in a feature's history. Fold them in.

## Message shape

Why the change was needed → what each section/file now owns → the pitfall that
cost time (and why it was invisible) → verification numbers. No chronology, no
"fix typo", no dates.

## After pushing

```bash
git fetch -q origin && git rev-parse --short origin/development   # equals local
git log --format="%an <%ae> %G?" -3                                # identity + signature
```

Squashing preserves the author of the original commits only when the single
commit is created fresh; confirm the identity and the GPG status before saying
it is done, and merge to `main` with a signed local merge — never via a forge
API, which commits under the token's account and without a signature.
