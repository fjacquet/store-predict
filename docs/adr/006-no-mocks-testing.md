# ADR-006: Real Objects and Sample Data for Tests

**Status:** Accepted
**Date:** 2026-02-18

## Context

Testing strategy decision: use unittest.mock or real objects with actual sample data.

## Decision

Never use `unittest.mock`. All tests use real objects, fixtures, and sample data files.

## Rationale

- Real sample files (RVTools, LiveOptics) catch actual parsing issues
- Mocks can hide bugs by simulating ideal behavior
- Sample data represents real customer environments
- Tests validate the full code path, not just interfaces

## Consequences

- Tests are slower (reading real xlsx files)
- Tests depend on sample files being present
- Cannot test in isolation from dependencies
- Higher confidence that code works with real-world data
