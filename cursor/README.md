# Cursor — Runlog skill adapter (placeholder)

This directory is a placeholder for the Cursor adapter of the Runlog client skills. **Not yet implemented.**

Cursor is the highest-priority vendor target after Claude Code (largest agent-tool user base). Tracker: `[F25] Multi-vendor MCP skill coverage` in the project backlog.

## What lands here when implemented

- **Read side** — adapter wrapping `runlog_search` / `runlog_report`, mirroring [`../claude-code/SKILL.md`](../claude-code/SKILL.md). Vendor-specific glue: Cursor's MCP config location, `.cursorrules` / `cursor/rules/*.mdc` as the team-memory surface to check before calling `runlog_search`, and how the dependency manifest is persisted across the agent's tool-use turns.
- **Write side** — adapter wrapping [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md). The canonical author body is inherited byte-for-byte; this adapter swaps orchestration glue (Cursor's tool-use API, agent-mode iteration, command palette invocation, how local Bash is dispatched).

## Invariants every Cursor adapter MUST honour

- The four rules in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
- The author-side rules in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) (when shipping the write skill).

The contract is framework-agnostic; the adapter swaps glue, not the rules.
