---
name: four-point-client-contract
description: The four rules every official Runlog MCP client skill MUST follow. Both read-side (skills/claude-code/SKILL.md) and write-side (skills/runlog-author/SKILL.md) inherit from this contract. Per-vendor adapters reference this file rather than re-authoring.
---

# The Four-Point Client Contract

The cross-vendor invariant for Runlog client skills. Originating spec: [`../../docs/07-mcp-interface.md`](https://github.com/runlog-org/runlog-docs/blob/main/07-mcp-interface.md) §10.4. Currently embodied in [`../claude-code/SKILL.md`](../claude-code/SKILL.md) (read side) and [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) (write side). Per-vendor adapters — Cursor, Cline, Continue, Windsurf, Aider, Copilot via MCP, JetBrains AI, Zed — MUST follow these four rules in their own framework. Violating any of them collapses Runlog into a weaker competitor to team-memory tools.

## The Four Rules

1. **The agent MUST consult team memory before calling `runlog_search`.** The team's own context (CLAUDE.md, Cursor rules, mem0, project docs, prior conversation) is faster, free, and already scoped to the codebase. Runlog is consulted only after team memory has no answer.

2. **The agent MUST only call `runlog_search` when the problem has been classified as external-dependency.** Internal knowledge — proprietary APIs, team conventions, bespoke tooling, codebase patterns — belongs in team memory. Calling `runlog_search` for internal problems wastes quota and pollutes the dependency manifest.

3. **The agent MUST route new learnings to the correct layer.** Knowledge about internal code or team conventions goes into team memory (CLAUDE.md update, project doc, etc.). Knowledge about a third-party system that other teams will independently hit goes to `runlog_submit` (via the `runlog-author` skill once its prerequisites land, or hand-authored YAML before then). Never cross the streams.

4. **The agent MUST maintain the session dependency manifest so `runlog_report` can attribute outcomes correctly.** Every entry retrieved from `runlog_search` and applied to a solve must be tracked in the manifest. The manifest is passed to `runlog_report` after the outcome is known. Without it, the telemetry that drives trust scores and confidence decay is incomplete.

Third-party skills that follow this contract may apply for official-compatible listing.

## How vendor adapters honour the contract

The contract is framework-agnostic. Per-vendor implementation glue varies:

- **Team-memory check (rule 1)** — Claude Code: `CLAUDE.md` files in the working directory. Cursor: `.cursorrules` and `cursor/rules/*.mdc`. Cline: `.clinerules` or workspace memory. Continue: `.continue/config.json` workspace context. The skill walks the vendor's idiomatic memory surface; `runlog_search` only fires after no hit.
- **Classification (rule 2)** — All vendors: a "before drafting" classifier that asks "is this third-party?" The shape is the same; the prompt is per-vendor.
- **Routing (rule 3)** — Per-vendor: how does the agent write back to team memory? Claude Code: edit `CLAUDE.md` directly. Cursor: append to `.cursorrules`. The skill's job is to route; the destination format is per-vendor.
- **Manifest (rule 4)** — All vendors: a session-scoped data structure tracking `kb_id`, `retrieved_at`, `status`. Persisted across the session, flushed via `runlog_report`. Per-vendor: where the manifest lives — in-memory only (Claude Code today), persistent on disk (vendors with project-scoped state).

## Companion documents

- [`runlog-author-contract.md`](./runlog-author-contract.md) — author-side cross-vendor invariants (extends this contract for the submission flow).
- `dependency-manifest.md` — wire shape for `session_manifest` (Pydantic model in `server/src/runlog/manifest/spec.py`, JSON Schema at `schema/manifest.schema.yaml`). *Tracked under [F25].*
- `reporting-conventions.md` — how outcomes are mapped to `runlog_report` calls. *Tracked under [F25].*

The two `*tracked under [F25]*` companions ship as part of the multi-vendor expansion. Today's adapters reference `docs/07-mcp-interface.md §10` and `schema/manifest.schema.yaml` directly until the extracted versions land.
