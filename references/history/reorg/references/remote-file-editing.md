# Editing Files on a Remote Working Machine over SSH

Research repos often live on a GPU laptop while the orchestrator runs on
another host. Every remote edit goes through ssh, and two failure classes
recur: silent no-ops that report success, and shell-quoting corruption.

## Write channel: scp-to-temp + mv, never heredoc-in-ssh

A base64 payload piped through a nested `ssh 'python3 -c ... <<EOF'` construct
can exit 0 with **zero bytes written** — the outer single-quote layer eats the
inner heredoc marker. Do not build file writes as quoted one-liners.

```bash
# local side: write intended content to scratch, then push as <name>.new
scp -P <port> scratch/edit_<f> user@host:<repo>/<f>.new
# remote side: verify .new byte-exact BEFORE replacing
base64 -w0 <repo>/<f>.new   # decode locally, compare == intended bytes
mv <repo>/<f>.new <repo>/<f>            # atomic replace after verification
base64 -w0 <repo>/<f>                   # read-back byte-compare AGAIN
```

Three checkpoints (arrived / replaced / read-back) — a "written" return from
any single command is not evidence the content landed.

## Read channel: base64 round-trip, not cat

Fetch full file text with `ssh 'base64 -w0 <path>'` and decode locally; raw
cat output mangles under quote layers and loses trailing-newline fidelity,
which breaks anchor matching.

## Anchor preflight: count in decoded text, not via grep -Fxc

Before any replacement, fetch the original, decode it locally, and assert
`text.count(anchor) == 1` per edit. `grep -Fxc '<full line>'` over double-
nested quoting returns spurious 0 for lines that verifiably exist (em-dashes,
backticks, `*` survive shell layers badly) — a false preflight failure that
aborts correct work. The decoded-string comparison IS the ground truth; if
shell grep disagrees with it, trust the decoded text.

## Diff visibility traps when staging an edit

- `git diff` compares working tree vs INDEX. If a prior session staged part of
  a file (`M ` column), your new edits show up in `git diff --cached` but NOT
  in plain `git diff` — checking only one of them misreads what changed.
  Always run `git status --short` first to see which column each file sits in.
- A file already staged keeps its OLD staged blob; editing the working copy
  afterwards means the staged version silently lacks your edit — re-`git add`
  before committing and confirm with `git diff --cached` containing your markers.

## Gate phases across machines

The harness classifies `ssh` itself as remote access: mutating phases
(planning/executing/closing) block it even for read-only remote commands.
Declare `accessing_device` before the batch of remote calls and return after;
do not treat a blocked ssh as "remote broken".