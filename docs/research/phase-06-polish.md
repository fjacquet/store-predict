# Phase 6: Polish, Docs & Deployment - Research

**Researched:** 2026-02-19
**Domain:** Docker deployment, MkDocs documentation, GitHub Actions CI/CD, security hardening
**Confidence:** HIGH

## Summary

Phase 6 brings StorePredict to production readiness across five workstreams: Docker Compose hardening, file upload validation and security, performance benchmarking, MkDocs documentation with Mermaid diagrams, and GitHub Actions CI + docs deployment.

The project already had solid foundations. Key gaps addressed: hardcoded `storage_secret`, no `.dockerignore`, no server-side file validation, no logging framework, no `README.md`, and no CI pipeline.

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| File validation | Manual magic-byte check | No extra dependency (vs python-magic requiring libmagic) |
| XLSX detection | `PK\x03\x04` magic bytes | XLSX is always a ZIP archive |
| CSV detection | UTF-8 decode first 1024 bytes | Simple text heuristic |
| Docs deployment | `mkdocs gh-deploy --force` | Single command, pushes to `gh-pages` branch |
| CI actions | `actions/checkout@v4`, `setup-python@v5` | Node 20 runtime, latest stable |
| Health check | Python urllib in HEALTHCHECK | No extra tools needed in container |

## Architecture Additions

```
.github/workflows/ci.yml       # Lint, type-check, test on PR + push
.github/workflows/docs.yml     # MkDocs to GitHub Pages on push to main
.dockerignore                   # Build context exclusions
docs/architecture.md            # 3 Mermaid diagrams
docs/getting-started.md         # Docker + local dev quickstart
README.md                       # Project root quickstart
src/store_predict/pipeline/validation.py  # Server-side file validation
src/store_predict/logging_config.py       # Log sanitization framework
tests/test_performance.py       # 5000 VM + PDF benchmarks
tests/test_validation.py        # File validation tests
tests/test_log_sanitization.py  # Log sanitization + session isolation tests
```

## Pitfalls Addressed

1. **`.gitignore` vs Docker** — `DRR.csv` must be tracked despite `samples/` exclusion
2. **Hardcoded secrets** — `STORAGE_SECRET` now from `os.environ`
3. **Client-side-only validation** — Server-side magic-byte check added
4. **GitHub Pages setup** — Manual step documented in getting-started guide

## Sources

- NiceGUI docs: storage, upload, session management
- MkDocs Material docs: Mermaid setup, GitHub Actions publishing
- GitHub Actions docs: workflow syntax, Python CI
