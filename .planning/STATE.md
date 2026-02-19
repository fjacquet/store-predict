# Project State — StorePredict

## Current Phase

Phase 5: Calculation & PDF Report (IN PROGRESS)
Plans: 1 of 3 complete

## Milestone

v1.0 — MVP Sizing Tool

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

## Next Action

Execute Phase 5 (Calculation & PDF Report).

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

## Notes

- RVTools sample added (samples/rvtools.xlsx) — column names verified
- LiveOptics sample verified (samples/live-optics.xlsx) — 610 VMs
- DRR.csv has parsing quirks (embedded newlines, trailing rows) — handled by DRRTable service
- User preference: Mermaid diagrams for documentation (not ASCII art)
- User preference: Documentation in MkDocs on GitHub Pages
- User preference: NO unittest.mock — use real objects, fixtures, and sample data for tests

## Last Session

- **Stopped at:** Completed 05-01-PLAN.md
- **Timestamp:** 2026-02-19T03:59:00Z

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
