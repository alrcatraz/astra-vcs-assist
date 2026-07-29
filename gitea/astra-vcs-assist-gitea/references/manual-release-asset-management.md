# Managing Gitea Release Assets by Hand

On days without CI you may need to replace a release binary by hand — after a
rebuild, or when uploading an artefact built on another machine.

> This file covers API calls outside CI; for in-CI workflows see the main
> SKILL.md Workflow Template section.

## Prerequisites

- Gitea API Token（scope: `write:repository`）
- Gitea URL (internal and external forms)
- The Release ID and Asset ID

## List releases and their asset IDs

```bash
TOKEN="your-gitea-token"
HOST="http://gitea:3000"
OWNER="alrcatraz"
REPO="easytier"

curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases?limit=5" | \
  python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f\"Release: {r['tag_name']} (id={r['id']})\")
    for a in r.get('assets', []):
        print(f\"  id={a['id']} name={a['name']} size={a['size']} dl_count={a.get('download_count',0)}\")
"
```

## Delete the old asset

**Important: Gitea v1.27 requires both the Release ID and the Asset ID in the path.**

```bash
# correct (Gitea v1.27+)
curl -sk -X DELETE \
  -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets/$ASSET_ID"
# → HTTP 204 No Content

# wrong (asset ID only, no release ID)
curl -sk -X DELETE \
  -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/assets/$ASSET_ID"
# → HTTP 404 Not Found
```

### If it returns 404

First confirm the asset still exists via `releases/{id}`:

```bash
curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID" | \
  python3 -c "import json,sys; [print(f'  id={a[\"id\"]} {a[\"name\"]}') for a in json.load(sys.stdin)['assets']]"
```

If the asset is already gone (deleted earlier), skip deletion and upload directly.

## Upload the new asset

```bash
curl -sk -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @/path/to/local/binary \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets?name=$FILENAME"
# -> HTTP 201 Created, returns the new asset JSON
```

`Content-Type: application/octet-stream` + `--data-binary` works for binaries. You can also use `-F attachment=@file` (equivalent to the in-CI upload).

## Verify the upload

```bash
curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID" | \
  python3 -c "
import json,sys; data=json.load(sys.stdin)
print(f\"Release: {data['tag_name']}\")
for a in data.get('assets', []):
    print(f\"  {a['name']} ({a['size']}B) ✓\")
"
```

## Common pitfalls

### Asset IDs are not sequential

Delete asset id=9, then upload: the new ID is not 10 but possibly 11 (the checksum
file took ID=10 after asset 9 was created). **Always re-list and confirm after every operation.**

### Same file size before and after = no effect

If the size is unchanged (e.g. both 25MB), the "new" binary is effectively identical
to the old one. A genuine embed build is 3-4MB larger (the SPA frontend files).

### Shell escaping when building complex JSON bodies

When creating a release with curl, `-d '{"body":"multiline text\\nwith special chars"}'` and may succeed while storing mojibake. Build the JSON with a Python script instead:

```python
import json, subprocess
data = {
    "tag_name": tag,
    "name": f"Release {tag}",
    "body": "Release notes with\nmultiline content",
    "draft": False,
    "prerelease": False,
}
cmd = ["curl", "-s", "-X", "POST",
       "-H", f"Authorization: token {token}",
       "-H", "Content-Type: application/json",
       "-d", json.dumps(data),
       f"{host}/api/v1/repos/{owner}/{repo}/releases"]
result = subprocess.run(cmd, capture_output=True, text=True)
```

## Full example: replacing the embed binary in a release

```bash
TOKEN="b6cf278..."
HOST="http://10.30.20.1:3000"
OWNER="alrcatraz"
REPO="easytier"
RELEASE_ID=82

# 1. list current assets
curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID" | \
  python3 -c "import json,sys; [print(a['id'], a['name']) for a in json.load(sys.stdin)['assets']]"

# 2. delete the old embed asset
curl -sk -X DELETE \
  -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets/9"
# → 204

# 3. upload the new 28MB binary
curl -sk -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @/tmp/easytier-web-embed.new \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets?name=easytier-web-embed-x86_64-v2.6.4-astra.1"
# -> 201 Created, returns the asset JSON

# 4. verify
curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID" | \
  python3 -c "import json,sys; [print(a['name'], a['size']) for a in json.load(sys.stdin)['assets']]"
```
