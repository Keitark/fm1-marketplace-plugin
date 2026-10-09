# Browser tools and MCP App panel

The top-level FM1 Site registers six tools through
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
| `start_fm1_switch_review` | `{catalog_id,entry_method}` | Open human review; `entry_method` is `serial` or `already_uboot`. No device write is submitted. |

There is no WebMCP confirmation tool. Review returns package identity and
SHA-256 but never the approval nonce. Cancel or Escape clears the displayed
approval. Final confirmation requires a trusted click on the visible control,
the server's owner-bound one-use approval, and deliberate local switching
enablement. See [the relay contract](SITE_RELAY.md) for delivery, digest, expiry,
and uncertainty handling.

## Embedded panel

The iframe uses native MCP Apps, not the top-level WebMCP registry. It sends
`ui/initialize`, receives host capabilities/context, then sends
`ui/notifications/initialized`. The host's initial library tool result renders
without a duplicate library request. If that result is absent, a bounded
fallback reads the library only when the host advertises `serverTools`.

New requests use host-proxied `tools/call` and require `serverTools`; an initial
result can still render without that capability. The iframe acknowledges
`ui/resource-teardown`, aborts its lifecycle, clears approval state, and rejects
pending requests. Page closure performs the same cleanup.

## Verification recorded on 2026-10-09

In a supported in-app browser, all six tools were discovered and called with
valid input against the local HTTP synthetic relay. Library read/refresh,
offline planning, saved-request inspection, saved-job inspection, and staged
review updated the visible interface. The synthetic job showed 2 of 4 verified
sectors. Review returned the package digest without approval data; Cancel
closed the modal. Malformed input was rejected for all six tools. The actual
browser's Confirm control was not clicked. A local SQLite read after stopping
the fixture confirmed zero queued `switch_app` tasks; no device writes were
performed.

The 11 formal UI tests in `site/test/ui.test.mjs` passed. They cover initial
render without duplicate requests, initial render without `serverTools`,
fallback, teardown, registry abort, nonce-free review, untrusted confirmation
rejection, Cancel/Escape, one-use trusted confirmation, awaited job inspection,
and malformed input rejection. The trusted-click test is a VM fixture, not a
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

4. Open the local URL in an in-app browser that exposes WebMCP. Discover the six
   tools, exercise the valid and malformed cases above, and read back the UI
   state. Use the synthetic `nes-test` package for planning/review and Cancel
   the review. Stop the fixture and local Worker afterward.
5. Run the formal UI checks separately:

   ```powershell
   node --test test/ui.test.mjs
   ```

The fixture accepts only the literal loopback origin on port 3000, imports no
bridge or device backend, and returns synthetic metadata. These results do
not establish deployed plugin entrypoints, an authenticated live bench relay,
hardware write/readback/startup, sound, screen, keys, or physical acceptance.
