# 手工管理 Gitea Release Assets

在 CI 之外的日子里，你可能需要手工替换 release 的二进制文件——例如重新编译后替换旧文件，或直接上传从其他机器构建好的 artifact。

> 本文件覆盖 CI 之外的 API 调用（CI 内的工作流见主 SKILL.md 的 Workflow Template 章节）。

## 前提

- Gitea API Token（scope: `write:repository`）
- Gitea 地址（内部：`http://gitea:3000`，外部：`https://git01.wrt.astra-lab.org`）
- Release ID 和 Asset ID

## 列出 Release 及其 Asset ID

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

## 删除旧 Asset

**重要：Gitea v1.27 要求 Release ID + Asset ID 都在路径中。**

```bash
# ✅ 正确（Gitea v1.27+）
curl -sk -X DELETE \
  -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets/$ASSET_ID"
# → HTTP 204 No Content

# ❌ 错误（仅 asset ID，无 release ID）
curl -sk -X DELETE \
  -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/assets/$ASSET_ID"
# → HTTP 404 Not Found
```

### 如果 404

先从 `releases/{id}` 确认 asset 还存在：

```bash
curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID" | \
  python3 -c "import json,sys; [print(f'  id={a[\"id\"]} {a[\"name\"]}') for a in json.load(sys.stdin)['assets']]"
```

如果 asset 已不存在（之前已被删除），跳过删除步骤，直接上传。

## 上传新 Asset

```bash
curl -sk -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @/path/to/local/binary \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets?name=$FILENAME"
# → HTTP 201 Created，返回新 asset 的 JSON
```

`Content-Type: application/octet-stream` + `--data-binary` 方式适用于二进制文件。你也可以用 `-F attachment=@file` 方式（等同 CI 内的上传）。

## 验证上传结果

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

## 常见陷阱

### Asset ID 不是连续的

删除 asset id=9，再上传新的。新 asset 的 ID 不会是 10，而可能是 11（因为 checksum 文件的 ID=10 是在 asset 9 之后创建的）。所以**每次操作后都重新列出确认**。

### 新旧文件大小一样 = 没效果

如果替换前后文件大小没变化（例如都是 25MB），说明新编译出的二进制实际上和旧的没区别。真正的 embed 版本会比非 embed 大 3-4MB（SPA 前端文件）。

### 构造复杂 JSON Body 的 Shell 转义问题

当用 curl 创建 release 时，`-d '{"body":"multiline text\\nwith special chars"}'` 容易遇到 shell 转义问题导致提交成功但内容是乱码。推荐用 Python 脚本构造 JSON：

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

## 完整示例：替换 release 中的 embed 二进制

```bash
TOKEN="b6cf278..."
HOST="http://10.30.20.1:3000"
OWNER="alrcatraz"
REPO="easytier"
RELEASE_ID=82

# 1. 列出当前 assets
curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID" | \
  python3 -c "import json,sys; [print(a['id'], a['name']) for a in json.load(sys.stdin)['assets']]"

# 2. 删除旧的 embed asset
curl -sk -X DELETE \
  -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets/9"
# → 204

# 3. 上传新的 28MB binary
curl -sk -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @/tmp/easytier-web-embed.new \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets?name=easytier-web-embed-x86_64-v2.6.4-astra.1"
# → 201 Created，返回 asset JSON

# 4. 验证
curl -sk -H "Authorization: token $TOKEN" \
  "$HOST/api/v1/repos/$OWNER/$REPO/releases/$RELEASE_ID" | \
  python3 -c "import json,sys; [print(a['name'], a['size']) for a in json.load(sys.stdin)['assets']]"
```
