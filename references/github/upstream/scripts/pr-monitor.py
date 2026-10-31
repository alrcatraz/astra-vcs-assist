#!/usr/bin/env python3
"""Monitor open PRs for new activity: comments, reviews, CI status changes.

Reports the ACTUAL content of new activity (author, timestamp, body) instead
of just counts, so recipients can judge what happened.

Add entries to the PRS list at the top, then run:
  python3 pr-monitor.py

The script is silent on first run (initialises state).
On subsequent runs, it outputs only when something changes.
Set up as a no_agent cron job: cronjob action=create schedule="every 30m" \
  name="PR monitor" script=pr-monitor.py no_agent=true repeat=-1 deliver=origin

Each detected change ALSO posts to the `pr-activity` webhook route (signed
HMAC-V2, idempotent delivery id), which drafts a follow-up brief into the
Telegram war-room thread where the user decides next actions. The cron stdout
delivery stays untouched — dual channel, zero loss. If the gateway is down the
POST fails loudly on stderr but never blocks the report.
"""
import hashlib, hmac, json, os, subprocess, sys, time, urllib.error, urllib.request

PRS = [
    {"repo": "NousResearch/hermes-agent", "num": "73849"},   # dual-stack serve (ours, review round)
    {"repo": "NousResearch/hermes-agent", "num": "127624"},  # compaction summary prefix variants (ours)
    {"repo": "EasyTier/EasyTier",         "num": "2424"},    # MagicDNS UDP listener (ours)
    {"repo": "EasyTier/EasyTier",         "num": "2425"},    # tld_dns_zone web console (ours)
    {"repo": "chen08209/FlClash",         "num": "2456"},    # profile app shortcuts (ours)
    {"repo": "NousResearch/hermes-agent", "num": "137661"},  # ssh mux wedge fixes (ours)
]

STATE_FILE = os.path.expanduser("~/.hermes/scripts/pr-monitor-state.json")
WEBHOOK_ROUTE = "pr-activity"

def webhook_config() -> dict:
    """secret ← webhook_subscriptions.json; URL ← config.yaml. Single sources, no hardcode.

    host/port are read WITHOUT a yaml dependency (the cron interpreter may lack PyYAML):
    the platforms.webhook.extra block is located by indentation, values only."""
    subs = json.load(open(os.path.expanduser("~/.hermes/webhook_subscriptions.json")))
    route = subs[WEBHOOK_ROUTE]
    host, port = "127.0.0.1", 8644
    in_block = False
    for line in open(os.path.expanduser("~/.hermes/config.yaml")):
        s = line.rstrip("\n")
        if not in_block:
            if s.strip() == "webhook:" and s.startswith("  "):
                in_block = True
            continue
        # inside platforms.webhook — stop when dedented to or past "extra:"
        if s.strip().startswith(("host:", "port:")) and s.startswith("      "):
            v = s.split(":", 1)[1].strip().strip("'\"")
            if v:
                if s.strip().startswith("host:"): host = v
                else: port = int(v)
        elif not s.startswith("    ") and s.strip():
            break
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return {"secret": route["secret"], "url": f"http://{host}:{port}/webhooks/{WEBHOOK_ROUTE}"}

def post_webhook(brief: str, keys: list[str]) -> None:
    """Signed POST of the change brief to the pr-activity route (drafting + war-room thread).
    Loud on stderr, never raises — the cron stdout delivery must survive gateway downtime."""
    body = json.dumps({"brief": brief, "prs": sorted(keys)}, ensure_ascii=False).encode("utf-8")
    # idempotent per (PR set + change-id set): a re-run of the same batch does not re-wake the agent
    ident = ",".join(sorted(keys)) + "|" + hashlib.sha1(body).hexdigest()[:16]
    delivery_id = hashlib.sha1(ident.encode()).hexdigest()
    try:
        wc = webhook_config()
        ts = str(int(time.time()))
        sig = hmac.new(wc["secret"].encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
        req = urllib.request.Request(
            wc["url"], data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "X-Webhook-Signature-V2": sig,
                     "X-Webhook-Timestamp": ts,
                     "X-Webhook-Delivery-Id": delivery_id})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never via proxy
        with opener.open(req, timeout=15) as resp:
            status = resp.status
        if status not in (200, 202):
            print(f"pr-monitor: webhook POST unexpected {status}", file=sys.stderr)
    except Exception as e:
        print(f"pr-monitor: webhook POST failed (cron report unaffected): {e}", file=sys.stderr)

