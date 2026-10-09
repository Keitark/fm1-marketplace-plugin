# Integration verification

The checks below were recorded on 2026-10-09 using Python 3.11.0 and
Node.js v22.22.2 on Windows. The original aggregate offline run, later focused
relay regression run, accepted v2 server deployment, cached native v1 panel,
and unaccepted native v2 rendering are separate evidence levels.
Offline checks started no live bridge,
relay, protected helper, USB device, or tunnel.

| Check | Result |
|---|---|
| Earlier `python -m unittest discover -s tools/jieli-wl82 -p 'test_*.py'` | 136 tests passed in 35.679 seconds; historical aggregate, not rerun after the two new relay regressions |
| Latest focused `python -m unittest test_site_relay` from `tools/jieli-wl82/` | 39 tests passed in 4.824 seconds, including physical-identifier filtering |
| `node --test tools/jieli-wl82/test_remote_store.cjs` | 10 tests passed |
| PowerShell syntax parsing | All 3 scripts passed: `flash-session-client.ps1`, `start-remote-bridge.ps1`, and `start-site-relay.ps1` |
| Current `node --test site/test/*.test.mjs` | 41 tests passed: 25 server/SQLite, 12 UI, and 4 SDK tests |
| Current `node node_modules/typescript/bin/tsc --noEmit` from `site/` | Passed for the v2 SDK implementation |
| Current production build via installed npm CLI and `npm run build` | Passed; v2 Cloudflare Worker output generated |
| Actual SDK Client 2.3.1 in-memory transport | Modern `2026-07-28` and legacy `2025-11-25` negotiation passed |
| Earlier synthetic browser UI verification | Passed in Codex in-app browser against a local synthetic HTTP relay; historical disconnected screenshot below |
| Private Sites deployment | Version 2 succeeded, runtime revision 1; MCP-ready |
| Installed hosted plugin tools | Earlier library/open, status, catalog, and saved-job calls succeeded; cached v1 panel calls also work through the v2 server |
| Actual native MCP App iframe | Cached v1 Refresh and saved-job inspection succeeded after v2 deployment; rendering the new v2 resource remains pending |
| Top-level WebMCP | All 6 tools passed earlier valid/malformed synthetic cases; live Site Refresh succeeded through the metadata relay |
| Authenticated live bench relay round trip | Passed for inventory, catalog, plan prerequisite failure, and saved-job inspection; switching disabled |
| Pinned official server SDK 2.3.1 + ext-apps 2.0.3 | Local tests/typecheck/build and v2 deployment passed; native v2 Apps SDK host acceptance remains pending |
| Direct deployed SDK Client probe with existing relay service credential | HTTP 401; remote modern-protocol negotiation was not accepted by this probe |
| Hardware write/readback/startup and physical acceptance | Pending; no protected session/helper or physical I/O was used |

Tests use mocked device operations, synthetic data, temporary state, and
loopback HTTP. The historical 136-test aggregate included 37 outbound relay
tests plus the bridge, backend, client, and progress tests. The latest focused
relay run passed 39 tests after adding two identifier privacy regressions; no
new aggregate total is claimed. They verify strict task/origin
validation, distinct credentials, redirect and oversized/nonfinite JSON
rejection, metadata filtering, per-state process exclusion, durable task/batch
journaling, duplicate result handling, lost submission/result recovery, and
switch enablement/digest/expiry checks. An interrupted plan/switch uses only
the original bridge job ID on recovery; it never repeats the submission.

Bridge regression coverage verifies that exceptions in offline `plan`,
`plan_app`, and `environment` requests produce `failed`, including restart
handling, while uncertain device operations retain `unknown` and their
persistent device-operation block. Transport success does not replace an
authoritative bridge job's failed/unknown status.

The 10 local-store JavaScript tests verify accessible progress, authoritative
job outcome handling, incomplete readback/startup state, and network-loss
polling without resubmission. They are source-contract tests and do not prove
native panel rendering or real WebMCP discovery.

## Historical import evidence

At the original source-snapshot verification, 97 Python tests and 10
local-store JavaScript tests passed, all 14 imported files matched the recorded
hashes/sizes, both copied PowerShell scripts parsed, and the publication scan
found no embedded private inputs or credentials. `source-snapshot.json` is
that historical import record. It is not a current hash manifest for files
changed by this integration.

The protected writer/bootstrap, private packages, and vendor USB dependencies
remain outside this repository. Python bytecode generated during verification
is ignored by Git. Local SDK and deployment acceptance remain distinct from
native v2 host rendering, remote modern-protocol acceptance, and hardware
acceptance.

## Published Site and browser evidence

