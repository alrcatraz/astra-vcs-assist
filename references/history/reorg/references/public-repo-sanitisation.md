# Sanitising a public repo's history while authoring it

When the repository is public, sanitisation is part of WRITING the commit
series, not a follow-up pass. Commit → sanitise → soft-reset → re-commit means
redoing the same themed commits, and a soft reset taken from the old index can
reintroduce a pre-sanitised blob.

## Before the first commit

Fix the neutral vocabulary first, then write the commits:

- machine roles instead of machine names ("the deployment host", "the build
  host") — a hostname in a YAML comment is published as loudly as one in config;
- "the private cache" instead of its hostname or internal service name;
- no proxy egress IPs, no internal DNS suffixes, no hardware model numbers;
- secrets and tokens never in a commit at all, even one you plan to rewrite.

Host-KIND functional statements ("a NAS runs the image under Container Manager",
"rootless podman on a second host") are not leakage; names and addresses are.

## Verify against the committed tree

`git grep -nIiE '<pattern>' HEAD` describes what you are about to publish. A
worktree `grep -r` also matches ignored files and uncommitted edits, so its
result is not evidence about the pushed tree — and it misses nothing only by
accident.

Pattern set worth running every time:

```
<host names> <internal domain suffix> <service names> <egress IPs>
<vendor/proxy product names> <hardware models>
```

Re-run after the squash, and again after any amend. Run it separately for
comments (`*.yml`, `*.sh`) — a comment-only match still fails the rule.

## Related gates

- Confirm branch protection before planning a force-push:
  `gh api repos/<owner>/<repo>/branches/<branch> --jq .protected`; `false` means
  `--force-with-lease` works without an unblock step.
- Re-point release tags after a rewrite: a tag left on the old head points the
  release at orphaned history.
- For GHCR deletes, remember the API deletes a package VERSION, not a tag — see
the image-pipeline reference under the `declarative-systems` skill's guix/executor-ci material.