def gh_api(endpoint: str) -> dict:
    """Best-effort read of one GitHub endpoint.

    A single slow/limited call must never abort the whole run: an exception here
    would leave `old` unsaved, so the next run re-fires everything it already
    reported. One retry on timeout (the common failure under rate limiting),
    then degrade to {} for that endpoint only.
    """
    for attempt in range(2):
        try:
            r = subprocess.run(
                ["gh", "api", endpoint, "--jq", "."],
                capture_output=True, text=True, timeout=45,
            )
        except subprocess.TimeoutExpired:
            if attempt == 0:
                time.sleep(3)
                continue
            print(f"GH API timeout (2x, {endpoint})", file=sys.stderr)
            return {}
        except OSError as e:
            print(f"GH API spawn error ({endpoint}): {e}", file=sys.stderr)
            return {}
        if r.returncode != 0:
            print(f"GH API error ({endpoint}): {r.stderr.strip()}", file=sys.stderr)
            return {}
        try:
            return json.loads(r.stdout) if r.stdout.strip() else {}
        except json.JSONDecodeError as e:
            print(f"GH API bad JSON ({endpoint}): {e}", file=sys.stderr)
            return {}
    return {}

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try: return json.loads(open(STATE_FILE).read())
        except: pass
    return {}

def save_state(s: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    open(STATE_FILE, "w").write(json.dumps(s, indent=2))

def fmt_time(iso: str) -> str:
    """2026-07-31T09:19:15Z -> 2026-07-31 09:19 UTC"""
    try:
        return iso.replace("T", " ").replace("Z", " UTC")
    except Exception:
        return iso

MERGE_CONFIG = ("repos/{repo}/pulls/{num}?test=true")

def merge_cfg(repo: str, num: str) -> dict:
    """Read mergeability with ?test=1 — forces GitHub to recompute instead of
    returning a cached `mergeable: null` (the source of spurious flip-flops)."""
    return gh_api(MERGE_CONFIG.format(repo=repo, num=num))

def check_pr(repo: str, num: str, old: dict, my_login: str = "") -> list[str]:
    pr = gh_api(f"repos/{repo}/pulls/{num}")
    merge = merge_cfg(repo, num) if pr else {}
    if merge.get("mergeable") is not None:
        pr["mergeable"] = merge["mergeable"]
        pr["mergeable_state"] = merge.get("mergeable_state", pr.get("mergeable_state", ""))
        pr["rebaseable"] = merge.get("rebaseable", pr.get("rebaseable"))
    if not pr:
        return []
    key = f"{repo}#{num}"
    prev = old.get(key, {})
    changes = []

    # --- state/mergeable changes (always tracked) ---
    now_status = pr.get("state", "unknown")
    now_mergeable = pr.get("mergeable")
    if prev.get("status") and prev.get("status") != now_status:
        changes.append(f"State: {prev['status']} → {now_status}")
    # GitHub resets mergeable to null while recomputing (head move / periodic refresh);
    # a null reading is transient, not a state change — skip it and keep the prior value.
    # A null stored value means the previous tick saw GitHub mid-recompute: until a
    # real boolean arrives, no transition can be judged — skip instead of False->True noise.
    if (
        "mergeable" in prev
        and now_mergeable is not None
        and prev.get("mergeable") is not None
        and prev.get("mergeable") != now_mergeable
    ):
        changes.append(f"Mergeable: {now_mergeable}")

    # mergeable_state transition (blocked->clean = gate cleared; dirty = conflict).
    # Reject non-values: "unknown" means the mergeability check itself could not be
    # read (a failed/throttled ?test=1 window), so a transition INTO or OUT of it
    # is local noise, not upstream news. Legal set per GitHub's API docs.
    LEGAL_MS = {"dirty", "blocked", "clean", "unstable", "has_hooks", "unknown"}
    now_ms = pr.get("mergeable_state", "")
    prev_ms = prev.get("mergeable_state", "")
    # 'unknown' is a recompute-window sentinel (read failed), not a real state.
    # Skip transitions INTO or OUT OF it — only report dirty/blocked/clean/unstable/has_hooks.
    if (now_ms in LEGAL_MS and prev_ms in LEGAL_MS
            and now_ms != prev_ms
            and now_ms != "unknown" and prev_ms != "unknown"):
        changes.append(f"Mergeable state: {prev_ms} -> {now_ms}")

    # reviewDecision transition (empty->APPROVED/CHANGES_REQUESTED = reviewer acted)
    now_rd = pr.get("reviewDecision", "")
    prev_rd = prev.get("reviewDecision", "")
    if now_rd and prev_rd and now_rd != prev_rd:
        changes.append(f"Review decision: {prev_rd} -> {now_rd}")

    # --- issue comments (PR-level discussion) ---
    comments = gh_api(f"repos/{repo}/issues/{num}/comments")
    seen = set(prev.get("comment_ids", []))
    for c in comments:
        if c.get("id") not in seen:
            if my_login and c.get("user", {}).get("login") == my_login:
                seen.add(c.get("id")); continue
            body = (c.get("body") or "").strip()
            changes.append(
                f"💬 Comment by {c['user']['login']} ({fmt_time(c.get('created_at',''))}):\n"
                f"    {body}"
            )
            seen.add(c.get("id"))

    # --- inline review comments (on code lines) ---
    inline = gh_api(f"repos/{repo}/pulls/{num}/comments")
    seen_i = set(prev.get("inline_ids", []))
    for c in inline:
        if c.get("id") not in seen_i:
            if my_login and c.get("user", {}).get("login") == my_login:
                seen_i.add(c.get("id")); continue
            body = (c.get("body") or "").strip()
            path = c.get("path", "")
            line = c.get("line") or c.get("original_line") or ""
            changes.append(
                f"📝 Review comment by {c['user']['login']} "
                f"({fmt_time(c.get('created_at',''))}) on {path}:{line}:\n"
                f"    {body}"
            )
            seen_i.add(c.get("id"))

    # --- formal reviews (approvals etc.) ---
    reviews = gh_api(f"repos/{repo}/pulls/{num}/reviews")
    seen_r = set(prev.get("review_ids", []))
    for r in reviews:
        if r.get("id") not in seen_r and r.get("state") != "PENDING":
            if my_login and r.get("user", {}).get("login") == my_login:
                seen_r.add(r.get("id")); continue
            body = (r.get("body") or "").strip()
            suffix = f":\n    {body}" if body else ""
            changes.append(
                f"🔍 Review {r.get('state')} by {r['user']['login']} "
                f"({fmt_time(r.get('submitted_at',''))}){suffix}"
            )
            seen_r.add(r.get("id"))

    # Commit new state (always — fixes old bug where state only saved on change)
    old[key] = {
        "status": now_status,
        "mergeable": now_mergeable,
        # Never persist "unknown": it means the mergeability read FAILED, so keep the
        # last good value instead of poisoning the baseline (which would fire a
        # false recovery alert on the next successful tick).
        "mergeable_state": (lambda _v: _v if _v != "unknown" else prev.get("mergeable_state", ""))(pr.get("mergeable_state", "")),
        "review_decision": pr.get("reviewDecision", ""),
        "comment_ids": sorted(seen),
        "inline_ids": sorted(seen_i),
        "review_ids": sorted(seen_r),
    }
    return changes

def main():
    old = load_state()
    # resolve our own gh login once per run so we can suppress self-triggered activity
    my_login = ""
    try:
        lr = subprocess.run(["gh","api","user","--jq",".login"], capture_output=True, text=True, timeout=15)
        my_login = (lr.stdout or "").strip()
    except Exception:
        pass  # non-fatal: without it we just report our own comments too

    all_changes = []
    for pr in PRS:
        try:
            changes = check_pr(pr["repo"], pr["num"], old, my_login=my_login)
        except Exception as e:
            # one PR's failure must not abort the run or lose state for the others
            print(f"check_pr {pr['repo']}#{pr['num']} failed: {e}", file=sys.stderr)
            changes = []
        if changes:
            url = f"https://github.com/{pr['repo']}/pull/{pr['num']}"
            lines = [f"  {url}"]
            for c in changes: lines.append(f"    ⚡ {c}")
            all_changes.append("\n".join(lines))
        save_state(old)  # persist after EACH PR so partial progress survives crashes
    if all_changes:
        print("PR Activity detected:\n")
        for block in all_changes: print(block)
        # second channel: signed POST -> pr-activity route drafts into the war-room thread
        keys = [b.split("/pull/")[0].split("//")[1] for b in all_changes if "/pull/" in b]
        post_webhook("\n\n".join(all_changes), keys or ["unknown"])

if __name__ == "__main__":
    main()
