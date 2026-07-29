#!/usr/bin/env python3
"""Create a Gitea release and upload assets.

Requirements:
  - GITEA_PAT (or GITEA_TOKEN) in environment
  - GITEA_API (optional, default: http://gitea:3000/api/v1)
  - GITHUB_REF_NAME (or TAG env var) for release tag
  - GITHUB_REPOSITORY (optional, default: alrcatraz/easytier)
  - dist/ directory with built artifacts

Usage: python3 ci-release.py
"""

import json, os, subprocess, sys, time

def api(path, data=None, method="GET"):
    token = os.environ.get("GITEA_PAT", os.environ.get("GITEA_TOKEN", ""))
    base = os.environ.get("GITEA_API", "http://gitea:3000/api/v1")
    headers = ["-s", "-X", method,
               "-H", f"Authorization: token {token}",
               "-H", "Content-Type: application/json"]
    if data is not None:
        cmd = ["curl"] + headers + ["-d", json.dumps(data), f"{base}{path}"]
    else:
        cmd = ["curl"] + headers + [f"{base}{path}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def main():
    tag = os.environ.get("GITHUB_REF_NAME", os.environ.get("TAG", ""))
    repo = os.environ.get("GITHUB_REPOSITORY", "alrcatraz/easytier")

    if not tag:
        print("ERROR: GITHUB_REF_NAME or TAG env var required", file=sys.stderr)
        sys.exit(1)

    release_data = {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": f"Automated build of {tag}",
        "draft": False,
        "prerelease": False,
    }

    # Delete existing release for this tag (idempotent)
    existing = api(f"/repos/{repo}/releases/tag/{tag}")
    try:
        existing_id = json.loads(existing).get("id")
        if existing_id:
            api(f"/repos/{repo}/releases/{existing_id}", method="DELETE")
            time.sleep(1)
            print(f"Deleted existing release {existing_id}")
    except (json.JSONDecodeError, AttributeError):
        pass

    # Create release
    resp = api(f"/repos/{repo}/releases", data=release_data, method="POST")
    try:
        release = json.loads(resp)
    except json.JSONDecodeError:
        print(f"ERROR: Failed to parse response: {resp[:500]}", file=sys.stderr)
        sys.exit(1)

    release_id = release.get("id")
    if not release_id:
        err = release.get("message", resp)
        print(f"ERROR: Failed to create release: {err}", file=sys.stderr)
        sys.exit(1)
    print(f"release_id={release_id}")

    # Upload assets
    token = os.environ.get("GITEA_PAT", os.environ.get("GITEA_TOKEN", ""))
    api_base = os.environ.get("GITEA_API", "http://gitea:3000/api/v1")

    if not os.path.isdir("dist"):
        print("WARNING: dist/ directory not found, nothing to upload")
        return

    for f in sorted(os.listdir("dist")):
        fpath = os.path.join("dist", f)
        if not os.path.isfile(fpath):
            continue
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: token {token}",
            "-F", f"attachment=@{fpath}",
            f"{api_base}/repos/{repo}/releases/{release_id}/assets?name={f}"
        ], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  -> uploaded {f}")
        else:
            print(f"  -> FAILED {f}: {result.stderr[:200]}", file=sys.stderr)

if __name__ == "__main__":
    main()
