# Private Site bench relay

`tools/jieli-wl82/site_relay.py` is a Python 3.11+ standard-library client. It
polls the private hosted Site using outbound HTTPS and forwards a small set of
operations to the existing authenticated bridge. It imports no USB/serial
backend and does not start, restart, configure, or replace the bridge or its
protected writer session. The installed plugin, native panel, website, and live
relay have passed metadata round trips. Site version 5 is privately deployed
and MCP-ready, displaying server version 2.1.1 with source
`7c2a46dd4719db0b415a2645db65e5f7b1288a3d`. The current resource is
`ui://fm1/device-panel-v5.html`; v1-v4 aliases serve the same UI for older
installed descriptors. Server SDK 2.3.1 and ext-apps 2.0.3 remain pinned.
Close and reopen an existing panel first. The latest new native panel still
loaded the older cached UI, whose **Refresh** cleared the progress bar
asynchronously. If that UI persists, the plugin connection or resource cache
needs refreshing; native v5 acceptance remains pending an actual cache reload.
The published and tested v5 UI uses bounded, cancellable read-only inspection
of the exact original job. Its **Refresh** updates metadata while preserving
selected progress.

The user-confirmed NES switch job `9067aa03ef7f4826b9f143722cb5635e` completed
on 2026-10-10 at 10:38 JST with 96/96 sectors, full readback and serial startup
verified. Subsequent inventory reported COM10 in normal serial mode and the
protected session idle/unblocked. The
[saved switch response](evidence/fm1-nes-switch-20261010.json) retains that
original job. Physical acceptance remains false, and official MIDI/SysEx
transfer is untested. The protected setup and initial v4 acceptance below are
dated evidence. The v5 release passed 84 Site tests (40 server, 40 UI, 4 SDK),
typechecking and production build. See [VERIFICATION.md](VERIFICATION.md).

## Initial v4 live acceptance (2026-10-10)

Owner-private Site v4 deployment `appgdep_6ac9903cd9e08191b5df920575373d1e`
has MCP enabled and source SHA `bd87d14a039b8ef5233a6b3c60291c3642ee7f98`.
The actual native MCP App panel renders its dark background (`rgb(16,26,24)`)
and **Refresh** works. It shows **FM1 in UBOOT**, six packages ready, switching
**Enabled**, and the pinned official updater as **Needs FM1 MIDI connection**.
The NES switch review showed **auto → already_uboot** and the correct digest;
the review was canceled without submitting a switch.

Native NES **View plan** then succeeded for original bridge job/request
`427b240eda7c4867b403aee8f8838682`; inspection request
`ea27707a4bb04f428aef9d4729b21f1e` and installed `get_fm1_request` confirmed
that original ID. The authoritative job reported `status:succeeded`,
`result.ok:true`, `device_io:false`, `blocked:false` and **96 planned sectors**,
candidate SHA-256
`4d4da3ab34b643034ea91ddb670fd3556b737a05835ed77fced687eae6ad345c`.
Write completion, full readback and boot verification were false. No actual
candidate flash was submitted. The installed tool's structured result is
preserved in the [saved native plan response](evidence/fm1-v4-native-plan-20261010.json).

The current helper is
`C:\Program Files\FM1FlashSession-53b32bdc8a444cdda6c838934831e49c`, recorded
PID **240396**, using the frozen runtime with `trusted_local:false`. Its state
is idle/unblocked with no running loader or pending reset, including after the
offline plan. The verified
baseline is from two matching actual 1 MiB reads, SHA-256
`c719cad560ddcbc05a795cb77e11d65eeb108e1dfdb76afb508d71533437bf1f`;
originals remain under `readback-source`. The adopted baseline's target guard
remains local, and no raw physical identifier is published.

The supported bridge remains on loopback **9770**, now recorded PID **262496**,
with existing state `C:\Users\keita\AppData\Local\FM1RemoteBridge`. The relay
is recorded PID **223876**, with existing state
`C:\Users\keita\AppData\Local\FM1SiteRelay\fm1-app-library`. Both
`-AllowSwitch` and `-AllowOfficialUpdate` were enabled intentionally after
session validation. Existing tokens were retained privately. Process IDs are
dated observations; inspect live state before attempting a restart or launch.

