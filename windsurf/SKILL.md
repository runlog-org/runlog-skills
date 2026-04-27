---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team memory (.windsurfrules, Windsurf memories), only for external-dependency problems. See https://runlog.org.
---

## Runlog (Windsurf adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team-memory tools (Windsurf rules, Windsurf memories, CLAUDE.md, mem0); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor. Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules
- `skills/runlog-author/SKILL.md` — write-side companion

This file is the **Windsurf-flavored read skill body**.

## When to Use This Skill

### Use it when

- About to debug or implement against a third-party system, **and**
- Team memory (`.windsurfrules`, Windsurf memories, project docs) does not already cover the problem.

### Do NOT use it when

- The problem concerns internal/proprietary code or team-specific conventions.
- The answer could legitimately live in `.windsurfrules` or Windsurf memories. Then it belongs there.

The server rejects internal-domain submissions at `runlog_submit` time with `scope_rule`.

## Decision Flow

```
Cascade encounters problem
        │
        ▼
  Check .windsurfrules + Windsurf memories + project docs
        │
    ┌───┴───┐
    │       │
  Hit?    No hit
    │       │
    ▼       ▼
  Apply   External-dependency?
              │
           ┌──┴──┐
          Yes    No
           │     │
           │     ▼
           │   Solve directly, update .windsurfrules / save memory, done
           ▼
     runlog_search
           │
       ┌───┴───┐
     Hit?    No hit
       │       │
     Apply   Solve, then runlog_submit (via runlog-author) if generic
       ▼
   runlog_report
```

## The Four-Point Client Contract

Canonical: `skills/common/four-point-client-contract.md`.

1. **Cascade MUST consult `.windsurfrules` + memories + project docs before calling `runlog_search`.**
2. **Cascade MUST only call `runlog_search` when the problem has been classified as external-dependency.**
3. **Cascade MUST route new learnings to the correct layer.** Internal → `.windsurfrules` or save as a Windsurf memory. External → `runlog_submit` (via `runlog-author`).
4. **Cascade MUST maintain a session dependency manifest.** Carry across Cascade turns; flush on report.

## Tool Reference

### `runlog_search`

| Parameter | Type | Required |
|---|---|---|
| `query` | string | yes |
| `domain` | string[] | no |
| `version_constraints` | object | no |
| `limit` | integer | no (default 10) |

**Failure:** `error.type` ∈ {`auth.missing_key`, `auth.invalid_key`, `auth.suspended`, `rate_limit`, `internal_error`}.

### `runlog_submit`

Use the companion `runlog-author` skill (`skills/windsurf/runlog-author.md`).

### `runlog_report`

Always call after applying an entry.

| Parameter | Type | Required |
|---|---|---|
| `entry_id` | string | yes |
| `outcome` | `"success"` or `"failure"` | yes |
| `session_manifest` | object | no |
| `error_context` | object | no |

For the manifest wire shape, see `schema/manifest.schema.yaml`.

## Setup

### 1. Register and receive your API key

Visit https://runlog.org/register, click the verification email link. You receive `sk-runlog-<id12>-<secret32>` (shown once).

### 2. Set the environment variable

```sh
export RUNLOG_API_KEY="sk-runlog-<your-key>"
```

### 3. Add Runlog to Windsurf's MCP config

Windsurf reads MCP server config from `~/.codeium/windsurf/mcp_config.json`. Edit the file (create if missing):

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

Or open Windsurf → Settings → Cascade → Plugins → "Configure" which opens the same file.

> **VERIFY:** Windsurf's MCP config path and schema have evolved. Confirm against the current Windsurf docs before publishing.

### 4. Install this skill as a Windsurf rule

Drop the body into `.windsurfrules` at the workspace root:

```sh
cp skills/windsurf/SKILL.md .windsurfrules
```

Or for global rules across all workspaces, paste the body into Windsurf → Settings → Cascade → Rules → "Global Rules" and save.

### 5. Verify the connection

Open Cascade and check the available tools — `runlog_search`, `runlog_submit`, `runlog_report` should appear. Or ask Cascade: *"Can you call runlog_search with the query 'stripe webhook'?"*

If the tools don't appear, restart Windsurf and confirm `RUNLOG_API_KEY` is set in the shell that launched it.

## Rate Limits

| Tool | Limit (per 24h) |
|---|---|
| `runlog_search` | 1000 |
| `runlog_submit` | 50 |
| `runlog_report` | 500 |

## v0.1 Caveats

- Submitted entries land at `status="unverified"` unless submitted via `runlog-author`.
- Cassette capture for integration entries is in flight.
- Coarse hard-reject sanitization in v0.1.

## Further Reading

- `skills/runlog-author/SKILL.md` — submitting verified entries
- `skills/common/four-point-client-contract.md` — cross-vendor contract
- `docs/04-submission-format.md` — entry YAML, placeholders, verification types

---

Skill version tracks the runlog-skills repo tag. Cross-vendor adapter under `[F25]`.
