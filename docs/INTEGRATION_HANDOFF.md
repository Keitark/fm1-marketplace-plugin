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

At the recorded 2026-10-09 metadata check, the local bridge had no configured
protected session or official updater. Inventory reported COM4 and CDC/audio interfaces, and six validated
private packages all remained `ready:false`. An MDX plan reached the bridge
but correctly failed on the protected-session prerequisite. No helper was
created and no device I/O, firmware write, or physical acceptance occurred.
The browser's six WebMCP tools also passed earlier synthetic execution and
invalid-input checks.

## Current SDK deployment and native panel

Site version **3** pins official server SDK **2.3.1** and **ext-apps 2.0.3**.
The current Site suite passed **45 tests** (26 server, 15 UI, 4 SDK), typechecking
and the production build passed, and deployment
`appgdep_6ac8fc0660648191a2521acd37271e3c` succeeded with runtime revision 1
and MCP-ready status. Its source SHA is
`0e76fa6923d74ca96f71312a77d033b4c4935723`. Actual SDK Client 2.3.1 negotiated
current **2026-07-28** and legacy **2025-11-25** protocols in memory.

The current native Codex panel renders the black/mint **FM1 plugin** interface
with **FM1 on COM4**. Its current descriptor points to
`ui://fm1/device-panel-v3.html`; the v1 and v2 resource URLs also serve the
current UI, preserving older installed registrations. A read-only Codex
app-server metadata refresh reported the installed app callable and its new
**FM1 device panel** tool title. Compatibility resource reads resolved the
previous stale native UI without reinstalling the plugin. The existing
panel-tab title can still reflect its earlier registration.

A direct deployed SDK Client probe using the existing
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
| App switching | `POST /v1/jobs`, `switch_app` | Approved `auto`, `serial` or `already_uboot` entry, package digest and protected writer checks. |
| Official firmware | `POST /v1/jobs`, `official_updater` | Separate human approval and local enable flag; exact updater executable digest; fixed vendor GUI handoff. |

Relay switching is disabled by default. Enabling its local capability is a
deliberate bench configuration step, not permission for a particular write.
The Site stages a review without submitting a write. Human confirmation consumes
an expiring, one-use approval bound to the signed-in user, catalog ID, package
digest and entry method; queue insertion and approval consumption are atomic.
The approval ID becomes the durable bridge job ID. The confirmation tool is
app-visible rather than a model-visible shortcut. The local bridge still has
no per-write consent field; the adapter owns this approval boundary.

Official handoff has its own disabled-by-default local
`-AllowOfficialUpdate`/`--allow-official-update` capability and expiring one-use
approval bound to the reviewed updater SHA-256. Its strict bridge request has
only `id`, `operation` and `expected_sha256`; paths, commands, arguments and
firmware payloads cannot be supplied remotely. The backend rechecks the pinned
updater and fresh mode before GUI launch; the relay preserves the same ID on uncertainty.

Passive inventory chooses one protected CDC or UBOOT route for `auto`; exact
stock/OTA MIDI names select the official GUI route. Inventory errors, duplicate
or conflicting candidates, incomplete MIDI pairs and changed mode prevent
automatic selection. WinMM capability queries open no MIDI endpoint. MIDI
names establish a routing candidate, not unique-unit provenance. The selected
custom app still uses the existing protected writer and catalog digest.

The generic manufacturer M-UPGRADE GUI accepts official `.fwsc` selection;
the operator completes that flow locally. Preserve its full Qt dependency
directory. The older FM1-specific GUI embeds V14; the separately published
official package is V15. See the [manufacturer downloads and instructions](https://www.m-vave.com/download).
The adapter does not implement a direct SysEx sender or convert app bundles to
`.fwsc`. A saved successful GUI handoff reports `written_verified:false` and
persistently blocks device jobs. After official completion, establish a fresh
protected session and verified current-unit baseline; retain prior evidence.

Auto routing and official handoff are implementation capabilities with offline
coverage. Hosted deployment, actual GUI operation, readback and physical
screen/audio/control acceptance require their own dated evidence. The earlier
metadata acceptance above does not establish those results.

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
The native panel retains the original job ID across metadata refresh and
inspection. It saves the approval/job ID before confirmation; a lost reply
directs the user to inspect that ID rather than submit another switch.

Relay metadata is bounded to 58,000 encoded bytes to leave room beneath the
Site's request/result limits. Legacy completed receipts replay unchanged until
an explicit size rejection proves they were not accepted. Only HTTP 413 or
local `request_too_large` permits compaction, which is persisted before retry.
Timeouts and immutable-result conflicts never replace a receipt or repeat a
bridge submission. The larger existing bridge/journal limits remain intact.
Unknown device outcomes retain the bridge's persistent block and require local
inspection. Offline backend exceptions now produce `failed`, so a failed
`plan_app`, `plan` or `environment` request does not create device uncertainty.

Metadata rollout now uses the supported local bridge on loopback port 9770
(observed PID 134988) and updated relay (observed PID 422648), with switching disabled.
These process IDs are dated evidence, not future launch configuration. The
relay never launches or restarts the bridge or replaces its state.
Do not substitute a new state directory, clear latches or change a frozen helper
to bring the Site online. Inspect live launcher/session selection before any
operational change. The older protected snapshot worker is stopped and lacks
the required remote-read guard, and the remote laptop is offline. Do not
reactivate that worker or infer that its historical session is usable locally.

The saved MDX plan request/job `d984e14543204d1e93a966099cc708d7` was delivered
successfully but has authoritative status `failed` with **Start a protected
session on the laptop first**. Current native inspection request
`2e5b770a13ed49c69ba90f18bdca17ea` verified the original saved job. It used no
device I/O. This is current evidence of transport and prerequisite handling,
not successful planning or device acceptance.

Before device operations, establish an idle verified protected session and
unit-specific baseline through the bench workflow. Separately accept any
explicitly authorized hardware operation and physical screen/audio/control behavior.

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
