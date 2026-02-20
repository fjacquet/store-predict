# Project State — StorePredict

## Current Phase

Phase: Not started (defining requirements)

## Milestone

v1.1 — i18n, Branding & Intelligence

## Completed

- [x] PROJECT.md initialized
- [x] Research: Stack, Features, Architecture, Pitfalls
- [x] REQUIREMENTS.md written
- [x] ROADMAP.md written (6 phases)
- [x] CLAUDE.md created
- [x] Plan 01-01: Project structure, models, DRR table service (14 tests passing)
- [x] Plan 01-02: NiceGUI app skeleton, Docker deployment (app runs on :8080)
- [x] Plan 02-01: Core parsers (RVTools, LiveOptics xlsx/csv) with column alias resolution
- [x] Plan 02-02: Format detection orchestrator, template filtering, 29 ingestion tests
- [x] Plan 03-01: Classification engine with 29 rules, 28 tests, all 28 DRR subcategories covered
- [x] Plan 03-02: Integration tests with real sample data, DRR consistency, 82 total tests, 0% Unknown rate
- [x] Plan 04-01: Upload page with pipeline integration, session state, dark mode toggle
- [x] Plan 04-02: UI components (AG Grid VM table, workload dialog, summary stats)

- [x] Plan 04-03: Review page assembly, dark mode toggle, navigation wiring
- [x] Plan 05-01: Calculation engine with per-VM and grouped results
- [x] Plan 05-02: PDF report generator with branded layout
- [x] Plan 05-03: Report page UI with summary cards, breakdown table, PDF download, navigation

- [x] Plan 06-01: Docker deployment hardening (.dockerignore, HEALTHCHECK, env-var secret)
- [x] Plan 06-04: MkDocs documentation with architecture Mermaid diagrams, getting-started guide, README
- [x] Plan 11-01: LLM config (pydantic-settings), async classifier with circuit breaker, LLM tests
- [x] Plan 11-02: LLM fallback wired into upload pipeline, i18n keys, docker-compose env stubs, .env.example

## Current Phase Progress

Phase 11 (LLM Classification Fallback) — COMPLETE (2/2 plans done)

## Next Action

Phase 11 complete. Determine next phase to execute.

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Accurate, defensible PowerStore DRR sizing per workload
**Current focus:** v1.1 — i18n, Branding & Intelligence

## Decisions

