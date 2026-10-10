# FM1 Marketplace Plugin

FM1 app library integration for ChatGPT and Codex through a private Site,
MCP App panel, plugin extension entrypoints, and top-level WebMCP tools.

The implementation includes the existing browser store/bridge, a Sites Worker
with HTTP MCP at `/mcp`, a durable D1 request queue, an MCP App library panel,
global/thread extension metadata, WebMCP registration, and an outbound Windows
relay. The relay keeps the existing authenticated bridge and protected writer
local. Version 4 is privately deployed with pinned server SDK 2.3.1 and
ext-apps 2.0.3. It detects serial, UBOOT and official MIDI/SysEx modes, selects
the protected app route automatically, and provides a reviewed handoff to the
pinned official Windows updater. Firmware writes still require human confirmation.
Local tests/build, protected runtime setup, verified readback adoption and the
native offline plan passed. Physical candidate write and startup acceptance
remain separate.
See [VERIFICATION.md](docs/VERIFICATION.md).

The owner-private [FM1 App Library](https://fm1-app-library.keitark.chatgpt.site)
is deployed and MCP-ready, and its plugin is installed. The native Codex panel
uses the black/mint interface with connection, detected mode, packages and saved
jobs. Its current resource is `ui://fm1/device-panel-v4.html`; the v1/v2/v3
aliases serve the same current UI. A cached tool title may remain older.
Read the dated verification record for the currently attached session and
hardware acceptance; saved inventory does not prove current physical state.
The app and panel icon use an original black/mint
FM-1 silhouette based on the physical front-panel arrangement.

Start with the [user guide](docs/USER_GUIDE.md) for plugin installation, browsing
the connected metadata panel, planning, saved-job recovery, and progress interpretation.

`ChatGPT/Codex → private Site Worker → D1 queue ← outbound Windows relay → existing FM1 bridge → established protected session → FM1`

## Source layout

- `tools/jieli-wl82/remote_store.html`: app library, package selection, write confirmation, and job progress.
- `remote_bridge.py`: loopback HTTP service, authenticated fixed operations, durable jobs, and uncertainty handling.
- `remote_backend.py` and `flash-session-client.ps1`: adapter to an existing protected Windows flashing session.
- `update_mode.py`: passive serial/disk/MIDI classification without opening an endpoint or transmitting SysEx.
- `remote_catalog.py`: immutable private package validation and device-baseline matching.
- `remote_client.py`: CLI with credential origin restrictions and no automatic job resubmission.
- `job_progress.py`: progress from persisted job/session metadata.
- `site/lib/fm1-server.mjs`: authenticated MCP, user-owned requests, relay routes, and expiring app-switch approvals.
- `site/lib/fm1-ui.mjs`: MCP App host bridge and top-level WebMCP library interface.
- `site/lib/fm1-app-host.mjs`: native panel integration with the pinned MCP Apps SDK.
- `site/lib/fm1-contract.mjs`: narrow tool schemas, extension metadata, and metadata projection.
- `site/db/schema.ts` and `site/drizzle/`: durable D1 queue and approval schema.
- `site_relay.py` and `start-site-relay.ps1`: outbound client, private local journal, and hidden unelevated launcher.
- `docs/SITE_RELAY.md`: relay credentials, launch prerequisites, and recovery contract.
- `docs/INTEGRATION_HANDOFF.md`: architecture, current implementation, and acceptance boundaries.
- `docs/REMOTE_DEBUG_REFERENCE.md`: remote-debug setup reference maintained with the setup chat.
- `source-snapshot.json`: historical hashes and provenance for the initial imported source.

The initial snapshot came from the active `progress-kit/fm1-remote` source on
the Windows bench. Its manifest records that import rather than the later
integration changes. Private packages, ROMs, songs, firmware images,
credentials, session descriptors, job receipts, bundled Python, and vendor
USB tooling are excluded.

## Offline verification

Use Python 3.11 or newer and a Node.js runtime with `node:test`. The tests use synthetic data, temporary directories, mocked subprocesses, and loopback HTTP. They do not open the FM1 device.

```powershell
python -m unittest discover -s tools/jieli-wl82 -p 'test_*.py'
node --test tools/jieli-wl82/test_remote_store.cjs
```

The current checks passed **189 Python tests**, **62 focused relay tests**,
**10 browser-store JavaScript tests**, and **69 Site tests**: 40 server, 25 UI,
and 4 SDK tests. See [VERIFICATION.md](docs/VERIFICATION.md) for the dated
results, PowerShell checks, and live validation receipts.
The Python suite includes relay validation, durable
same-ID recovery, switch digest/expiry checks, credential filtering, and the
offline exception fix: failed planning no longer creates an unknown device
outcome that blocks later device operations.

Site typechecking and the v4 production build passed. Actual SDK Client 2.3.1
negotiated modern `2026-07-28` and legacy `2025-11-25` protocols in memory.
An earlier direct deployed client probe returned HTTP 401 and did not establish
remote modern-protocol acceptance. The seven WebMCP tool contracts are covered
by the Site tests; the earlier six-tool release was also checked in a supported
browser against a synthetic HTTP relay. See [WEBMCP.md](docs/WEBMCP.md).

## Local operation

The bridge binds to `127.0.0.1:9770`. The store and `/v1/` API share the same origin. The store token is held in page memory; every data/operation request requires authentication.

Windows device operations require a separately prepared, verified protected flashing session and its reviewed USB dependencies. This repository includes the pipe client, but does not create that session, install Python, supply firmware, or supply the vendor loader. Use the established bench workflow for those prerequisites.

Do not start a duplicate bridge over an existing listener or redirect its state folder to this repository. Preserve the existing job state and unknown-outcome latch. Tailscale Serve can provide private HTTPS for the same-origin store. See the remote-debug reference before changing a running setup.

## Site and plugin operation

The Site offers catalog and inventory refresh, offline app plans, saved
request/job inspection, automatic app-switch review, and official SysEx updater
review. The latter opens the pinned manufacturer's tool for an official `.fwsc`
package; it does not report a completed update from a GUI launch. The MCP panel uses server tools
through its host bridge. The full website separately feature-detects
`document.modelContext.registerTool`; normal library controls remain available
when WebMCP is unavailable. The panel does not embed the loopback store.

The hosted server receives sanitized metadata through an outbound relay; it
does not directly reach laptop loopback or provide USB access by itself.
Relay setup requires distinct private Site relay and platform service
credentials plus the existing local bridge token. See
[SITE_RELAY.md](docs/SITE_RELAY.md) before preparing or starting it. Starting a
relay process does not verify a hosted connection or authorize a device write.

App switching is disabled by default on the relay. An enabled bench capability
still requires explicit human confirmation of an expiring one-use approval
bound to the signed-in user, catalog ID, package digest, and entry method.
The relay checks the digest and expiry before submitting to the existing
protected writer. Transport delivery and bridge job outcome remain distinct:
a delivered response can contain a failed or unknown job, and interrupted
submissions are inspected by their saved ID without resubmission.

The installed plugin, updated native panel, and metadata relay have live
acceptance. The panel preserves the original job ID across metadata refresh
and a lost confirmation reply; inspect that exact ID before any further
operation. Relay metadata is bounded to 58,000 serialized bytes, with durable
receipt recovery for proven oversize rejections. Device writes and
physical screen/audio/control acceptance require
the established bench prerequisites and an explicitly confirmed operation.
