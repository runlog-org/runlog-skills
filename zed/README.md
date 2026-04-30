# Zed — Runlog skill adapter

**Status:** ✅ shipped, with caveats. Zed's `context_servers` schema and HTTP-transport support are evolving — verify the exact JSON shape for HTTP MCP servers against current Zed docs before publishing your config. The stdio-bridge fallback (mcp-proxy or similar) works on older Zed versions that don't yet support HTTP transports natively.

Zed adapter of the Runlog client skills. Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install as `.rules` (workspace) or `~/.config/zed/rules.md` (global) |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter |

## Quickstart

1. **Get an API key** at https://runlog.org/register and set:

   ```sh
   export RUNLOG_API_KEY="sk-runlog-<your-key>"
   ```

2. **Add Runlog to Zed's `context_servers`** in `~/.config/zed/settings.json` (global) or `.zed/settings.json` (workspace). HTTP transport (newer Zed):

   ```json
   {
     "context_servers": {
       "runlog": {
         "source": "custom",
         "url": "https://api.runlog.org/mcp",
         "headers": {
           "Authorization": "Bearer ${RUNLOG_API_KEY}"
         }
       }
     }
   }
   ```

   Or stdio bridge (older Zed):

   ```json
   {
     "context_servers": {
       "runlog": {
         "command": {
           "path": "npx",
           "args": ["-y", "mcp-proxy", "--http", "https://api.runlog.org/mcp"],
           "env": {
             "MCP_PROXY_AUTH_HEADER": "Authorization: Bearer ${RUNLOG_API_KEY}"
           }
         }
       }
     }
   }
   ```

   > **Security note.** `npx -y mcp-proxy` installs the latest published version on every Zed launch. `mcp-proxy` is a third-party npm package — verify the publisher before trusting it with `RUNLOG_API_KEY`. For production use, pin to a specific version (`"mcp-proxy@X.Y.Z"`). Run `npm view mcp-proxy` to find the current latest and pin to it.

   > **VERIFY against current Zed docs** at https://zed.dev/docs/.

3. **Install the read-side skill** as a Zed rule:

   ```sh
   cp skills/zed/SKILL.md .rules
   ```

   Or global:

   ```sh
   mkdir -p ~/.config/zed
   cp skills/zed/SKILL.md ~/.config/zed/rules.md
   ```

4. **(Optional) Install the write-side skill** for verified submissions — append `runlog-author.md` to the rules file. Then build the verifier and generate a keypair (see SKILL.md §Setup).

5. **Verify** — open Zed Assistant. `runlog_search`, `runlog_submit`, `runlog_report` should appear in the available tools.

## Cross-vendor invariants

Every Zed adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md).

The contract is framework-agnostic; Zed adapters swap orchestration glue (`context_servers` config, `.rules` file format, Zed Assistant's tool-call surface), not the rules.

## Notes

- Zed historically supported only stdio-launched MCP servers via `context_servers`. HTTP transport support has been added in newer versions; the exact JSON shape (`url` / `transport` / `source`) varies. The stdio bridge is a reliable fallback that works across versions and also lets you inspect MCP traffic locally.
- Zed Assistant's tool-use depends on the model supporting tool calls. Smaller local models or completion-only modes won't support the verification loop.
