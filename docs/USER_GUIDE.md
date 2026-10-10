# FM1 App Library user guide

Use the installed **FM1 App Library** plugin in ChatGPT or Codex and ask it to
open your FM1 app library. Its native panel is the primary interface selected
for this integration. The private [FM1 App Library website](https://fm1-app-library.keitark.chatgpt.site)
is also available; sign in with the owner account when prompted. Both use the
[black/mint FM-1 mark](../site/public/fm1-icon.png).

## Install the ChatGPT/Codex plugin

Use **Install** or **Connect** on the offered **FM1 App Library** installation
card, then complete any sign-in prompts. If that offer is no longer visible,
ask to reopen the installation offer for the provisioned plugin. There is no
need to create another plugin or configure a local MCP server.

The plugin advertises a sidebar entry and a conversation panel. On 2026-10-09,
the installed plugin's library, status, catalog, and saved-job tools were
verified. The updated Site v3 panel renders in Codex with **FM1 on COM4** and
the black/mint interface. **Refresh** and exact saved-job inspection after
the relay restart also passed in that native panel. No Chrome
extension is required for this native plugin experience. The website can be
opened independently of plugin installation.

## Recorded metadata bench state (2026-10-09)

The following is the recorded metadata acceptance check. Use **Refresh** for
the current session, update mode and enable flags; later setup does not turn
these earlier observations into hardware acceptance.

Browse the five app cards: **NES, Doom, MDX, Buddha, and ProTracker**. The
verified local relay is connected with switching **Disabled**. It reports six
validated private package variants; all are currently blocked because the
local bridge has no configured protected session or verified baseline.

Inventory reported COM4 and CDC/audio interfaces. This verifies metadata
transport, not a device write or physical acceptance. A tested MDX **View plan**
request reached the bridge and failed with **Start a protected session on the
laptop first**. That is an expected prerequisite failure; no protected helper
was created and no device I/O occurred.

Inspection after the relay restart returned that same original job and
prerequisite failure. Refresh retained its job ID; it did not create another
plan or switch.

If the relay later disconnects, **Bench disconnected** and **Offline** are
expected. Saved responses can remain visible after a disconnect. With no
private package metadata, cards show **No package connected**; the cards
describe supported apps rather than installed firmware.

## When the bench is ready

The metadata bridge and outbound relay are already connected in the recorded
setup. Before planning can succeed or switching can be enabled, the bench
owner must prepare and verify the protected session and unit-specific
baseline through the established bench workflow. The Site does not prepare
that session. See [SITE_RELAY.md](SITE_RELAY.md) for connection and recovery
details; preserve an existing listener and its state.

1. Click **Refresh** to load current inventory and package metadata.
2. Choose a package variant on its app card. Check its **Ready/Blocked** state
   and displayed **SHA256**. A blocked package needs bench-side attention.
3. Click **View plan** to check the selected package offline. This creates a
   saved request and does not write to the device.
4. Keep the original request and job IDs. Click a row under **Saved requests &
   progress** to inspect that request, or paste the original 32-character job
   ID into **Inspect a saved job** and click **Inspect job**. After a timeout or
   disconnect, resume those IDs instead of submitting another operation.
   **Refresh** preserves the job ID already entered in the recovery field.

## Review an app switch

Switching must already be enabled deliberately at the bench. **Review switch**
opens a review without writing anything. Check the exact app, variant,
SHA-256, and entry method against the package you intend to use.

Click **Confirm app switch** yourself only when that review is correct and
the bench is ready. The approval expires and can be used once. **Cancel** or
Escape closes the review and clears its approval. Browser tools can open a
review; they do not expose a confirmation tool. The panel saves the original
job ID before submitting confirmation. If the confirmation reply is lost,
use **Inspect job** with that ID before reviewing another switch; do not
submit the operation again.

## Choose the update route

The **Auto** entry method chooses the protected app route from fresh passive
inventory: one recognized CDC interface uses the existing serial entry flow;
one UBOOT disk uses the already-in-UBOOT flow. An inventory error, duplicate
devices, conflicting modes or a changed mode prevents submission. The approved
catalog ID and package SHA-256 still identify the custom app to install.
Auto does not convert an app bundle into an official firmware package.

For official firmware, open its review and confirm the displayed executable
SHA-256 yourself. The bench must separately enable official-update
handoff and expose one recognized stock or OTA MIDI input/output pair. The
confirmed action opens the locally configured M-UPGRADE GUI; select the correct
official `.fwsc` there and complete the manufacturer workflow locally. The
[manufacturer download page](https://www.m-vave.com/download) lists the generic
[M-UPGRADE package](https://yms-file-store.oss-cn-hongkong.aliyuncs.com/software/pc/M-UPGRADE.zip)
and [FM-1 V15 firmware](https://yms-file-store.oss-cn-hongkong.aliyuncs.com/software/firmware/FM-1.fwsc).
The older FM1-specific bundle embeds V14, so use the reviewed generic updater
for the external V15 package.

A saved successful handoff means the GUI started. It does not establish a
firmware transfer or verification. Keep its original job ID if any reply is
lost. Handoff persistently blocks further device jobs because the old baseline
may no longer describe the FM1. After official completion, the bench owner must
establish a fresh protected session and verified current-unit baseline while
preserving the previous state and receipts. There is no remote unblock or
automatic retry. Direct SysEx writing is not implemented by this integration.

Automatic mode selection and vendor handoff have offline contract coverage.
Their physical acceptance must be recorded separately for the connected unit;
the earlier metadata check does not establish it.

## Read progress correctly

**Bench connected** means the relay is responding. Package readiness means the
bench reported a usable package. A delivered request can still contain a
failed or unknown device job; inspect the saved job's own status.

Sector counts describe reported verified progress. They do not establish
successful startup, screen output, sound, or working keys. An unknown device
outcome needs inspection by the bench owner before another device operation.
Physical acceptance remains a separate bench check.

Site version 3 is deployed, and the updated native panel is accepted in Codex.
The server also serves the current UI at the older v1/v2 resource URIs for
installed-plugin compatibility. An older cached tool title can still appear;
the verified panel itself shows the current interface. See
[VERIFICATION.md](VERIFICATION.md) for the dated deployment, native panel,
metadata, and hardware acceptance evidence.

Further detail: [relay setup](SITE_RELAY.md), [browser tools and verification](WEBMCP.md),
[integration handoff](INTEGRATION_HANDOFF.md), and [verification evidence](VERIFICATION.md).
