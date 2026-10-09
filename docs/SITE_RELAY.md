# Private Site bench relay

`tools/jieli-wl82/site_relay.py` is a Python 3.11+ standard-library client. It
polls the private hosted Site using outbound HTTPS and forwards a small set of
operations to the existing authenticated bridge. It imports no USB/serial
backend and does not start, restart, configure, or replace the bridge or its
protected writer session. The installed plugin, cached native v1 panel,
website, and live relay have passed metadata round trips. After Site version 2
deployment, cached-panel Refresh and saved-job inspection still worked through
the new server. Rendering the new native v2 resource remains unverified.
Protected-session preparation,
device operations, and physical acceptance remain separate bench work.

## Verified metadata setup on 2026-10-09

The supported local bridge was launched on loopback port 9770 without a
`SessionRoot` or official updater; the observed process ID was 134988. The
outbound relay's observed process ID was 411680, with switching disabled.
These are dated observations, not permanent process identities. Inspect the
current listener/process before any future launch and do not start duplicates.

Inventory reported COM4 and CDC/audio interfaces. Six validated private
packages were listed, all with `ready:false`. The missing protected session
and verified baseline intentionally keep device switching unavailable.
Installed plugin status/catalog/job calls, native-panel Refresh, and live
Site WebMCP Refresh worked through this relay.

The MDX plan request/bridge job `d984e14543204d1e93a966099cc708d7` had delivery
`succeeded` and authoritative bridge status `failed`, with the prerequisite
message **Start a protected session on the laptop first**. Saved-job inspection
used delivery request `68060f826e704d2d8075321d4461577d`. No device I/O or
protected-helper creation occurred. The older snapshot worker is stopped and
lacks the required remote-read guard; it must not be reactivated as a shortcut.
The remote laptop is offline, so its earlier protected setup is not current
local session evidence.

## Authentication and origins

Three distinct credentials are required. Supply them through private token
files with the corresponding CLI option, or through these process environment
variables:

| Credential | Environment variable | File option | Destination |
|---|---|---|---|
| Site relay token | `FM1_RELAY_TOKEN` | `--relay-token-file` | Site `Authorization: Bearer …` |
| Sites platform service credential | `FM1_SITES_SERVICE_TOKEN` | `--sites-token-file` | Site `OAI-Sites-Authorization: Bearer …` |
| Existing bridge token | `FM1_BRIDGE_TOKEN` | `--bridge-token-file` | Bridge `Authorization: Bearer …` |

Tokens must have at least 32 printable ASCII characters without spaces. File
options take precedence over their environment variable. No token is generated,
printed, stored in relay journal/results, or sent to the other endpoint.
Private files must have restricted access; the Windows launcher checks their
ACLs without changing the existing bridge token file. Do not paste credentials
into a chat, repository, launch argument, Site response, or public artifact.

`--site-url` is the exact HTTPS origin, without a path, query, fragment, or URL
credentials. The bridge defaults to `http://127.0.0.1:9770`. Other HTTP bridge
origins must use a literal loopback IP address; `localhost` and LAN IP addresses
are rejected. An explicitly configured remote bridge origin must use HTTPS and
a `.ts.net` hostname. TLS certificate verification remains enabled. Redirects
and environment HTTP proxies are rejected so credentials stay on the pinned
origin. A response must be JSON and at most 256 KiB; duplicate JSON keys and
nonfinite numbers are rejected.

## Local launch

Keep using the bench owner's existing bridge and protected-session setup.
Provision the Site relay token and platform service credential separately,
then set the three environment variables locally or supply private file paths.
No live values are included in this repository. From PowerShell:

```powershell
& .\tools\jieli-wl82\start-site-relay.ps1 -SiteUrl 'https://your-private-site.example' -PrepareOnly
& .\tools\jieli-wl82\start-site-relay.ps1 -SiteUrl 'https://your-private-site.example'
```

The launcher uses a hidden, unelevated process and dedicated restricted state
under `$env:LOCALAPPDATA\FM1SiteRelay`. `-StateRoot` may select a subdirectory
beneath that directory. It rejects reparse points and existing live relay PIDs,
creates no credentials, and never touches the existing bridge state or helper.
`-PrepareOnly` validates local prerequisites and prepares only relay state; it
makes no HTTP request. A successfully started process is not proof of an
authenticated Site connection; verify that connection on the Site.

App switching is disabled by default. `-AllowSwitch` (Python `--allow-switch`)
is a deliberate local enable flag, in addition to the hosted Site's explicit
human confirmation flow. An enabled relay submits only the confirmed catalog
ID and exact `serial` or `already_uboot` entry method, after checking the approved
package SHA-256 against current catalog metadata and the approval's expiry.
Catalog IDs are immutable in the existing bridge: a different package requires
a new ID. Do not enable switching
until the bench owner has verified the current protected session and physical
conditions. Stop this relay locally by its recorded PID when it is no longer
needed; this does not stop the bridge.

