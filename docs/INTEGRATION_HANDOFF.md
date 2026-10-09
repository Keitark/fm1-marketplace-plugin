# FM1 Codex integration handoff

## Goal and current state

The user wants the local FM1 store available in Codex, using OpenAI plugin extensions and potentially a Sites-hosted MCP App/server plus WebMCP. They requested publishing this source repository and collaboration with the running **Set up remote debug kit** chat on this PC.

This repository is the current store/bridge foundation. It has no MCP transport or extension registration yet. The first session researched feasibility and prepared this source snapshot; a follow-up session should implement and verify the integration.

## Existing operations to reuse

| Capability | Existing API | Integration behavior |
|---|---|---|
| Device inventory and writer state | `GET /v1/status` | Read current readiness; preserve blocked and unknown outcomes. |
| App library | `GET /v1/catalog` | Return variant metadata and readiness, without firmware image bytes. |
| Offline app plan | `POST /v1/jobs`, `operation: plan_app` | Requires a catalog ID and an existing verified baseline; returns a durable job ID. |
| Job status/progress | `GET /v1/jobs/<id>` | Resume by saved ID; do not resubmit after a network timeout. |
| App switching | `POST /v1/jobs`, `operation: switch_app` | Preserve catalog validation, explicit entry method, confirmation, and protected writer checks. |

The store's `api()`, `refresh()`, `preview()`, `choose()`, `submit()`, and `poll()` functions already implement these flows. Job submission uses a unique ID. The backend delegates device work to `flash-session-client.ps1` and the selected existing protected session. The source snapshot also includes progress reporting and explicit app-variant labels from the active progress kit.

`/v1/status` is inventory/persisted-state access. `serial_status` and `read_firmware` are separate device operations; do not label them as passive reads. Firmware read setup can affect loader/protection state.

## Extension and transport findings

- [OpenAI plugin extensions](https://developers.openai.com/plugins/build/extensions) provide sidebar and conversation entrypoints through MCP App metadata. Test the chosen surface in the user's installed Codex/desktop app; the documentation describes ChatGPT surfaces.
- [WebMCP site tools](https://learn.chatgpt.com/docs/webmcp) use `document.modelContext.registerTool` in a top-level browser page. Feature-detect this API and preserve the human interface when it is unavailable.
- WebMCP tools inside iframes are not discovered. An MCP App panel therefore needs server MCP tools and its app-to-host bridge; WebMCP can be offered separately by the full website.
- The existing store sets `frame-ancestors 'none'`, and the HTTP API has no cross-origin access. Do not simply iframe the loopback page or weaken authentication to make a hosted page connect.
- A hosted Sites backend cannot reach loopback or a private tailnet endpoint by default. Keep the Windows device bridge local; choose and verify an authenticated relay/tunnel before claiming hosted tool access.
- [Sites MCP instructions](https://learn.chatgpt.com/docs/sites) should be checked with the installed Sites skills during implementation. Sites provisions its own plugin connection; preserve user-specific authorization and its hosting authentication.

For a native panel, the intended path is `Codex MCP App -> hosted MCP tools -> trusted local transport -> FM1 bridge -> protected session -> USB device`. For local WebMCP, the page can use its current same-origin authenticated API directly.

## Suggested next steps

1. Confirm the first user-facing experience: a native panel, tools in the existing local store, or both. The previous experience picker was unanswered; neither option is an established preference.
2. Read the installed OpenAI Docs and Sites MCP skills and current official APIs before implementation. No OpenAI inference API is needed merely to expose existing FM1 tools.
3. Implement catalog, inventory, offline planning, and job inspection first, using narrow schemas and metadata-only results.
4. Verify disconnected, blocked, missing-package, invalid-ID, and timeout/resume behavior with the existing offline tests and meaningful integration checks.
5. Add app switching through the reviewed confirmation flow. A tool that requests confirmation must not submit a write while claiming only to display a dialog.
6. If using Sites, verify the transport and permissions, then package/deploy privately and verify a read-only tool through the provisioned plugin.

## Source and coordination boundaries

The live launcher configuration selected `progress-kit/fm1-remote` when this snapshot was prepared, and the setup chat confirmed that the convenience launcher also selects that kit. Inspect the live launch configuration again before operational changes. This publication does not modify or restart the running bridge.

The remote-debug setup chat owns live bench setup and its private assets. Coordinate changes with it. Keep private catalog JSON (which contains firmware image bytes), bootstrap images, ROM/music inputs, device receipts, tokens, actual session descriptors, and runtime installers out of this public repository. Use synthetic fixtures for tests. The protected session and vendor USB dependencies remain external prerequisites.
