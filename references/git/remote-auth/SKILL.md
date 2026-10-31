---
name: git-remote-auth-diagnosis
description: "Use when git push or fetch fails to authenticate."
version: 1.0.0
author: alrcatraz
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [git, credentials, forgejo, github, auth, troubleshooting]
    related_skills: [credential-store-management, astra-vcs-assist]
---

# Git remote auth diagnosis

## When to use

Load when a remote operation fails with an auth-shaped error — `could not read
Username`, `Permission to <owner>/<repo> denied to <user>`, HTTP 403, or a
credential prompt in a non-interactive context — on any forge (GitHub, Forgejo,
Gitea). This covers git's own credential chain. For the VALUES (which vault
entry, which attribute, field discipline) load `credential-store-management`.

## Order of diagnosis — cheapest first

Do not start at the vault. Three of the four failure modes below never involve a
wrong password, and re-reading the store wastes the most time.

### 1. Is a helper even being invoked?

```bash
GIT_TRACE=1 GIT_TERMINAL_PROMPT=0 git ls-remote origin refs/heads/<branch> 2>&1 | head -20
```

If the trace shows the remote helper starting but **no `git-credential-…` run at
all**, the fault is configuration, not the script or the secret. Go to step 2.

### 2. Empty helper override wipes the chain

```bash
git config --show-origin --get-all credential.helper
```

An entry whose value is empty (`file:.git/config` → blank line) is **not** "use
the default": git treats it as a helper that clears the accumulated list, so
every global helper is skipped and the op falls through to an interactive
prompt — which fails outright when `GIT_TERMINAL_PROMPT=0`. That is why the
symptom looks exactly like a missing credential.

Repair and prove:

```bash
git config --unset-all credential.helper
git config credential.helper '!/home/<user>/.hermes/scripts/git-credential-<backend>.sh'
GIT_TERMINAL_PROMPT=0 git ls-remote origin refs/heads/<branch>   # expect a commit hash
```

### 3. Host not mapped / wrong store

A helper routinely maps only some hosts (`github.com`, an internal git host) and
exits 0 for everything else, by design, so the next helper in the chain can try.
Before editing the script, test it by hand with the protocol on stdin:

```bash
printf 'protocol=https\nhost=<host>\n\n' | <helper> get
# expect: username=… / password=…   (two keys, nothing else)
```

If that returns nothing for a host you expect, the mapping is missing — add a
`case "$HOST"` branch. When the host's secret lives in a DIFFERENT backend than
the rest (e.g. the fleet forge is in the KeePass SSOT while the github entries
are still in `pass`), dispatch to a child script instead of trying to merge the
backends. The parent has already consumed git's stdin, so hand the parsed values
over in the environment and let the child answer without reading the protocol
again:

```bash
[ "${1:-get}" = "get" ] || exit 0     # store/erase are never ours
case "$HOST" in
  <forge-host>) GIT_HOST="$HOST" GIT_USER_HINT="$USERNAME" \
                  exec "$HOME/.hermes/scripts/git-credential-<name>.sh" ;;
esac
```

Test the child standalone before wiring it into git
(`GIT_HOST=… GIT_USER_HINT=… <child>` → two keys, exit 0).

### 4. Wrong ACCOUNT, not wrong credential

`remote: Permission to <owner>/<repo>.git denied to <other-user>` with a token
that is otherwise valid means the tool authenticated as the wrong identity.
`gh` activates ONE account per host, and the credential helper hands that
account's token to every push — so a repo owned by account B fails while you are
active as account A, even with both logged in:

```bash
gh auth status                      # lists every account, marks the active one
gh auth switch -u <owner-account>
GPG_TTY=/dev/null git push origin <branch>
gh auth switch -u <previous-account>   # switch back in the same chain
```

`gh repo create <owner>/<repo> --public --source . --remote origin` has the same
requirement — run it under the owner account or the repository lands under the
wrong owner. Always verify with `git ls-remote origin refs/heads/<branch>`
against `git rev-parse HEAD`; a new-branch push prints a "create a pull request"
hint that reads like success regardless.

## Pitfalls

- **`GPG_TTY=/dev/null` is required on fleet machines** for headless pushes; without it a
  GUI credential manager aborts the push mid-flight and the error reads as an auth
  failure rather than a tty problem.
- **Never inline a token into a remote URL** to "fix" a 403 — it persists in `.git/config`
  in plaintext and leaks into logs. Repair the helper chain instead.
- **A one-off `GIT_ASKPASS` script is a probe, not a fix.** It is fine for proving the
  credential works (`GIT_ASKPASS=<script> GIT_TERMINAL_PROMPT=0 git push`), but it must be
  deleted afterwards and the real repair is the helper mapping — otherwise the next
  session repeats the whole diagnosis.
- **`/tmp` is often mounted `noexec`.** A throwaway `GIT_ASKPASS` or helper script
  written there fails as `cannot exec: Permission denied`, which reads like a git
  bug. Write probe scripts under the session scratch directory and `chmod 700`
  them.
- **Test helpers with the interpreter they will actually run under.** A helper that shells
  out to Python needs an interpreter that can import the vault library; a venv whose own
  interpreter cannot import the vault module must be bypassed explicitly, e.g.
  `exec env PYTHONPATH="$HOME/.hermes/hermes-agent/venv/lib/python3.13/site-packages"
  /usr/bin/python3 - <<'PY'`. Verify the child standalone; git gives you no traceback.
