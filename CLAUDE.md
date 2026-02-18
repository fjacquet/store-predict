# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StorePredict is a full-Python web tool for Dell pre-sales engineers. It analyzes VMware workload exports (RVTools .xlsx, LiveOptics .xlsx/.csv) to predict Data Reduction Ratios (DRR) on Dell PowerStore arrays. Users upload a file, review auto-classified VMs, adjust workload types, and export a one-page PDF sizing report.

## Tech Stack

- **UI:** NiceGUI with Tailwind CSS
- **Data processing:** pandas, openpyxl
- **PDF generation:** ReportLab or WeasyPrint
- **Testing:** pytest
- **Linting/Formatting:** ruff, mypy
- **Deployment:** Docker Compose (single container)
- **Documentation:** MkDocs, deployed via GitHub Actions to GitHub Pages

## CRITICAL: Always use RTK prefix

**All shell commands MUST be prefixed with `rtk`** for token optimization. This applies to ALL agents, subagents, and executors — no exceptions.

```bash
# ✅ Correct
rtk git status
rtk pytest
rtk ruff check .
rtk mypy src/
rtk docker compose up --build

# ❌ Wrong (never use bare commands)
git status
pytest
ruff check .
```

Even in command chains: `rtk git add file && rtk git commit -m "msg"`

## Commands

```bash
# Development
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m store_predict.main          # Run the app

# Quality
rtk ruff check .                      # Lint
rtk ruff format .                     # Format
rtk mypy src/                         # Type check

# Testing
rtk pytest                            # All tests
rtk pytest tests/test_classifier.py -k "test_sql_detection"  # Single test
rtk pytest --cov=store_predict        # With coverage

# Docker
rtk docker compose up --build         # Run in container

# Docs
mkdocs serve                          # Local docs preview
mkdocs build                          # Build docs
```

## Architecture

### Pipeline (3 stages)

1. **Ingestion** — Parse uploaded file, detect format (RVTools vs LiveOptics), extract VM list with storage metrics
2. **Classification** — Match each VM to a workload category using rules-based pattern matching on VM Name + OS field
3. **Calculation** — Apply DRR coefficients, compute `Required Capacity = Provisioned / DRR`

### Key Data Formats

- **RVTools .xlsx:** vInfo tab — columns: VM Name, OS according to VMware Tools, Provisioned MiB, In Use MiB
- **LiveOptics .xlsx:** VMs tab — columns: VM Name, VM OS, Virtual Disk Size (MiB), Guest VM Disk Capacity/Used (MiB)
- **LiveOptics .csv:** Same data as xlsx VMs tab
- **DRR reference:** `samples/DRR.csv` — semicolon-delimited, columns: Workload Category, Application/Use case, Data Reduction Ratio

### Classification Rules

Pattern matching on VM Name and OS field maps VMs to workload categories from DRR.csv. Examples:

- "SQL", "MSSQL" → Database/Microsoft SQL (DRR: 5)
- "Oracle", "ORA" → Database/Oracle (DRR: 5)
- "VDI", "Desktop" → VDI category (DRR: 1-8 depending on clone type)
- "SAP", "HANA" → Database/SAP (DRR: 2-5)
- Windows Server without DB signals → Virtual Machines (DRR: 5)
- Unmatched → Unknown Reducible (DRR: 5)

### Multi-Workload DRR

When a VM has multiple workload types selected, use the **lowest (most conservative)** DRR among them. Pre-sales needs defensible sizing numbers.

## Conventions

- All user-facing strings should support future i18n (French is primary use case)
- DRR table is reference data loaded from CSV, not hardcoded — users may need to update ratios
- Sample data in `samples/` is real customer data — never commit additional customer data without anonymization
- Planning docs live in `.planning/` and are tracked in git
- Tests use real objects, fixtures, and sample data — never use `unittest.mock`

---

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
