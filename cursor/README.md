# Cursor — Runlog skill adapter

**Status:** ✅ shipped. Read side is operational; write side is operational once F24 prerequisites land (see `skills/runlog-author/DESIGN.md §Status`).

Cursor adapter of the Runlog client skills. Cursor is the highest-priority vendor target after Claude Code (largest agent-tool user base). Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install as `.cursor/rules/runlog.mdc` (or `~/.cursor/rules/runlog.mdc` globally) |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter — install as `.cursor/rules/runlog-author.mdc` |

## Quickstart

1. **Get an API key** at https://runlog.org/register and set it:
   ```sh
   export RUNLOG_API_KEY="sk-runlog-<your-key>"
   ```

2. **Add Runlog to Cursor's MCP config.** Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):
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

3. **Install the read-side skill** as a Cursor rule:
   ```sh
   mkdir -p .cursor/rules
   cp skills/cursor/SKILL.md .cursor/rules/runlog.mdc
   ```

4. **(Optional) Install the write-side skill** for verified submissions:
   ```sh
   cp skills/cursor/runlog-author.md .cursor/rules/runlog-author.mdc
   ```
   Then build the verifier (`cd verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/`) and generate a keypair (`runlog-verifier keygen --out ~/.runlog/key`).

5. **Verify** — open Settings → Cursor Settings → MCP. `runlog` should show as connected with three tools.

## Cross-vendor invariants

Every Cursor adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) (when running the write skill).

The contract is framework-agnostic; Cursor adapters swap orchestration glue (slash-command invocation, `.mdc` rule format, terminal-tool dispatch), not the rules.

## Older Cursor versions

For workspaces still on the legacy single-file rules format, append the body of `SKILL.md` (and `runlog-author.md` if using the write side) to a `.cursorrules` file at the workspace root instead of the per-rule `.mdc` files. The newer `.cursor/rules/*.mdc` format is preferred — it supports YAML frontmatter for scoping rules to specific globs.
