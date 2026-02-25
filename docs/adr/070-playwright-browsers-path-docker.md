# ADR-070: PLAYWRIGHT_BROWSERS_PATH for Non-Root Docker Execution

**Status:** Accepted
**Date:** 2026-02-25

## Context

PDF generation in StorePredict uses Playwright (headless Chromium) to render the
print-optimised NiceGUI page and export it as a PDF. The Dockerfile installs
Chromium during the build phase (as root) and then switches to a non-root
`appuser` for the runtime process.

By default, Playwright stores browser binaries under `~/.cache/ms-playwright`.
When installed as root this resolves to `/root/.cache/ms-playwright`. At runtime,
`appuser` looks in `/home/appuser/.cache/ms-playwright`, which does not exist,
causing every PDF export to fail with a browser-not-found error.

## Decision

Set the `PLAYWRIGHT_BROWSERS_PATH` environment variable to `/ms-playwright` in the
Dockerfile before the `playwright install` step. After installation, grant world
read+execute on that directory with `chmod -R o+rX /ms-playwright`.

```dockerfile
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN .venv/bin/playwright install chromium --with-deps \
    && chmod -R o+rX /ms-playwright
```

The `ENV` directive persists into the runtime container so the Playwright Python
API discovers the correct path automatically — no application code change required.

## Rationale

- A fixed, non-home-relative path is independent of which user runs the process.
- `ENV` propagates to every subsequent layer and to the final running container.
- `chmod o+rX` is the minimum permission grant: read and directory-traverse for
  "other", without making binaries writable.
- No alternative (e.g. keeping the `root` user, or copying the cache into the
  home directory) is as clean or as secure.

## Alternatives Considered

- **Run as root:** Avoids the permission problem but violates container security
  best-practices and is rejected by hardened Kubernetes/OpenShift environments.
- **Copy `/root/.cache/ms-playwright` to `/home/appuser/.cache/`:** Works but is
  fragile (the copy must happen after `useradd`) and duplicates disk usage.
- **`--with-deps` already called — skip chmod:** `--with-deps` installs system
  packages but does not change the `755`/`700` permissions of the browser cache
  directory itself, which is still owned by root with mode `700`.

## Consequences

- All PDF exports (DRR report, layout report, concerns report) work correctly in
  the production container under `appuser`.
- The `/ms-playwright` directory adds ~200 MB to the image; this was already
  present in the layer — the fix merely makes it accessible.
- Rebuilding the image is required to apply this fix to existing deployments.
