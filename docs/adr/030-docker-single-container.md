# ADR-030: Docker Compose Single-Container Deployment

**Status:** Accepted
**Date:** 2026-02-19

## Context

StorePredict is a pre-sales tool deployed by individual engineers or on a shared internal server. The deployment must be simple and self-contained.

## Decision

Deploy as a single Docker Compose container with all state held in-memory. No external database or cache service is used.

## Rationale

- Pre-sales use case does not require persistent cross-session storage
- Single container eliminates orchestration complexity (no networking between services)
- `HEALTHCHECK` implemented with stdlib `urllib.request` — no curl/wget dependency required
- `STORAGE_SECRET` injected via environment variable with Compose variable substitution

## Alternatives Considered

- **Multi-container with Redis:** Enables session sharing across replicas but introduces operational overhead irrelevant to the use case
- **Kubernetes:** Excessive complexity for a single-engineer pre-sales tool

## Consequences

- All uploaded data is lost on container restart (acceptable; pre-sales sessions are ephemeral)
- Horizontal scaling requires sticky sessions or external session storage (not a current requirement)
- `STORAGE_SECRET` must be set in the environment; the compose file documents this requirement
