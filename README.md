# FM1 Marketplace Plugin

Source foundation for connecting the FM1 app library and its local USB bridge to Codex through MCP Apps, plugin extensions, and WebMCP.

This initial snapshot contains the existing browser store, authenticated bridge, Windows adapter, CLI, progress reporting, and offline tests. MCP endpoints, extension registration, WebMCP registration, and a Sites deployment are follow-up work; they are not implemented by this snapshot.

## Source layout

- `tools/jieli-wl82/remote_store.html`: app library, package selection, write confirmation, and job progress.
- `remote_bridge.py`: loopback HTTP service, authenticated fixed operations, durable jobs, and uncertainty handling.
- `remote_backend.py` and `flash-session-client.ps1`: adapter to an existing protected Windows flashing session.
- `remote_catalog.py`: immutable private package validation and device-baseline matching.
- `remote_client.py`: CLI with credential origin restrictions and no automatic job resubmission.
- `job_progress.py`: progress from persisted job/session metadata.
- `docs/INTEGRATION_HANDOFF.md`: integration findings and the next development steps.
- `docs/REMOTE_DEBUG_REFERENCE.md`: remote-debug setup reference maintained with the setup chat.
- `source-snapshot.json`: hashes and provenance for imported source files.

The snapshot comes from the active `progress-kit/fm1-remote` source on the Windows bench. Private packages, ROMs, songs, firmware images, credentials, session descriptors, job receipts, bundled Python, and vendor USB tooling are excluded.

## Offline verification

Use Python 3.11 or newer and a Node.js runtime with `node:test`. The tests use synthetic data, temporary directories, mocked subprocesses, and loopback HTTP. They do not open the FM1 device.

```powershell
python -m unittest discover -s tools/jieli-wl82 -p 'test_*.py'
node --test tools/jieli-wl82/test_remote_store.cjs
```

## Local operation

The bridge binds to `127.0.0.1:9770`. The store and `/v1/` API share the same origin. The store token is held in page memory; every data/operation request requires authentication.

Windows device operations require a separately prepared, verified protected flashing session and its reviewed USB dependencies. This repository includes the pipe client, but does not create that session, install Python, supply firmware, or supply the vendor loader. Use the established bench workflow for those prerequisites.

Do not start a duplicate bridge over an existing listener or redirect its state folder to this repository. Preserve the existing job state and unknown-outcome latch. Tailscale Serve can provide private HTTPS for the same-origin store. See the remote-debug reference before changing a running setup.

## Planned integration

A native plugin panel needs an MCP App/server with extension metadata. A website can additionally register WebMCP tools in its top-level page. A Sites-hosted server needs an authenticated transport to the local bridge; remote hosting alone does not make local USB accessible.

Start with the catalog, device inventory, offline app plans, and saved job progress. Preserve the store's package hash, explicit write confirmation, and existing protected writer validation when exposing writes.
