# Initial source snapshot verification

Verified on 2026-10-09 using Python 3.11 and Node.js on the Windows bench:

| Check | Result |
|---|---|
| `python -m unittest discover -s tools/jieli-wl82 -p 'test_*.py'` | 97 tests passed |
| `node --test tools/jieli-wl82/test_remote_store.cjs` | 10 tests passed |
| Source snapshot hashes and sizes | All 14 imported files matched |
| PowerShell syntax parsing | Both copied scripts passed |
| Independent publication scan | No embedded credentials, private session/device IDs, firmware/music/game payloads, or oversized files found |

Tests use mocked device operations, synthetic data, temporary state, and loopback HTTP. These results verify the source snapshot and existing store/bridge contracts; they do not verify a live USB write, an MCP connection, native extension entrypoints, WebMCP discovery, or Sites hosting.

The protected writer/bootstrap, private packages, and vendor USB dependencies remain outside this repository. Python bytecode generated during verification is ignored by Git.
