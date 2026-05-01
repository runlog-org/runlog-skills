# Windsurf — Runlog skill adapter

**Status:** ✅ shipped. Read side is operational; write side is operational once F24 prerequisites land.

Windsurf (Codeium) adapter of the Runlog client skills. Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install as `.windsurfrules` (workspace) or in Windsurf global rules |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter |
| [`runlog-harvest.md`](./runlog-harvest.md) | Harvest skill — end-of-session retrospective submission flow |

## Quickstart

1. **Get an API key** at https://runlog.org/register and set:

   ```sh
   export RUNLOG_API_KEY="sk-runlog-<your-key>"
   ```

2. **Add Runlog to Windsurf's MCP config** at `~/.codeium/windsurf/mcp_config.json`:

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

3. **Install the read-side skill** as a Windsurf rule:

   ```sh
   cp skills/windsurf/SKILL.md .windsurfrules
   ```

   Or paste into Settings → Cascade → Rules → "Global Rules" for cross-workspace use.

4. **(Optional) Install the write-side skill** for verified submissions — append `skills/windsurf/runlog-author.md` to `.windsurfrules`. Then build the verifier and generate a keypair (see SKILL.md §Setup).

5. **(Optional) Install the harvest skill** for end-of-session retrospective submission — append `skills/windsurf/runlog-harvest.md` to `.windsurfrules`. Invoke at session end with the literal "harvest this session to runlog". Same verifier prerequisites as the write-side skill.

6. **Verify** — open Cascade; `runlog_search`, `runlog_submit`, `runlog_report` should appear in the tool list.

## Cross-vendor invariants

Every Windsurf adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md).
- The harvest-side rules in [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) (when running the harvest skill).

The contract is framework-agnostic; Windsurf adapters swap orchestration glue (Cascade integration, `.windsurfrules` rule loading, terminal-tool dispatch), not the rules.

## Notes

- Windsurf's MCP config path and schema have evolved across versions — verify against the current Windsurf docs before publishing.
- Windsurf's "memory" system is workspace-scoped and persistent across sessions — useful for the team-memory layer (rule 1 of the four-point contract). Keep memories that come out of internal-code investigations there; route external-dependency learnings to `runlog_submit`.
