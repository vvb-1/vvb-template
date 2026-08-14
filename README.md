# VVB Project Title

Short description of what this repo is for.

## Quickstart

```bash
# Install deps
npm i    # or pip install -e .

# Test
npm test

# Lint
npm run lint
```

## Repo conventions

- Every bugfix PR: add an entry to `.learnings/ERRORS.md`
- Every meaningful change: update `CHANGELOG.md`
- iPad/touch-first if there's a UI
- Customer-facing strings: Swedish
- Internal code identifiers: English

## CI

Runs on every PR. Smart gates skip CI when only docs change.
Secret-scan runs unconditionally.

## Owners

See `.github/CODEOWNERS`. Auto-assigned on every PR.