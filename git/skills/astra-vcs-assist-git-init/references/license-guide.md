# Licence Selection Guide

Quick reference for choosing and implementing project licences.

## Decision Matrix

| Want this? | Choose this | Notes |
|:-----------|:------------|:------|
| Maximum adoption, permissive | **MIT** | Short, simple. Industry standard for tools/libraries |
| Share-alike, copyleft | **GPL-3.0** | Derivative works must also be GPL |
| Weak copyleft (libraries) | **LGPL-3.0** | Linkable from proprietary code |
| Patent protection | **Apache-2.0** | Express patent grant. Used by Google, Android, K8s |
| Documentation only | **CC BY-SA 4.0** | Standard for educational content |
| Dual licence (code + docs) | **MIT + CC BY-SA 4.0** | Code under MIT, docs under CC. README: `CC BY-SA 4.0 (text) · MIT (code examples)` |
| No licence | **All rights reserved** | Default. Others cannot copy/modify/distribute |

## Practical Steps

```bash
# MIT (code)
curl -sL https://raw.githubusercontent.com/licenses/license-templates/master/templates/mit.txt -o LICENSE

# CC BY-SA 4.0 (docs)
curl -sL https://raw.githubusercontent.com/samuel-phan/CC-Licenses/master/CC-BY-SA-4.0.md -o LICENSE

# Dual licence — companion file
cat > LICENSE.DUAL.md << 'EOF'
This project is dual-licensed:
- Code: MIT License (see `LICENSE`)
- Documentation: CC BY-SA 4.0
EOF
```

## ⚠️ GitHub Detection Pitfall

GitHub detects licences by matching `LICENSE` against SPDX standard templates. A custom preamble at the top of `LICENSE` causes `NOASSERTION`. **First line must be the template's first line.** Put explanations in a separate file.

```bash
# Verify detection
curl -s "https://api.github.com/repos/owner/repo/license" | python3 -c "import sys,json; print(json.load(sys.stdin).get('license',{}).get('spdx_id','NOT DETECTED'))"
```

## Fork Copyright Handling

```diff
 Copyright (c) 2025 Original Author
+Copyright (c) 2026 Your GitHub Account
```

- Keep original copyright — do not remove or modify
- Append your own — use your GitHub account name
- The licence text itself stays identical (MIT stays MIT)

## Tutorial Projects

| Content | Recommended | Why |
|:--------|:------------|:----|
| Tutorial text | **CC BY-SA 4.0** | Standard for educational content |
| Code/config snippets | **MIT** | Readers need to reuse freely in any environment |
| Combined | `CC BY-SA 4.0 (text) · MIT (code) © Author` | Single README line |

Do **NOT** use GPL/AGPL for tutorials — copyleft forces snippet users to open-source their entire project.
