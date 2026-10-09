# FM1 Codex integration handoff

## Current implementation and acceptance

This repository now includes the FM1 Site adapter, MCP App panel, top-level
WebMCP tools and outbound Windows relay alongside the original store/bridge
source. The initial publication at `b024784` established the source foundation;
the integration extends that work rather than replacing the protected writer.
The owner-private [FM1 App Library](https://fm1-app-library.keitark.chatgpt.site)
is deployed and MCP-ready. The provisioned plugin has been offered for installation;
user connection and native panel rendering are unconfirmed. No FM1 is currently
available, so the live bench relay and physical acceptance remain pending.
The supported browser's six WebMCP tools passed synthetic execution and invalid-input
checks. Local tests/builds do not prove a device write.

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

Rollout requires an idle, established bridge and an existing verified protected
session. The relay never launches or restarts the bridge or replaces its state.
Do not substitute a new state directory, clear latches or change a frozen helper
to bring the Site online. Inspect live launcher/session selection before any
operational change. Verify the privately deployed MCP connection and a read-only
relay round trip before separately accepting native entrypoints, WebMCP discovery
and any explicitly authorized hardware operation.

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
