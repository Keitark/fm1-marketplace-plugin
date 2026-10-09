# Integration verification

The final independent bridge/relay offline checks below ran on 2026-10-09
using Python 3.11.0 and Node.js v22.22.2 on Windows. No live bridge, relay, protected helper,
USB device, or tunnel was started for these checks.

| Check | Result |
|---|---|
| `python -m unittest discover -s tools/jieli-wl82 -p 'test_*.py'` | 136 tests passed in 35.679 seconds |
| `node --test tools/jieli-wl82/test_remote_store.cjs` | 10 tests passed |
| PowerShell syntax parsing | All 3 scripts passed: `flash-session-client.ps1`, `start-remote-bridge.ps1`, and `start-site-relay.ps1` |
| `node --test site/test/*.test.mjs` | 36 tests passed: 25 server/SQLite and 11 UI lifecycle/approval tests |
| `node node_modules/typescript/bin/tsc --noEmit` from `site/` | Passed |
| Production build via installed npm CLI and `npm run build` | Passed; Cloudflare Worker output generated |
| Browser UI verification | Passed in Codex in-app browser against local synthetic HTTP relay; disconnected final screenshot below |
| Private Sites deployment | Succeeded, version 1, runtime revision 1; MCP-ready |
| Hosted MCP/plugin connection and native entrypoints | Endpoint and plugin provisioned; user installation/connection and native rendering are not confirmed |
| Top-level WebMCP discovery | All 6 tools discovered; all 6 valid and malformed cases verified in supported browser |
| Authenticated live bench relay round trip | Pending; no live relay activation during offline checks |
| Hardware write/readback/startup and physical acceptance | Pending; requires an available FM1 and the established bench workflow |

Tests use mocked device operations, synthetic data, temporary state, and
loopback HTTP. The 136 Python tests include 37 outbound relay tests plus the
bridge, backend, client, and progress tests. They verify strict task/origin
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
is ignored by Git. Replace the pending Site/build/browser rows with exact
commands and observed results after completing those checks;
offline source acceptance remains distinct from native host rendering and hardware acceptance.

## Published Site and browser evidence

Owner-private Site: [FM1 App Library](https://fm1-app-library.keitark.chatgpt.site).
The successful native deployment was `appgdep_6ac86547ba848191bf7b1e4fb6adb1ce`,
with pushed Site source `599d6ef7a7586a24c14d66181e006603e3415b5c`. The native
connection metadata reports `/mcp` as its HTTP endpoint and OAuth resource.
The generated plugin has been offered for installation; offering it is not
proof that it is installed or connected. The Website and MCP metadata carry
the original black/mint FM-1 mark as SVG and lossless PNG.

The local browser fixture used `/relay/heartbeat`, `/relay/poll`, and
`/relay/result`, exercising the real Worker/D1 routes without importing a
bridge or device backend. Valid calls displayed synthetic catalog, plan and
saved-job progress. Switch review returned no approval nonce, Cancel closed
the dialog, and a local readback counted zero `switch_app` tasks. The VM tests
separately verify untrusted-click rejection and one-use trusted confirmation.
See [WEBMCP.md](WEBMCP.md) for the exact boundary and repeatable fixture.

The final local screenshot uses an empty, disconnected database after fixture
cleanup. No test credentials, production relay token, or local mock identity
were embedded in the production Worker. Runtime secrets are held in Sites;
owner-only credential files remain outside Git. No live bench relay was started.

![Disconnected local library with FM-1 icon](images/fm1-library.jpg)
