# JetBrains AI Assistant — Runlog skill adapter

**Status:** ✅ shipped, with caveats. JetBrains AI Assistant's MCP support and tool-use capabilities vary across IDE products (IntelliJ IDEA, PyCharm, WebStorm, GoLand, Rider, RubyMine, PhpStorm, CLion, RustRover) and plugin versions — verify against the current AI Assistant docs for the IDE and plugin version you have installed before publishing your config.

JetBrains AI Assistant adapter of the Runlog client skills. Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install in the project's AI guidelines or as a custom prompt |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter |
| [`runlog-harvest.md`](./runlog-harvest.md) | Harvest skill — end-of-session retrospective submission flow |

## Quickstart

1. **Get an API key** at https://runlog.org/register and set:

   ```sh
   export RUNLOG_API_KEY="sk-runlog-<your-key>"
   ```

2. **Add Runlog as an MCP server** through the AI Assistant settings. Path varies by IDE:
   - Settings (or Preferences on macOS) → Tools → AI Assistant → MCP Servers (or similar — exact menu item is plugin-version-dependent)
   - URL: `https://api.runlog.org/mcp`
   - Transport: `http` or `streamable-http`
   - Custom header: `Authorization: Bearer ${RUNLOG_API_KEY}`

   For plugin versions that read MCP config from a JSON file:

   ```json
   {
     "mcpServers": {
       "runlog": {
         "url": "https://api.runlog.org/mcp",
         "headers": {
           "Authorization": "Bearer ${RUNLOG_API_KEY}"
         }
       }
     }
   }
   ```

   > **VERIFY against current JetBrains AI Assistant docs.**

3. **Install the read-side skill** as a project AI guideline. Settings → Tools → AI Assistant → Guidelines — paste the body of `SKILL.md`. Or add to a project-scoped guidelines file (path varies by version).

4. **(Optional) Install the write-side skill** for verified submissions — same surface with `runlog-author.md`. Then build the verifier and generate a keypair (see SKILL.md §Setup).

5. **(Optional) Install the harvest skill** for end-of-session retrospective submission — same surface with `runlog-harvest.md` (paste into AI Assistant Guidelines or the project-scoped guidelines file). Invoke at session end with the literal "harvest this session to runlog" inside Junie agent mode. Same verifier prerequisites as the write-side skill.

6. **Verify** — open AI Assistant chat (or Junie); `runlog_search`, `runlog_submit`, `runlog_report` should appear in the available tools when MCP is wired correctly.

## Cross-vendor invariants

Every JetBrains adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md).
- The harvest-side rules in [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) (when running the harvest skill).

The contract is framework-agnostic; JetBrains adapters swap orchestration glue (Settings UI for MCP config, AI guidelines for rule loading, Junie agent-mode dispatch), not the rules.

## Notes

- AI Assistant's classic chat mode may not support tool use; Junie (the agent mode) is the surface that dispatches MCP tool calls. Confirm you're using the right mode.
- The IDE's environment variables are inherited from the launching shell on Linux/macOS. On Windows or when launching from a desktop launcher, set `RUNLOG_API_KEY` via the IDE's environment-variable settings (Help → Edit Custom VM Options is for JVM args, not env vars; use Settings → Build → Toolchains or per-run-config env vars where applicable).
- JetBrains has been actively iterating AI Assistant's tool-use surface. If your installed version doesn't yet expose MCP tool calls in chat, track upstream and re-evaluate.
