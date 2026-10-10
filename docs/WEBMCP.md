# Native MCP App panel and browser tools

The installed FM1 plugin and native MCP App panel are the user's primary
interface. On 2026-10-09, native library/status/catalog/saved-job tools and panel
Refresh succeeded through the authenticated local relay. After Site v3
deployment, the actual Codex MCP App panel renders the updated black/mint UI
with **FM1 on COM4**. Older installed descriptors can read that current UI
through compatibility resource aliases.
Native Refresh and exact saved-job inspection after the relay restart also
passed in this updated panel, verifying the deployed MCP Apps SDK host bridge.
The full website's WebMCP tools are an additional interface; native plugin use
requires no Chrome extension.

The top-level FM1 Site registers seven tools through
`document.modelContext.registerTool` when the in-app browser supports WebMCP.
They share the visible library's actions and state. Unsupported browsers keep
the ordinary controls. Registration uses an `AbortSignal` and is removed when
the page closes.

## Browser tool contract

Every input is an object with exactly the fields below; required fields,
unexpected fields, types, patterns, and enum values are checked before action.
`catalog_id` matches `^[a-z0-9][a-z0-9_-]{0,63}$`. Saved `request_id` and `job_id`
match `^[a-f0-9]{32}$`.

| Tool | Required input | Behavior |
|---|---|---|
| `view_fm1_library` | `{}` | Read saved library, catalog, connection, and requests. |
| `refresh_fm1_library` | `{}` | Refresh inventory and catalog metadata through the relay; no device I/O. |
| `plan_fm1_app` | `{catalog_id}` | Submit an offline plan and show its saved outcome. |
| `inspect_fm1_request` | `{request_id}` | Read the original request's saved delivery and job outcome. |
| `inspect_fm1_job` | `{job_id}` | Inspect the original bridge job and display its result; never resubmit it. |
| `start_fm1_switch_review` | `{catalog_id,entry_method}` | Open human review; `entry_method` is `auto`, `serial` or `already_uboot`. Automatic selection is rechecked locally before device operations. No device write is submitted. |
| `start_fm1_official_update_review` | `{}` | Review the pinned official Windows SysEx updater. No updater launch or firmware transfer is submitted. |

There is no WebMCP confirmation tool. Review returns package identity and
SHA-256 but never the approval nonce. Cancel or Escape clears the displayed
approval. Final confirmation requires a trusted click on the visible control,
the server's owner-bound one-use approval, and deliberate local switching
enablement. Official updater review uses a separate local capability and binds
the executable SHA-256. Its human confirmation opens the vendor tool; completion
remains in that tool. See [the relay contract](SITE_RELAY.md) for delivery, digest, expiry,
and uncertainty handling.

## Native panel and SDK migration

The iframe uses native MCP Apps, not the top-level WebMCP registry. The panel
contract sends
`ui/initialize`, receives host capabilities/context, then sends
`ui/notifications/initialized`. The host's initial library tool result renders
without a duplicate library request. If that result is absent, a bounded
fallback reads the library only when the host advertises `serverTools`.

New requests use host-proxied `tools/call` and require `serverTools`; an initial
result can still render without that capability. The iframe acknowledges
`ui/resource-teardown`, aborts its lifecycle, clears approval state, and rejects
pending requests. Page closure performs the same cleanup.

The Site pins **ext-apps 2.0.3** and official server SDK **2.3.1**.
The current resource is `ui://fm1/device-panel-v4.html`; v1, v2 and v3 aliases
serve the same current panel. The ten MCP tools include two app-only confirmation
tools. See [VERIFICATION.md](VERIFICATION.md) for dated deployment evidence.
The historical v3 release passed 45 Site tests, typecheck, production build and
private deployment. Actual SDK Client 2.3.1 negotiated **2026-07-28** and legacy
**2025-11-25** protocols in memory. The new native UI resource is
`ui://fm1/device-panel-v3.html`. Tool descriptors advertise that URI; reads of
`ui://fm1/app-library-v1.html` and `ui://fm1/device-panel-v2.html` return the same
current HTML with identical metadata and CSP. Both modern and legacy SDK
integration tests verify these reads.

