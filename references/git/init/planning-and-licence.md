# Repository planning and licence selection

## 1. Repository Planning

Before touching git, clarify:

| Question | Why it matters |
|:---------|:---------------|
| **What does this project do?** | Drives README structure, licence choice, gitignore patterns |
| **Public or private?** | Public → open-source licence, CI, community standards. Private → simpler |
| **Single developer or team?** | Determines commit convention strictness, PR workflow |
| **Language / framework?** | Gitignore templates, CI config, contribution guide |
| **Primary author identity?** | Which GPG key, which git user.name/email |

## 2. Licence Selection

Licence selection is a **three-step workflow**:

```
Analyse project context  →  Recommend licence  →  User decides  →  Execute
   │                             │                      │
   └── Check Fact Store /        └── Present 1–2        └── User confirms
       memory for preferences        candidates with        → Ready to
       & the existing                  rationale               implement
       project pattern
```

### Step 1 — Analyse

Before recommending, check:

1. **Fact Store** (`fact_store(action='search', query='license')`) — any stored
   preference about licences the user has stated before
2. **Academic output?** — Is this a paper, scholarly text, or research
   reproduction package? Academic output routes to tiers ① (paper → CC BY 4.0)
   or ② (reproduction code → Apache-2.0) — deliberately permissive, because
   impact (citations, reuse) outranks defensive copyleft here. See
   `references/license-guide.md` Decision Matrix.
3. **Project purpose** — is it code? Documentation? Tutorial? Mixed?
4. **Existing ecosystem pattern** — do the user's other similar projects use
   a consistent licence?
5. **Public or private?** — public projects need explicit licence; private can
   be "All rights reserved"

### Step 2 — Recommend

Present 1–2 candidates with rationale. Use the reference at
`skill_view('astra-vcs-assist-git-init', file_path='references/license-guide.md')`
for the decision matrix, fork copyright handling, and GitHub detection pitfalls.

### Practical steps

```bash
# 1. Choose your licence
# MIT (simplest):
curl -sL https://raw.githubusercontent.com/licenses/license-templates/master/templates/mit.txt \
  -o LICENSE

# CC BY-SA 4.0 (docs):
curl -sL https://raw.githubusercontent.com/samuel-phan/CC-Licenses/master/CC-BY-SA-4.0.md \
  -o LICENSE

# 2. For dual-licence projects, create a companion file
cat > LICENSE.DUAL.md << 'EOF'
# Licence Notice

This project is dual-licensed:

- **Code** is licensed under the MIT License (see `LICENSE`).
- **Documentation** is licensed under CC BY-SA 4.0.
EOF
```

### Licence verification

After adding the licence file, verify GitHub's detection:

```bash
# Push to GitHub first, then check
curl -s https://api.github.com/repos/<owner>/<repo>/license \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('license',{}).get('spdx_id','NOT DETECTED'))"
```

Expected: `MIT`, `CC-BY-SA-4.0`, `Apache-2.0`, etc. If `NOASSERTION`, the licence file may have extra text before the standard template.
