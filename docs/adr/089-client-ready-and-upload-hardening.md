# ADR-089: Stop building pages on deleted clients; harden the chunk upload endpoint

**Date:** 2026-11-08  
**Status:** Accepted

## Context

After 8 days of uptime the container sat at 40-45 % CPU and logged
`binding propagation for 38488 active links` and
`AssertionError: user storage ... should be created before accessing it`.

Every page awaited `client.connected()` and carried on. A bot that never opens
the websocket has its client deleted by NiceGUI after about 60 s, and
`connected()` then returns anyway. The page kept building elements and bindings
on the dead client, so they were never freed. The `AssertionError` is a symptom:
the user storage had already been pruned.

The same audit found the chunk upload endpoint (`/api/upload/{token}`) open to
any client with no size limit, abandoned temp uploads (customer data) never
deleted, and `docker-compose.yml` falling back to a public `STORAGE_SECRET`.

## Decision

- `client_ready()` in `ui/layout.py` awaits the connection and returns `False`
  if the client was deleted. Every page returns early on `False`.
- The upload endpoint only accepts tokens issued to a live `/upload` page (403),
  rejects uploads over 50 MB (413), and assembles files off the event loop.
- Temp uploads use the `sp_upload_` prefix, are deleted when validation fails,
  and files older than 6 h are purged at startup and on each upload-page load.
- Tab storage expires after 1 day (`app.storage.max_tab_storage_age`) instead of
  NiceGUI's 30-day default, because it holds the uploaded bytes and the VM list.
- `docker-compose.yml` refuses to start when `STORAGE_SECRET` is unset.

## Consequences

- Bot traffic no longer leaks elements or bindings. Watch the active-link count
  in the log after deploy; it should stay flat.
- Upload tokens live in a per-process set, so uploads need a single process
  (the current single-container deployment).
- Sessions older than 1 day are lost; users re-upload.
- Deployments with an existing `.env` must set a real `STORAGE_SECRET`.
