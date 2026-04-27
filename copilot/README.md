# VS Code GitHub Copilot — Runlog skill adapter

**Status:** ✅ shipped. Read side is operational with VS Code Copilot agent mode + MCP. Write side is operational once F24 prerequisites land.

VS Code GitHub Copilot adapter of the Runlog client skills. Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install in `.github/copilot-instructions.md` or `.github/instructions/runlog.instructions.md` |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter |

## Quickstart

1. **Get an API key** at https://runlog.org/register.

2. **Add Runlog to VS Code's MCP config** at `.vscode/mcp.json`:
   ```json
   {
     "servers": {
       "runlog": {
         "type": "http",
         "url": "https://api.runlog.org/mcp",
         "headers": {
           "Authorization": "Bearer ${input:runlog-api-key}"
         }
       }
     },
     "inputs": [
       {
         "type": "promptString",
         "id": "runlog-api-key",
         "description": "Runlog API key (sk-runlog-...)",
         "password": true
       }
     ]
   }
   ```
   The `${input:...}` form prompts on first use and stores in VS Code's secret store. Or use `${env:RUNLOG_API_KEY}` for the environment-variable form.

   > **VERIFY against current VS Code MCP docs.** The exact JSON shape (`servers` vs `mcpServers`, `type` enum values) has evolved.

3. **Enable instruction files** in VS Code Settings if not already:
   - `github.copilot.chat.codeGeneration.useInstructionFiles`: `true`

4. **Install the read-side skill** as a Copilot instruction:
   ```sh
   mkdir -p .github
   cat skills/copilot/SKILL.md >> .github/copilot-instructions.md
   ```
   Or as a scoped instruction with `applyTo` frontmatter:
   ```sh
   mkdir -p .github/instructions
   cp skills/copilot/SKILL.md .github/instructions/runlog.instructions.md
   ```

5. **(Optional) Install the write-side skill** for verified submissions — same shape with `runlog-author.md`. Then build the verifier and generate a keypair (see SKILL.md §Setup).

6. **Verify** — open Copilot Chat → switch to Agent mode. `runlog_search`, `runlog_submit`, `runlog_report` should appear in the available tools panel.

## Cross-vendor invariants

Every Copilot adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md).

The contract is framework-agnostic; Copilot adapters swap orchestration glue (`.github/copilot-instructions.md` rule loading, agent-mode tool dispatch, VS Code secret-store integration), not the rules.

## Notes

- VS Code Copilot's MCP support requires agent mode — ask/edit modes won't dispatch tool calls.
- Each team member enters their own API key on first use when using `${input:...}` (stored per-user in VS Code's secret store). For shared CI/automation, use `${env:RUNLOG_API_KEY}` instead.
- The `applyTo` frontmatter in `.github/instructions/*.instructions.md` lets you scope Runlog guidance to specific file patterns — useful when you want it only for files that interact with third-party APIs.
