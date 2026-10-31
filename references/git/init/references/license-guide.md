# Licence Selection Guide

Quick reference for choosing and implementing project licences.

## Decision Matrix — by purpose, in priority order

The axis is **what the output must achieve**, not which licence is "better".
Driven by three constraints: academic impact first (reproduction needs
citability), free-software philosophy as practical compromise (copyleft
protects what you actually maintain), and the VCS three-step workflow
(analyse → recommend → user decides).

**Core principle:** the more an output depends on being reused/cited, the
more permissive the licence; the more it is a sovereign asset you actively
maintain, the stronger the copyleft protection.

| # | Output type | Choose | Why (priority) |
|:--|:------------|:-------|:---------------|
| ① | **Academic paper / scholarly text** | **CC BY 4.0** | Open-access mainstream; **not SA** — allows re-collection, translation, inclusion in closed anthologies (SA would force same-licence on derivatives; BY does not). Maximises citation. |
| ② | **Research reproduction code / research tool** | **Apache-2.0** (fallback **MIT**) | Reuse → citations. FSF explicitly recommends Apache-2.0 over other permissive licences (patent grant/termination). GPL-3.0-compatible, leaving a future migration path. Permissive = zero friction for adopters. |
| ③ | **Tutorial / educational content** | **CC BY-SA 4.0 (text) · MIT (code)** | Standard for education; readers reuse snippets freely. Existing judgement, unchanged: do NOT use GPL/AGPL for tutorials — copyleft would force snippet users to open-source their whole project. |
| ④ | **Infrastructure / core component you actively maintain** | **AGPL-3.0** | The philosophy's home turf. Network copyleft here, so derivatives run as services must give back. Deliberately **not** applied to academic output (①②) — impact outranks defensive freedom there. |
| ⑤ | **Private / pre-VCS-review** | **All rights reserved** | VCS admission gate not passed; never enters the public projection. |

### Supporting licences (not in the priority tiers)

| Want this? | Choose this | Notes |
|:-----------|:------------|:------|
| Maximum adoption, permissive | **MIT** | Short, simple. Industry standard for tools/libraries |
| Weak copyleft (linkable libraries) | **LGPL-3.0** | Can be linked from proprietary code |
| Share-alike copyleft (general) | **GPL-3.0** | Derivative works must also be GPL; Apache-2.0 → GPL-3.0 compatible (NOT GPLv2) |
| Dual licence (code + docs) | **MIT + CC BY-SA 4.0** | Code MIT, docs CC. README: `CC BY-SA 4.0 (text) · MIT (code examples)` |

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