Owner-private Site: [FM1 App Library](https://fm1-app-library.keitark.chatgpt.site).
The initial successful native deployment was `appgdep_6ac86547ba848191bf7b1e4fb6adb1ce`,
with pushed Site source `599d6ef7a7586a24c14d66181e006603e3415b5c`. The native
connection metadata reports `/mcp` as its HTTP endpoint and OAuth resource.
The plugin was subsequently installed and its open/status/catalog/job tools
were verified. Refresh worked in the actual native MCP App iframe, and live
Site WebMCP Refresh worked through the authenticated metadata relay. These
results were initially recorded before the SDK migration. After v2 deployment,
the cached v1 panel continued to work through the new server, as recorded below. The
website and MCP metadata carry
the original black/mint FM-1 mark as SVG and lossless PNG.

The local browser fixture used `/relay/heartbeat`, `/relay/poll`, and
`/relay/result`, exercising the real Worker/D1 routes without importing a
bridge or device backend. Valid calls displayed synthetic catalog, plan and
saved-job progress. Switch review returned no approval nonce, Cancel closed
the dialog, and a local readback counted zero `switch_app` tasks. The VM tests
separately verify untrusted-click rejection and one-use trusted confirmation.
See [WEBMCP.md](WEBMCP.md) for the exact boundary and repeatable fixture.

The historical local screenshot uses an empty, disconnected database after fixture
cleanup. No test credentials, production relay token, or local mock identity
were embedded in the production Worker. Runtime secrets are held in Sites;
owner-only credential files remain outside Git. No live bench relay was
started during those fixture checks. The subsequent live metadata connection
is recorded separately below.

![Historical disconnected local library with FM-1 icon](images/fm1-library.jpg)

## Verified live metadata connection

The supported local bridge was observed as PID **134988** on loopback port
**9770**, launched without `SessionRoot` or an official updater. The relay was
observed as PID **411680**, with switching disabled. These process IDs are
dated observations; future operations must inspect the actual current process.
Inventory reported COM4 and CDC/audio interfaces. The catalog contained six
validated private packages, all `ready:false` because no verified protected
session/baseline was configured.

The MDX plan request and bridge job
`d984e14543204d1e93a966099cc708d7` had successful delivery and authoritative
bridge status `failed`, with **Start a protected session on the laptop first**.
Saved-job inspection used delivery request
`68060f826e704d2d8075321d4461577d` and confirmed that original outcome. No device
I/O or protected-helper creation occurred. A successful transport result is
not a successful plan or hardware operation.

The older snapshot worker is stopped and lacks the required remote-read
guard. The remote laptop is offline. Neither is current evidence of a usable
local protected session; no frozen helper was replaced or reactivated.

## Version 2 deployment and acceptance boundaries

Version **2** pins official server SDK **2.3.1** and native-panel **ext-apps
2.0.3**. Its **41 tests** (25 server, 12 UI, 4 SDK), type check, and production
build passed. Actual SDK Client 2.3.1 passed in-memory modern **2026-07-28** and
legacy **2025-11-25** protocol negotiation. The earlier 36-test Site result is
historical; the 41-test suite is the current SDK implementation's offline
record. These client tests do not establish remote modern negotiation.

Native deployment `appgdep_6ac8f089484881919b4e10b89ef4f608` succeeded as Site
version **2**, runtime revision **1**, with MCP-ready status. Source SHA:
`5d32bd0c023d4a3d7ef77fb454164844131a29d0`. The new UI resource is
`ui://fm1/device-panel-v2.html`.

After v2 deployment, the cached v1 native panel successfully refreshed
inventory with request `f5384b7e6f9e41e8b29073a3e93daed4` and catalog with
request `7cd30350d95d4cb6b780586043649cf6`. It still reported COM4 and six
blocked packages. Saved-job inspection delivery
`6767e0f9833d4826a480b12210aa09e0` preserved the original bridge job
`d984e14543204d1e93a966099cc708d7` and its `failed` protected-session prerequisite
outcome. No device I/O or protected session/helper creation occurred.

![Cached v1 native panel connected after v2 deployment](images/fm1-native-panel-v1-live.png)

A newly opened native panel still displays **Choose what plays next.** and the
older tool title. This verifies the cached v1 panel against the v2 backend,
not rendering or host SDK acceptance of `ui://fm1/device-panel-v2.html`.
Refreshing cached metadata/resources remains pending. No supported refresh
tool is exposed, and restart/reinstall has not been verified as a fix.

A direct deployed SDK Client probe using the existing relay service credential
returned **HTTP 401**. It did not establish modern remote protocol negotiation.
No raw secrets or private physical identifiers were persisted. Physical
write/readback/startup, screen, audio, and controls remain unaccepted.