The official updater has its full vendor dependency directory at
`F:\dev\fm1\references\downloads\M-UPGRADE-20261010\M-UPGRADE`; the pinned
`M-UPGRADE.exe` SHA-256 is
`cbda7a95e506cdeefbe39e9718106586147f2ee9857a83e0509644e349591e3b`.
UBOOT currently exposes no official MIDI pair, so vendor handoff/transfer and
physical candidate startup acceptance remain pending. A configured executable
and enabled capability do not establish a ready MIDI route or completed update.

Current checks passed 99 focused runtime tests, 189 integration Python tests,
10 JavaScript tests, 69 Site tests, typechecking, production build and
PowerShell parsing. One absent private profile fixture was excluded from the
runtime scope; broad private writer fixture acceptance is not claimed. See
[VERIFICATION.md](VERIFICATION.md) and the
[native v4 panel screenshot](images/fm1-native-panel-v4-live.png).

## Historical metadata setup (2026-10-09, v3)

At that check, the supported local bridge remained on loopback port 9770 without
a `SessionRoot` or official updater; its recorded PID was **134988**. The relay was
restarted with its existing state and switching disabled; its recorded PID is
**422648**. These are 2026-10-09 observations, not permanent process identities.
See [VERIFICATION.md](VERIFICATION.md) for the dated receipts. Inspect the
current listener/process before any future launch and do not start duplicates.

Inventory reported COM4 and CDC/audio interfaces. Six validated private
packages were listed, all with `ready:false`. The missing protected session
and verified baseline intentionally keep device switching unavailable.
Installed plugin status/catalog/job calls, native-panel Refresh, and live
Site WebMCP Refresh worked through this relay. In the updated v3 native panel,
Refresh succeeded and retained the original job ID. Exact saved-job inspection
also succeeded after the relay restart.

The MDX plan request/bridge job `d984e14543204d1e93a966099cc708d7` had delivery
`succeeded` and authoritative bridge status `failed`, with the prerequisite
message **Start a protected session on the laptop first**. Native saved-job
inspection after the relay restart used delivery request
`2e5b770a13ed49c69ba90f18bdca17ea` and returned that same original job. No device I/O or
protected-helper creation occurred. The older snapshot worker was stopped and
lacked the required remote-read guard; it must not be reactivated as a shortcut.
The remote laptop was offline, so its earlier protected setup was not current
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
ID and exact `auto`, `serial` or `already_uboot` entry method, after checking the approved
package SHA-256 against current catalog metadata and the approval's expiry.
Catalog IDs are immutable in the existing bridge: a different package requires
a new ID. Do not enable switching
until the bench owner has verified the current protected session and physical
conditions. Stop this relay locally by its recorded PID when it is no longer
needed; this does not stop the bridge.

Official updater handoff has a separate disabled-by-default capability:
`-AllowOfficialUpdate` (Python `--allow-official-update`). It submits only a
human-confirmed executable SHA-256. Before launch, the bridge rechecks its
configured updater digest and fresh stock/OTA MIDI mode. The bridge opens its fixed
local M-UPGRADE GUI with the vendor directory as its working directory; no
caller supplies an executable, path, firmware bytes or GUI arguments. The
operator selects the official `.fwsc` and completes the vendor update locally.
Preserve the full downloaded vendor directory, including Qt DLLs and plugin
subdirectories. Configuring only an EXE does not establish its dependency closure.

Auto chooses serial or already-in-UBOOT entry for protected catalog bundles;
official MIDI/SysEx mode uses the separate vendor handoff. Conflicting,
unrecognized or incomplete inventory fails before device submission. Mode
names are routing hints rather than proof of a unique physical unit. This
implementation neither emulates the vendor SysEx writer nor converts custom
bundles to `.fwsc`.

For one diagnostic poll cycle, Python supports `--once` with the same origin,
state, and credential options. The continuous loop defaults to a three-second
poll interval. Logs contain fixed error labels only, never task results or
HTTP/backend exception text.

## Wire contract and operation boundaries

All Site calls carry both Site credentials. `POST /relay/heartbeat` receives
`{"allow_switch":false,"allow_official_update":false}` by default. `POST /relay/poll` receives `{}` and returns
`{"tasks":[…],"connected":true}`. A task has exactly `id`, `operation`, and
`arguments`; IDs are 32 lowercase hexadecimal characters.

