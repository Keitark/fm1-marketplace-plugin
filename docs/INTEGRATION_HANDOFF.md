# FM1 Codex integration handoff

## Current implementation and acceptance

This repository now includes the FM1 Site adapter, MCP App panel, top-level
WebMCP tools and outbound Windows relay alongside the original store/bridge
source. The initial publication at `b024784` established the source foundation;
the integration extends that work rather than replacing the protected writer.
The owner-private [FM1 App Library](https://fm1-app-library.keitark.chatgpt.site)
is deployed and MCP-ready. The plugin is installed: library, status, catalog,
and saved-job tools have succeeded. Refresh worked in the actual native MCP
App iframe, and live Site WebMCP Refresh worked through the authenticated
local relay. The native plugin/panel is the user's selected primary interface;
it does not require a Chrome extension.

The local bridge currently has no configured protected session or official
updater. Inventory reported COM4 and CDC/audio interfaces, and six validated
private packages all remained `ready:false`. An MDX plan reached the bridge
but correctly failed on the protected-session prerequisite. No helper was
created and no device I/O, firmware write, or physical acceptance occurred.
The browser's six WebMCP tools also passed earlier synthetic execution and
invalid-input checks.

## SDK deployment and remaining native-panel acceptance

Site version **2** pins official server SDK **2.3.1** and **ext-apps 2.0.3**.
The current Site suite passed **41 tests** (25 server, 12 UI, 4 SDK), typechecking
and the production build passed, and deployment
`appgdep_6ac8f089484881919b4e10b89ef4f608` succeeded with runtime revision 1
and MCP-ready status. Its source SHA is
`5d32bd0c023d4a3d7ef77fb454164844131a29d0`. Actual SDK Client 2.3.1 negotiated
current **2026-07-28** and legacy **2025-11-25** protocols in memory.

After deployment, the cached native v1 panel successfully refreshed status
and catalog and inspected the original failed MDX job through the v2 server.
A newly opened native panel still shows **Choose what plays next.** and the
older tool title. Rendering `ui://fm1/device-panel-v2.html` through the host
and acceptance of its Apps SDK remain pending cached metadata/resource
refresh. No supported refresh tool is exposed, and restart/reinstall has not
been verified as a fix. A direct deployed SDK Client probe using the existing
relay service credential returned **HTTP 401**, so modern remote protocol
negotiation is not accepted by that check. See [VERIFICATION.md](VERIFICATION.md)
for the exact evidence and remaining boundaries.

## Architecture

`ChatGPT/Codex -> private Site Worker -> durable D1 queue <- outbound Windows relay -> existing loopback FM1 bridge -> established protected session -> FM1`

- The Site Worker handles HTTP MCP at `/mcp`, including tool discovery and MCP
  UI resources. The app library advertises global and thread entrypoints. Its
  panel uses the MCP App host bridge; the full website separately feature-detects
  `document.modelContext.registerTool` and offers WebMCP in the top-level page.
  The ordinary library controls remain available when WebMCP is unavailable.
- D1 holds user-owned requests, delivery outcomes and expiring approvals. The
  relay polls outbound; the hosted server does not connect directly to laptop
  loopback or assume private-tailnet reachability.
- The relay authenticates to the private Site with a Sites service token
  (`OAI-Sites-Authorization`) and a separate scoped relay bearer token. The
  existing bridge bearer credential stays on the Windows side. These are
  distinct credentials; none belongs in catalog data, tool results or browser
  storage.
- The local store remains same-origin with its HTTP API and retains
  `frame-ancestors 'none'`. The native panel serves its own UI resource instead
  of embedding that loopback page.

## Operations and approval

| Capability | Local API reused | Boundary |
|---|---|---|
| Inventory and writer state | `GET /v1/status` | Inventory/persisted state; preserve blocked and unknown outcomes. |
| App library | `GET /v1/catalog` | Variant metadata, digest and baseline readiness; no firmware bytes. |
| Offline plan | `POST /v1/jobs`, `plan_app` | Existing catalog ID and verified baseline; no device I/O. |
| Saved job inspection | `GET /v1/jobs/<id>` | Resume the original ID without resubmission. |
| App switching | `POST /v1/jobs`, `switch_app` | Explicit entry method, reviewed approval and protected writer checks. |

Relay switching is disabled by default. Enabling its local capability is a
deliberate bench configuration step, not permission for a particular write.
The Site stages a review without submitting a write. Human confirmation consumes
an expiring, one-use approval bound to the signed-in user, catalog ID, package
digest and entry method; queue insertion and approval consumption are atomic.
The approval ID becomes the durable bridge job ID. The confirmation tool is
app-visible rather than a model-visible shortcut. The local bridge still has
no per-write consent field; the adapter owns this approval boundary.

Only metadata crosses the relay. Keep private catalog bundle JSON, firmware,
ROM/music inputs, baseline images, session descriptors, receipts, device paths
and tokens local. Low-level recovery/helper management remains a bench operation.
Serial numbers, PnP unit identifiers, and related physical identity fields are
also filtered before Site results and local relay result journals are saved.
`serial_status` and `read_firmware` are device operations, not passive metadata
reads; firmware read setup can alter loader/protection state.

## Durable outcomes and deployment boundaries

Requests are saved before delivery and journaled locally before bridge
submission. A lost POST response is inspected using its existing ID; it is not
replaced by a new write request. Delivery state and authoritative bridge job
status are separate: successful transport can return a failed or unknown job.
Preserve the saved outcome and verified progress even after a transport failure.
Unknown device outcomes retain the bridge's persistent block and require local
inspection. Offline backend exceptions now produce `failed`, so a failed
`plan_app`, `plan` or `environment` request does not create device uncertainty.

Metadata rollout now uses the supported local bridge on loopback port 9770
(observed PID 134988) and relay (observed PID 411680), with switching disabled.
These process IDs are dated evidence, not future launch configuration. The
relay never launches or restarts the bridge or replaces its state.
Do not substitute a new state directory, clear latches or change a frozen helper
to bring the Site online. Inspect live launcher/session selection before any
operational change. The older protected snapshot worker is stopped and lacks
the required remote-read guard, and the remote laptop is offline. Do not
reactivate that worker or infer that its historical session is usable locally.

The saved MDX plan request/job `d984e14543204d1e93a966099cc708d7` was delivered
successfully but has authoritative status `failed` with **Start a protected
session on the laptop first**. Inspection request
`68060f826e704d2d8075321d4461577d` verified the original saved job. It used no
device I/O. This is current evidence of transport and prerequisite handling,
not successful planning or device acceptance.

Before device operations, establish an idle verified protected session and
unit-specific baseline through the bench workflow. Separately accept the
new v2 resource's host behavior, any explicitly authorized hardware
operation, and physical screen/audio/control behavior.

## Provenance and ownership

The initial snapshot imported the active `progress-kit/fm1-remote` store/bridge
source. `source-snapshot.json` remains its historical import record, not a hash
manifest for the subsequently modified implementation. Existing Git history
preserves that source closure. [VERIFICATION.md](VERIFICATION.md) records current
checks; [REMOTE_DEBUG_REFERENCE.md](REMOTE_DEBUG_REFERENCE.md) describes the bench
contract.

The **Set up remote debug kit** chat retains ownership of live bench setup and
private assets. Coordinate operational changes with that owner. The protected
helper, verified unit-specific baseline, vendor USB dependencies and physical
screen/audio/control acceptance remain external prerequisites. This integration
does not install or replace those assets.