For one diagnostic poll cycle, Python supports `--once` with the same origin,
state, and credential options. The continuous loop defaults to a three-second
poll interval. Logs contain fixed error labels only, never task results or
HTTP/backend exception text.

## Wire contract and operation boundaries

All Site calls carry both Site credentials. `POST /relay/heartbeat` receives
`{"allow_switch":false}` by default. `POST /relay/poll` receives `{}` and returns
`{"tasks":[…],"connected":true}`. A task has exactly `id`, `operation`, and
`arguments`; IDs are 32 lowercase hexadecimal characters.

| Task operation | Arguments | Fixed bridge request |
|---|---|---|
| `status` | `{}` | `GET /v1/status` |
| `catalog` | `{}` | `GET /v1/catalog` |
| `job` | `{job_id}` | `GET /v1/jobs/<job_id>` |
| `plan_app` | `{catalog_id}` | `POST /v1/jobs` with the task's own ID |
| `switch_app` | `{catalog_id,entry_method,expected_sha256,approval_expires}` | Recheck `GET /v1/catalog`, then `POST /v1/jobs` with the task's own ID, only when locally enabled |

No caller can select a URL, raw path, shell command, reset, read-firmware action,
binary upload/download, catalog installation, or arbitrary bridge operation.
Inventory reads do not submit `serial_status` or acquire a device handle.
Catalog IDs are lowercase slugs of at most 64 characters. The Site owns human
authorization; the relay owns transport validation, local enablement, and
durable submission recovery. `expected_sha256` is 64 lowercase hexadecimal
characters; `approval_expires` is an integer UNIX timestamp in seconds. They
are persisted in the relay journal and verified immediately before submission,
but never forwarded as unexpected fields to the strict bridge API. Missing,
changed, ambiguous, or unready catalog variants fail before any submission.

The relay posts `/relay/result` with the exact task ID and a terminal delivery
status: `succeeded`, `failed`, or `unknown`. Valid bridge `{ok:true,data:X}`
envelopes are unwrapped and reported as delivery `succeeded`. `X.status`,
including `queued`, `running`, `failed`, and `unknown`, is the authoritative
bridge job outcome and must be displayed separately. A delivery success never
means a firmware write, readback, startup, or physical acceptance succeeded.
Definite HTTP rejection is delivery `failed` with a fixed error label.

Results are metadata only. Recursive projection removes image/firmware payload
fields, credentials, paths, private session descriptors, binary values, long
encoded material, and strings containing configured secrets. Safe session
readiness flags, bridge blocked/unknown state, hashes, and progress remain.
Physical unit identifiers such as serial numbers and PnP device identifiers
are filtered recursively, including case and snake-case variants. Port,
VID/PID, description/model, and safe readiness flags remain available.
Detailed diagnostics and all firmware/ROM/music bytes stay on the laptop.

## Durability and uncertainty

An OS-held lock allows one process per relay state directory. Every validated
poll batch is journaled in full before any task executes. A task record moves
from `prepared` to `executing` before the bridge request, then to `completed`
only after its sanitized result is committed atomically. Repeated IDs replay
the saved result; a repeated ID with different arguments is rejected. A lost
Site result acknowledgment is retried with the identical saved result. The
result is marked reported only for an exact `{"saved":true}` acknowledgment.

If a bridge job submission loses its response, the relay only queries
`GET /v1/jobs/<saved-task-id>`. It does not resubmit, create a new ID, clear an
unknown latch, or infer success. On restart an `executing` plan/switch task is
recovered through the same GET-only path even when switching is now disabled
or the original approval has expired. A `prepared` switch whose approval has
expired fails without submission, including after a relay restart.
If no definite saved job can be obtained, delivery is `unknown` with
`bridge_outcome_unknown`. Inspect the local bridge and protected session before
initiating any new device operation. Restarted metadata GET tasks may safely
be read again. Corrupt journal state blocks startup; deleting a journal to
force retries defeats this safety property and is not a recovery procedure.

## Offline validation

```powershell
Push-Location .\tools\jieli-wl82
python -m unittest test_site_relay -v
Pop-Location
```

Tests use synthetic state, fake Site/bridge clients, and a temporary loopback
HTTP server. They cover strict task/origin validation, separate credentials,
redirect rejection, JSON bounds, sensitive result filtering, switch gating,
duplicate task and process exclusion, interrupted submission/restart recovery,
batch persistence, and lost Site acknowledgments. They neither connect to the
actual Site nor start any device operation.

The latest focused relay run passed **39 tests**, including recursive physical
identifier filtering in results and the journal. The earlier aggregate Python
run contained 136 tests and 37 relay tests; that aggregate was not rerun after
the two new identifier regressions. See [VERIFICATION.md](VERIFICATION.md) for
current live metadata evidence, the accepted v2 SDK tests/build/deployment,
and the remaining native v2 panel/remote modern-protocol checks.
