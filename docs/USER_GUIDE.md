# FM1 App Library user guide

Open the private [FM1 App Library](https://fm1-app-library.keitark.chatgpt.site)
and sign in with the owner account when prompted. The library uses the
[black/mint FM-1 mark](../site/public/fm1-icon.png).

## Install the ChatGPT/Codex plugin

Use **Install** or **Connect** on the offered **FM1 App Library** installation
card, then complete any sign-in prompts. If that offer is no longer visible,
ask to reopen the installation offer for the provisioned plugin. There is no
need to create another plugin or configure a local MCP server.

Once connected, ask ChatGPT or Codex to open your FM1 app library. The plugin
advertises a sidebar entry and a conversation panel. At the recorded
2026-10-09 handoff, installation had been offered, but user connection and
native panel rendering had not been confirmed. The website can be opened
independently of plugin installation.

## What you can do without an FM1

Browse the five app cards: **NES, Doom, MDX, Buddha, and ProTracker**. With no
bench relay connected, **Bench disconnected**, **Offline**, and switching
**Disabled** are expected. An empty library shows **No package connected**;
the cards describe supported apps, not installed firmware or sample packages.

Fresh planning and switching controls stay disabled until the bench supplies
real package metadata. Previously saved responses can remain visible after a
disconnect. No FM1 is currently available for live acceptance, so the published
Site is not evidence that a device has been connected or flashed.

## When the bench is ready

The bench owner first connects the existing bridge and outbound relay using
[SITE_RELAY.md](SITE_RELAY.md). The Site does not start the bridge or prepare a
device session.

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

Further detail: [relay setup](SITE_RELAY.md), [browser tools and verification](WEBMCP.md),
[integration handoff](INTEGRATION_HANDOFF.md), and [verification evidence](VERIFICATION.md).
