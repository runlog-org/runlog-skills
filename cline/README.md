# Cline — Runlog skill adapter

**Status:** ✅ shipped. Read side is operational; write side is operational once F24 prerequisites land (see `skills/runlog-author/DESIGN.md §Status`).

Cline adapter of the Runlog client skills. Cline is the second-highest priority vendor after Cursor — open-source and MCP-native, so the adapter is structurally simpler than closed-source IDE plugins. Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install as `.clinerules/runlog.md` |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter — install as `.clinerules/runlog-author.md` |

## Quickstart

1. **Get an API key** at https://runlog.org/register and set:
   ```sh
   export RUNLOG_API_KEY="sk-runlog-<your-key>"
   ```

2. **Add Runlog to Cline's MCP settings.** Open Cline → Settings → MCP Servers → "Configure MCP Servers" (this opens `cline_mcp_settings.json`):
   ```json
   {
     "mcpServers": {
       "runlog": {
         "url": "https://api.runlog.org/mcp",
         "headers": {
           "Authorization": "Bearer ${RUNLOG_API_KEY}"
         },
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

3. **Install the read-side skill** as a Cline rule:
   ```sh
   mkdir -p .clinerules
   cp skills/cline/SKILL.md .clinerules/runlog.md
   ```
   Cline auto-loads every `.md` file in `.clinerules/` into the agent's context.

4. **(Optional) Install the write-side skill** for verified submissions:
   ```sh
   cp skills/cline/runlog-author.md .clinerules/runlog-author.md
   ```
   Then build the verifier (`git clone https://github.com/runlog-org/runlog-verifier && cd runlog-verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/`) and generate a keypair (`runlog-verifier keygen --out ~/.runlog/key`).

5. **Verify** — open Cline's MCP Servers panel; `runlog` should show as connected with three tools.

## MCP settings file location

Cline stores MCP server config in VS Code's globalStorage. The path is the same file the in-app "Configure MCP Servers" button opens:

| OS | Path |
|---|---|
| Linux | `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| macOS | `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| Windows | `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json` |

If you use VS Code Insiders or VSCodium, replace `Code` in the path with `Code - Insiders` / `VSCodium`.

## Cross-vendor invariants

Every Cline adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) (when running the write skill).

The contract is framework-agnostic; Cline adapters swap orchestration glue (`execute_command` for the verifier, Plan/Act mode iteration, `.clinerules/` rule loading), not the rules.

## Auto-approve recommendations

To reduce friction in the write-side verification loop, consider whitelisting `runlog-verifier` in Cline's command auto-approve list. The verifier reads only the draft file and writes nothing outside `~/.runlog/` and `/tmp/`. Auto-approving `runlog_submit` is optional and risk-managed (forged signatures can't bypass server-side validation, but you lose the final "ship it?" gate).

User-rules (cross-workspace) typically live in `~/Documents/Cline/Rules/` — drop `runlog.md` and `runlog-author.md` there to apply across all workspaces. The exact path varies by Cline version; check Cline's settings UI.
