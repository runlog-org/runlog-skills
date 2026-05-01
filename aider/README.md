# Aider — Runlog skill adapter

**Status:** ✅ shipped, with caveats. Aider's MCP support is evolving; verify against Aider's current docs before publishing the config. Read side is operational once Aider has MCP wired; write side is operational once F24 prerequisites land too.

Aider adapter of the Runlog client skills. Aider is CLI-native and operates on a diff-cycle model rather than an agent panel — the orchestration shape differs from IDE-based vendors. Tracker: `[F25] Multi-vendor MCP skill coverage`.

## Files

| File | Purpose |
|---|---|
| [`SKILL.md`](./SKILL.md) | Read-side skill body — install in `CONVENTIONS.md` or via `--read` |
| [`runlog-author.md`](./runlog-author.md) | Write-side adapter |
| [`runlog-harvest.md`](./runlog-harvest.md) | Harvest skill — end-of-session retrospective submission flow |

## Quickstart

1. **Get an API key** at https://runlog.org/register and set:

   ```sh
   export RUNLOG_API_KEY="sk-runlog-<your-key>"
   ```

2. **Add Runlog as an MCP server in Aider.** In `.aider.conf.yml` (per-project) or `~/.aider.conf.yml` (global):

   ```yaml
   mcp-servers:
     - name: runlog
       transport: streamable-http
       url: https://api.runlog.org/mcp
       headers:
         Authorization: "Bearer ${RUNLOG_API_KEY}"
   ```

   > **VERIFY against current Aider docs.** Aider's MCP integration is evolving; the exact YAML shape and CLI flags differ across versions. https://aider.chat/docs/

3. **Install the read-side skill.** Either append to `CONVENTIONS.md`:

   ```sh
   echo '' >> CONVENTIONS.md
   cat skills/aider/SKILL.md >> CONVENTIONS.md
   ```

   Or as a separate file referenced via `--read`:

   ```sh
   mkdir -p .aider
   cp skills/aider/SKILL.md .aider/runlog.md
   ```

   Then in `.aider.conf.yml`:

   ```yaml
   read:
     - .aider/runlog.md
   ```

4. **(Optional) Install the write-side skill** for verified submissions — same shape as above with `runlog-author.md`. Then build the verifier and generate a keypair (see SKILL.md §Setup).

5. **(Optional) Install the harvest skill** for end-of-session retrospective submission — same shape as above with `runlog-harvest.md` (append to `CONVENTIONS.md` or drop at `.aider/runlog-harvest.md` and reference via `read:`). Invoke before `/exit` with `/ask harvest this session to runlog`. Same verifier prerequisites as the write-side skill.

6. **Verify** in an Aider session:

   ```text
   > Can you call runlog_search with the query "stripe webhook"?
   ```

## Cross-vendor invariants

Every Aider adapter MUST honour:

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md).
- The harvest-side rules in [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) (when running the harvest skill).

The contract is framework-agnostic; Aider adapters swap orchestration glue (CLI lifetime as the session boundary, `/run` for verifier dispatch, `CONVENTIONS.md` rule loading), not the rules.

## Notes

- Aider's MCP support is newer than the IDE-based vendors'. If your installed Aider version doesn't yet support MCP, the read skill cannot run end-to-end — track upstream and re-evaluate when MCP is mainline.
- Aider sessions are bounded by the CLI lifetime; the dependency manifest carries within the chat. Call `runlog_report` before `/exit` to flush outcomes for entries you applied.
- For users who want minimum approval friction in the write-side verification loop: Aider's `--yes-always` flag auto-approves `/run` invocations — but it applies to all commands, not just `runlog-verifier`. Consider a session-bound flag rather than enabling globally. Auto-approving the local verifier is fine in principle (deterministic, local, signed); auto-approving `runlog_submit` is **NOT recommended**, as submission is the final review gate and a prompt-injected context could otherwise publish without your review.
