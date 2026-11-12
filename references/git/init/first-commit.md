# The first commit and what it must contain

## 9. First Commit

```bash
git add .
git commit -S -m "chore: initial project bootstrap

Set up project skeleton with README, LICENSE, gitignore, and
basic git configuration."

# Push (single remote)
git push -u origin main
```

### First commit conventions (from section 9)

| Type | When to use |
|:-----|:------------|
| `chore: initial project bootstrap` | Standard first commit — initial files, no working code yet |
| `feat: initial project scaffold` | If the first commit already includes runnable code |
| `docs: initial documentation` | Documentation-only projects |
