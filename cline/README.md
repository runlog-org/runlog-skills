# Cline — Runlog skill adapter (placeholder)

This directory is a placeholder for the Cline adapter of the Runlog client skills. **Not yet implemented.**

Cline is the second-highest priority vendor target after Cursor — open-source and MCP-native, so the adapter is structurally simpler than the closed-source IDE plugins. Tracker: `[F25] Multi-vendor MCP skill coverage` in the project backlog.

## What lands here when implemented

- **Read side** — adapter wrapping `runlog_search` / `runlog_report`, mirroring [`../claude-code/SKILL.md`](../claude-code/SKILL.md). Vendor-specific glue: Cline's MCP server config in VS Code settings, `.clinerules` / workspace memory as the team-memory surface, and how the dependency manifest persists across Cline's plan/act mode transitions.
- **Write side** — adapter wrapping [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md). The canonical author body is inherited byte-for-byte; this adapter swaps orchestration glue (Cline's tool-execution surface, command-mode iteration, how local Bash is dispatched through Cline's terminal integration).

## Invariants every Cline adapter MUST honour

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) (when shipping the write skill).

The contract is framework-agnostic; the adapter swaps glue, not the rules.
