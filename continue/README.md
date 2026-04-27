# Continue.dev — Runlog skill adapter

**Status:** ✅ shipped. Read side is operational; write side is operational once F24 prerequisites land.

Continue.dev adapter of the Runlog client skills. Continue is the third-priority vendor target — open-source and MCP-native. Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install as a Continue rule (see Quickstart) |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter |

## Quickstart

1. **Get an API key** at https://runlog.org/register and set:
   ```sh
   export RUNLOG_API_KEY="sk-runlog-<your-key>"
   ```

2. **Add Runlog to Continue's config.** The exact key name has changed across Continue versions. For Continue 1.0+ (`config.yaml`):
   ```yaml
   mcpServers:
     - name: runlog
       type: streamable-http
       url: https://api.runlog.org/mcp
       requestOptions:
         headers:
           Authorization: "Bearer ${RUNLOG_API_KEY}"
   ```

   For older versions (`config.json`):
   ```json
   {
     "experimental": {
       "modelContextProtocolServers": [
         {
           "transport": {
             "type": "streamable-http",
             "url": "https://api.runlog.org/mcp",
             "requestOptions": {
               "headers": {
                 "Authorization": "Bearer ${RUNLOG_API_KEY}"
               }
             }
           }
         }
       ]
     }
   }
   ```

   > **VERIFY against Continue's current docs** at https://docs.continue.dev/ before publishing — the MCP config schema has evolved.

3. **Install the read-side skill** as a Continue rule. Add to `config.yaml`:
   ```yaml
   rules:
     - name: runlog
       rule: |
         <paste skills/continue/SKILL.md body here>
   ```

4. **(Optional) Install the write-side skill** for verified submissions — same shape as above with `name: runlog-author` and the body of `skills/continue/runlog-author.md`. Then build the verifier and generate a keypair (see SKILL.md §Setup).

5. **Verify** — open Continue's panel; `runlog_search`, `runlog_submit`, `runlog_report` should appear in the tool list.

## Config file locations

| Scope | Path |
|---|---|
| Global | `~/.continue/config.yaml` (or `config.json`) |
| Workspace | `.continue/config.yaml` (committed alongside the project) |

Workspace configs override global. For team-shared rules (everyone gets the same Runlog skill), commit `.continue/config.yaml` with the rules block; the API key still sits in each developer's environment.

## Cross-vendor invariants

Every Continue adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) (when running the write skill).

The contract is framework-agnostic; Continue adapters swap orchestration glue (`config.yaml` schema, terminal-tool dispatch, agent-mode iteration), not the rules.

## Notes

- Continue's MCP support is evolving. The exact YAML/JSON shape, transport type names (`streamable-http` vs `http` vs `stdio`), and config keys (`mcpServers` vs `experimental.modelContextProtocolServers`) have varied across versions. When upgrading Continue, re-validate the config against the docs.
- Continue rules don't have a per-file install location like Cursor `.cursor/rules/*.mdc` or Cline `.clinerules/*.md`; they're inline in the YAML config or referenced via `@file`.
