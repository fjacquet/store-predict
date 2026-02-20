# Task Completion Checklist

After completing any coding task, run these checks:

1. **Lint:** `rtk ruff check .` — must be clean
2. **Format:** `rtk ruff format .` — must be clean
3. **Type check:** `rtk mypy src/` — must be clean
4. **Tests:** `rtk pytest` — all tests must pass (currently 106+)
5. **No regressions:** Verify test count hasn't decreased

## Before Committing
- Use `rtk git status` and `rtk git diff` to review changes
- Commit with descriptive message following conventional commits
- Add `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` to commits
- Never commit secrets, .env files, or customer data

## Key Quality Rules
- Pipeline modules: zero UI imports
- Tests: no unittest.mock, use real objects
- All shell commands: prefix with `rtk`
