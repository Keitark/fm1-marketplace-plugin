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
verified, and **Refresh** worked in the actual native MCP App panel. No Chrome
extension is required for this native plugin experience. The website can be
opened independently of plugin installation.

## Current bench state

Browse the five app cards: **NES, Doom, MDX, Buddha, and ProTracker**. The
verified local relay is connected with switching **Disabled**. It reports six
validated private package variants; all are currently blocked because the
local bridge has no configured protected session or verified baseline.

Inventory reported COM4 and CDC/audio interfaces. This verifies metadata
transport, not a device write or physical acceptance. A tested MDX **View plan**
request reached the bridge and failed with **Start a protected session on the
laptop first**. That is an expected prerequisite failure; no protected helper
was created and no device I/O occurred.

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

## Review an app switch

Switching must already be enabled deliberately at the bench. **Review switch**
opens a review without writing anything. Check the exact app, variant,
SHA-256, and entry method against the package you intend to use.

Click **Confirm app switch** yourself only when that review is correct and
the bench is ready. The approval expires and can be used once. **Cancel** or
Escape closes the review and clears its approval. Browser tools can open a
review; they do not expose a confirmation tool. Keep the returned job ID if
the connection is interrupted.

## Read progress correctly

**Bench connected** means the relay is responding. Package readiness means the
bench reported a usable package. A delivered request can still contain a
failed or unknown device job; inspect the saved job's own status.

Sector counts describe reported verified progress. They do not establish
successful startup, screen output, sound, or working keys. An unknown device
outcome needs inspection by the bench owner before another device operation.
Physical acceptance remains a separate bench check.

Site version 2 is deployed, and Refresh and saved-job inspection still work
from the cached native panel. A newly opened panel currently keeps the older
**Choose what plays next.** heading and tool title; the new device panel has
not yet been accepted in the host. There is no exposed supported panel refresh
tool, and restart/reinstall has not been verified as a fix. See
[VERIFICATION.md](VERIFICATION.md) for the distinction between the tested v2
server and the cached v1 panel.

Further detail: [relay setup](SITE_RELAY.md), [browser tools and verification](WEBMCP.md),
[integration handoff](INTEGRATION_HANDOFF.md), and [verification evidence](VERIFICATION.md).