- Used setuptools.build_meta instead of_legacy backend (not available in current setuptools)
- DRR.csv has 28 valid entries, not 30 as estimated in research
- Path import moved to TYPE_CHECKING block per ruff TCH003 rule
- Context manager layout pattern for NiceGUI shared header/nav
- Page routes registered via module import side-effect (NiceGUI convention)
- Docker not runtime-tested (daemon not running) but files validated structurally
- Column alias resolution via dict lookup (not regex) for format normalization
- Shared _build_liveoptics_df helper avoids code duplication between xlsx/csv parsers
- pandas TYPE_CHECKING import in columns.py (annotation-only), runtime import in parser modules
- openpyxl read_only mode for xlsx sheet name detection (no full parse)
- Template filtering at orchestrator level, parsers remain pure data transformers
- Reordered PostgreSQL/MySQL rules before Microsoft SQL to prevent PGSQL matching SQL pattern
- Used word boundary regex for SAP to avoid GISAPP false positive
- Included CIT pattern for Citrix (26 genuine Citrix VMs in sample data)
- Excluded Web Servers/Content not included from DRR coverage check (user override only)
- 594 VMs classified after template filtering (610 raw, 16 templates removed)
- 0% Unknown (Reducible) rate achieved on LiveOptics sample data
- Used agSelectCellEditor for inline single-workload dropdown (AG Grid community)
- WorkloadDialog uses persistent prop and use-chips to prevent accidental close
- Summary stats use get() with defaults for robustness with incomplete data
- Stats container clear+rebuild pattern for real-time updates after workload changes
- Dark mode bound to app.storage.user (not tab) for cross-page persistence
- Row click: multi-select dialog; cell edit: inline dropdown -- both update DRR conservatively
- [Phase 05]: DRR guard uses max(drr, 0.1) to prevent division by zero
- [Phase 05]: Weighted avg DRR = total_provisioned / total_required (not simple average)
- [Phase 05]: Canvas type in TYPE_CHECKING block for ReportLab PDF generation
- [Phase 05]: Vera/VeraBd fonts registered at module level for French character support
- [Phase 05]: ui.table (not AG Grid) for read-only workload breakdown display
- [Phase 05]: ui.download uses positional src arg per NiceGUI API
- [Phase 06]: Used time.perf_counter() for high-resolution performance benchmarks
- [Phase 06]: CI triggers on push and PR to main; docs triggers on push only
- [Phase 06]: STORAGE_SECRET uses os.environ.get with dev-only fallback
- [Phase 06]: Docker Compose variable substitution for secret injection
- [Phase 06]: HEALTHCHECK uses stdlib urllib.request (no extra deps)
- [Phase 06]: 3 Mermaid diagrams for architecture docs (pipeline, data flow, session model)
- [Phase 06]: README links to GitHub Pages docs site
- [Phase 06]: validate_upload() runs before temp file write to reject bad files early
- [Phase 06]: Session isolation verified architecturally via source code inspection of app.storage.tab
- [Phase 07]: Performance columns default to NaN (not 0) for clean downstream aggregation
- [Phase 07]: 8K equivalent IOPS = avg_iops + (avg_throughput_kbs / 8.0) per research formula
- [Phase 07]: Throughput KB/s to MB/s conversion at parser level for early normalization
- [Phase 07]: Fire-and-forget setFilterModel/paginationGoToPage to avoid JS timeout
- [Phase 07]: enableClickSelection: False so row clicks open dialog, checkboxes handle selection
- [Phase 07]: Two-pass classify: direct vm_name matches first, description fallback second to preserve priority semantics
- [Phase 07]: Performance fields extracted with NaN-safe helper (math.isnan check, default 0.0)
- [Phase 07]: VM Statistics always in PDF; Performance Summary conditional on has_performance_data
- [Phase 07]: PDF CIDFont subset encoding requires size comparison for testing conditional sections
- [Phase 08]: Default locale is 'fr' (French) — French is primary use case per CLAUDE.md
- [Phase 08]: t() sets python-i18n process-global locale per call — safe in NiceGUI single-threaded async
- [Phase 08]: Full page reload on locale switch (location.reload()) — ui.header cannot be in @ui.refreshable
- [Phase 08]: skip_locale_root_data=True so YAML keys not prefixed with locale name
- [Phase 08]: Lazy import of get_locale() inside t() to avoid circular import
- [Phase 08]: Renamed loop variable t->wt in review.py to avoid shadowing t() import
- [Phase 08]: :localeText uses NiceGUI JS binding syntax so AG_GRID_LOCALE_FR resolves as JS object not string
- [Phase 08]: AG Grid FR locale CDN script injected only when locale='fr'
- [Phase 08]: _i18n.set('locale', locale) once at top of generate_report_pdf() — synchronous, safe
- [Phase 08]: ReportLab CID encoding means PDF text not searchable in raw bytes; test FR != EN instead
- [Phase 08]: make_summary fixture is a factory callable in conftest.py for shared PDF test data
- [Phase 08.1]: ZIP extraction runs before validate_upload so extracted xlsx bytes go through existing validation unchanged
- [Phase 08.1]: extract_liveoptics_from_zip returns tuple[bytes, str] — xlsx bytes plus matched member filename
- [Phase 08.1]: 100 MB zip bomb guard uses central directory sum — no extraction needed for detection
- [Phase 09]: Use _i18n.t() directly (not store_predict.i18n.t() wrapper) so locale set at function entry is respected; wrapper overrides with NiceGUI session locale
- [Phase 09]: Import store_predict.i18n at module level (noqa: F401) to ensure YAML load_path configured before first _i18n.t() call
- [Phase 09]: Three excel sheets mirror CalculationSummary: Summary (label-value), Workload Breakdown (grouped), VM Detail (per-VM)
- [Phase 09]: Green Download Excel button added between PDF and Back buttons in report.py using table_view icon
- [Phase 09]: excel_report.py uses _i18n.t() directly (not t() wrapper) so locale arg to generate_report_xlsx() is honoured throughout sheet writers
- [Phase 10]: DELL_LOGO_PATH in config.py uses Path(__file__).resolve().parent for Docker-safe bundled asset resolution
- [Phase 10]: _preprocess_logo keeps both RGBA and RGB as-is; only non-RGBA/RGB modes converted to RGBA before ReportLab embedding
- [Phase 10]: _DELL_LOGO_BYTES loaded at module import time for Docker-safe path resolution and no per-call I/O
- [Phase 10]: pillow>=12.1.1 added to runtime dependencies (not dev-only) — _preprocess_logo runs in production Docker
- [Phase 10]: Logo upload section positioned below action buttons to keep primary PDF/Excel/Back buttons prominent
- [Phase 10]: base64 decode guard: empty string short-circuits to None — avoids empty bytes from b64decode of empty string
- [Phase 11]: pydantic-settings BaseSettings with LLM_ env prefix for typed config; SecretStr for api_key
- [Phase 11]: DRRTable and LLMConfig in TYPE_CHECKING block in llm_classifier.py (ruff TC001, safe with from __future__ import annotations)
- [Phase 11]: Circuit breaker as module globals — simple, zero-dependency, correct for NiceGUI single-threaded async
- [Phase 11]: classify_single_vm returns None for invalid LLM responses (not in valid_categories) — conservative sizing
- [Phase 11]: LLM_ENABLED=false default — feature opt-in via env var, never active in tests or CI
- [Phase 11]: type: ignore[assignment] on df.to_dict(orient='records') — pandas stubs return Hashable keys but str at runtime
- [Phase 11]: .env.example tracked in git for operator onboarding; .env gitignored by pre-existing entry

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01    | 01   | 11min    | 2     | 13    |
| 01    | 02   | 5min     | 2     | 5     |
| 02    | 01   | 5min     | 2     | 5     |
| 02    | 02   | 4min     | 2     | 5     |
| 03    | 01   | 7min     | 2     | 2     |
| 03    | 02   | 4min     | 2     | 1     |
| 04    | 01   | 5min     | 2     | 4     |
| 04    | 02   | 4min     | 2     | 4     |
| 04    | 03   | 6min     | 1     | 6     |
| Phase 05 P01 | 3min | 2 tasks | 3 files |
| 05    | 02   | 5min     | 2     | 2     |
| 05    | 03   | 2min     | 2     | 4     |
| Phase 06 P01 | 2min | 2 tasks | 4 files |
| Phase 06 P03 | 2min | 1 tasks | 1 files |
| Phase 06 P05 | 1min | 2 tasks | 2 files |
| 06    | 04   | 2min     | 2     | 5     |
| 07    | 01   | 3min     | 2     | 5     |
| 07    | 02   | 3min     | 2     | 2     |
| Phase 07 P03 | 2min | 2 tasks | 2 files |
| Phase 07 P04 | 3min | 2 tasks | 4 files |
| Phase 07 P05 | 5min | 2 tasks | 3 files |
| 08    | 01   | 8min     | 2     | 6     |
| Phase 08 P02 | 12min | 2 tasks | 8 files |
| 08    | 03   | 12min    | 2     | 3     |
| Phase 08.1 P01 | 3min | 3 tasks | 4 files |
| Phase 09 P01 | 8min | 2 tasks | 4 files |
| Phase 09 P02 | 14min | 2 tasks | 5 files |
| Phase 10 P01 | 20min | 2 tasks | 7 files |
| Phase 10 P02 | 10min | 2 tasks | 2 files |
| Phase 11 P01 | 12min | 2 tasks | 4 files |
| Phase 11 P02 | 8min | 2 tasks | 5 files |

## Roadmap Evolution

- Phase 8.1 inserted after Phase 8: LiveOptics ZIP extraction (URGENT)

- Phase 7 added: UI bug fixes and report enhancements

## Notes

- RVTools sample added (samples/rvtools.xlsx) — column names verified
- LiveOptics sample verified (samples/live-optics.xlsx) — 610 VMs
- DRR.csv has parsing quirks (embedded newlines, trailing rows) — handled by DRRTable service
- User preference: Mermaid diagrams for documentation (not ASCII art)
- User preference: Documentation in MkDocs on GitHub Pages
- User preference: NO unittest.mock — use real objects, fixtures, and sample data for tests

## Last Session

- **Stopped at:** Completed 11-02-PLAN.md
- **Timestamp:** 2026-02-20

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:

```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)

```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (90-99% savings)

```bash
rtk cargo test          # Cargo test failures only (90%)
rtk vitest run          # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)

```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)

```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)

```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)

```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)

```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)

```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)

```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands

```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->