The actual native Codex panel now renders the updated UI, although a cached
tool title may remain older. The UI preserves the original job ID across
metadata refresh and a lost confirmation reply. Saved-job inspection always
targets that exact ID and does not resubmit a plan or switch. An earlier direct
deployed SDK Client probe using the relay service credential returned HTTP 401;
that probe did not verify remote modern-protocol negotiation.

## Verification recorded on 2026-10-09

The installed native plugin's open/status/catalog/job calls succeeded, and
Refresh worked in the actual native MCP App iframe. Live Site WebMCP Refresh
also worked through the local bridge/relay with switching disabled. Inventory
reported COM4 and CDC/audio interfaces; all six validated private packages were
blocked (`ready:false`) because no protected session or verified baseline was
configured. The tested MDX plan was delivered but its bridge job failed with
**Start a protected session on the laptop first**. No helper was created and
no device I/O occurred. These live results verify metadata transport and
prerequisite handling, not a successful plan or hardware acceptance.

After the v3 deployment, native Refresh succeeded and preserved the original
job ID in the recovery field. After restarting the relay with its existing
state, native **Inspect job** returned the same original MDX job with its
authoritative protected-session prerequisite failure. These checks establish
current native rendering and host-proxied calls without resubmitting the job.
Exact request IDs and deployment receipts are in
[VERIFICATION.md](VERIFICATION.md).

Earlier synthetic browser validation covered the complete six-tool contract:

In a supported in-app browser, all six tools were discovered and called with
valid input against the local HTTP synthetic relay. Library read/refresh,
offline planning, saved-request inspection, saved-job inspection, and staged
review updated the visible interface. The synthetic job showed 2 of 4 verified
sectors. Review returned the package digest without approval data; Cancel
closed the modal. Malformed input was rejected for all six tools. The actual
browser's Confirm control was not clicked. A local SQLite read after stopping
the fixture confirmed zero queued `switch_app` tasks; no device writes were
performed.

The current **15 formal UI tests** in `site/test/ui.test.mjs` passed. They cover initial
render without duplicate requests, initial render without `serverTools`,
fallback, teardown, registry abort, nonce-free review, untrusted confirmation
rejection, Cancel/Escape, one-use trusted confirmation, awaited job inspection,
malformed input rejection, and the native device-controls view with a detected
port and no duplicate refresh. Additional recovery checks preserve the job ID
through refresh and a lost confirmation reply, and select the exact job ID
for WebMCP inspection without resubmission. The trusted-click test is a VM fixture, not a
physical browser or hardware operation.

## Repeat the local fixture

Use a disposable local database and run from `site/` with the repository's
installed dependencies. Do not use a deployed Site or real bridge credentials.

1. In the ignored local `.dev.vars`, set this fixture-only value:

   ```dotenv
   FM1_RELAY_TOKEN=test-only-browser-fixture-token-0000
   ```

2. Apply the checked-in `drizzle/` migration to the disposable local `DB`
   binding using an ignored local Wrangler configuration. Start the Worker
   development preview on `http://127.0.0.1:3000` with that same database
   configuration. In the browser, complete the bundled local preview's mock
   sign-in at `http://127.0.0.1:3000/signin-with-chatgpt?return_to=/`. This is the
   local test identity flow; hosted identity continues to come from Sites.
3. In another terminal, start the fixture:

   ```powershell
   node test/browser-fixture.mjs http://127.0.0.1:3000
   ```

4. Open the local URL in an in-app browser that exposes WebMCP. Discover the seven
   tools, exercise the valid and malformed cases above, and read back the UI
   state. Use the synthetic `nes-test` package for planning/review and Cancel
   the review. Stop the fixture and local Worker afterward.
5. Run the formal UI checks separately:

   ```powershell
   node --test test/ui.test.mjs
   ```

The fixture accepts only the literal loopback origin on port 3000, imports no
bridge or device backend, and returns synthetic metadata. These results do
not establish actual native resource rendering, remote modern negotiation, or hardware
write/readback/startup, sound, screen, keys, or physical acceptance. Live native
plugin rendering and metadata relay evidence are recorded separately above
and in [VERIFICATION.md](VERIFICATION.md).