| Task operation | Arguments | Fixed bridge request |
|---|---|---|
| `status` | `{}` | `GET /v1/status` |
| `catalog` | `{}` | `GET /v1/catalog` |
| `job` | `{job_id}` | `GET /v1/jobs/<job_id>` |
| `plan_app` | `{catalog_id}` | `POST /v1/jobs` with the task's own ID |
| `switch_app` | `{catalog_id,entry_method,expected_sha256,approval_expires}` | Recheck `GET /v1/catalog`, then `POST /v1/jobs` with the task's own ID, only when locally enabled |
| `official_updater` | `{expected_sha256,approval_expires}` | `POST /v1/jobs` with the task's own ID and reviewed updater digest, only when separately enabled; the backend revalidates before GUI launch |

No caller can select a URL, raw path, shell command, reset, read-firmware action,
binary upload/download, catalog installation, or arbitrary bridge operation.
Inventory reads do not submit `serial_status` or acquire a device handle.
Catalog IDs are lowercase slugs of at most 64 characters. The Site owns human
authorization; the relay owns transport validation, local enablement, and
durable submission recovery. `expected_sha256` is 64 lowercase hexadecimal
characters; `approval_expires` is an integer UNIX timestamp in seconds. They
are persisted in the relay journal and verified immediately before submission.
Switch approval fields remain relay-local; the official handoff forwards only
`expected_sha256` with `id` and `operation` to its strict bridge request.
Missing,
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

New projected metadata is limited to **58,000 serialized bytes**, leaving room
for the Site result and journal envelopes. ASCII-escaped JSON serialization
makes the limit apply to multibyte text too. Oversize metadata is compacted
with `metadata_truncated:true`, retaining bounded identity, outcome, progress,
and safe engine flags. The Site independently enforces a 65,536-byte request
limit before decoding JSON, even when `Content-Length` is absent.

## Durability and uncertainty

An OS-held lock allows one process per relay state directory. Every validated
poll batch is journaled in full before any task executes. A task record moves
from `prepared` to `executing` before the bridge request, then to `completed`
only after its sanitized result is committed atomically. Repeated IDs replay
the saved result; a repeated ID with different arguments is rejected. A lost
Site result acknowledgment is retried with the identical saved result. The
result is marked reported only for an exact `{"saved":true}` acknowledgment.

Completed legacy receipts retain their previous size budget so an already
accepted result can replay identically after an upgrade. Only a definite Site
HTTP **413** or local `request_too_large` rejection permits compaction of an
oversize saved receipt. The replacement is journaled before retrying the Site
result report. A timeout, malformed acknowledgment, or immutable-result
conflict preserves the receipt; none authorizes another bridge job POST.

If a bridge job submission loses its response, the relay only queries
`GET /v1/jobs/<saved-task-id>`. It does not resubmit, create a new ID, clear an
unknown latch, or infer success. On restart an `executing` plan/switch/updater task is
recovered through the same GET-only path even when switching is now disabled
or the original approval has expired. A `prepared` switch or updater handoff
whose approval has expired fails without submission, including after a relay restart.
If no definite saved job can be obtained, delivery is `unknown` with
`bridge_outcome_unknown`. Inspect the local bridge and protected session before
initiating any new device operation. Restarted metadata GET tasks may safely
be read again. Corrupt journal state blocks startup; deleting a journal to
force retries defeats this safety property and is not a recovery procedure.

A successful official handoff is saved as a GUI handoff with
`written_verified:false`; it persistently blocks further bridge device jobs.
After local vendor completion, establish a fresh protected session and verified
current-unit baseline through the bench workflow. Preserve the prior journals
and receipts. Neither a GUI launch, passive mode detection nor these offline
checks establishes device-write or physical acceptance.

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

The earlier aggregate Python run passed **150 tests** and focused relay run
passed **51 tests**; these counts are historical. The current relay suite
passed **62 tests** within the 189-test integration run above. See
[VERIFICATION.md](VERIFICATION.md) for dated counts and deployment/native
panel acceptance. The
suite includes recursive physical-identifier filtering, ASCII/multibyte
metadata size boundaries, legacy receipt replay, and recovery only after a
proven oversize rejection. Remote modern-protocol acceptance and physical
device acceptance are recorded separately from local SDK and metadata checks.
