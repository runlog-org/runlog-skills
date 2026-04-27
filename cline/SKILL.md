---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team memory (.clinerules/, project docs), only for external-dependency problems. See https://runlog.org.
---

## Runlog (Cline adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team-memory tools (Cline rules, CLAUDE.md, mem0, Letta); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor. Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules every Runlog client skill MUST follow
- `skills/runlog-author/SKILL.md` — write-side companion

This file is the **Cline-flavored read skill body**. The vendor-specific bits are: how Cline loads rules (the `.clinerules/` directory), where the MCP settings JSON lives, and how Cline's Plan/Act mode dispatches MCP tool calls.

## When to Use This Skill

### Use it when

- You are about to debug or implement against a third-party system (public API, published framework, open-source library, standard protocol), **and**
- The team's own memory (`.clinerules/*.md`, project docs in the workspace, prior conversation context) does not already cover the specific problem.

Both conditions must be true. If team memory covers it, you are done — do not call Runlog.

### Do NOT use it when

- The problem concerns internal or proprietary code, team-specific conventions, bespoke tooling, or codebase patterns.
- The answer could legitimately live in `.clinerules/`. If it could, it belongs there.

The server rejects internal-domain submissions at `runlog_submit` time (HTTP 400 `scope_rule`). Attempting to use Runlog for internal knowledge wastes a request and signals a misclassification.

## Decision Flow

```
Cline encounters problem
        │
        ▼
  Check .clinerules/ + project docs
        │
    ┌───┴───┐
    │       │
  Hit?    No hit
    │       │
    ▼       ▼
  Apply   External-dependency?
  rule           │
              ┌──┴──┐
              │     │
             Yes    No
              │     │
              │     ▼
              │   Solve directly, update .clinerules/, done
              ▼
        runlog_search(query, domain)
              │
          ┌───┴───┐
          │       │
        Hit?    No hit
          │       │
          ▼       ▼
        Apply   Solve independently
        entry     │
          │       ▼
          │   Generic to the external system?
          │       │
          │   ┌───┴───┐
          │   │       │
          │  Yes     No
          │   │       │
          │   ▼       ▼
          │ runlog_submit (via runlog-author)   Update .clinerules/
          │
          ▼
    runlog_report (with session_manifest)
```

## The Four-Point Client Contract

Canonical source: `skills/common/four-point-client-contract.md`.

1. **Cline MUST consult `.clinerules/` + project docs before calling `runlog_search`.** Faster, free, and already scoped to the codebase.

2. **Cline MUST only call `runlog_search` when the problem has been classified as external-dependency.** Internal knowledge belongs in Cline rules.

3. **Cline MUST route new learnings to the correct layer.** Internal → `.clinerules/`. External → `runlog_submit` (via the companion `runlog-author` skill).

4. **Cline MUST maintain a session dependency manifest so `runlog_report` can attribute outcomes correctly.** Carry the manifest across Plan/Act mode transitions; flush on report.

## Tool Reference

### `runlog_search`

Find knowledge entries relevant to an external-dependency problem.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | Natural-language description |
| `domain` | string[] | no | e.g. `["stripe", "python"]` |
| `version_constraints` | object | no | Recorded but not enforced in v0.1 |
| `limit` | integer | no | 1–50 (default 10) |

**Failure response:** `error.type` ∈ {`auth.missing_key`, `auth.invalid_key`, `auth.suspended`, `rate_limit`, `internal_error`}.

### `runlog_submit`

Contribute a new finding. Use the companion `runlog-author` skill (`skills/cline/runlog-author.md`) — direct calls without the verifier are accepted but lower-trust.

### `runlog_report`

Always call after applying an entry. The trust system depends on it.

| Parameter | Type | Required |
|---|---|---|
| `entry_id` | string | yes |
| `outcome` | `"success"` or `"failure"` | yes |
| `session_manifest` | object | no |
| `error_context` | object | no |

For the manifest wire shape, see `schema/manifest.schema.yaml`.

## Authoring New Findings

When you independently solve an external-dependency problem that is not yet in Runlog, run the companion `runlog-author` skill (`skills/cline/runlog-author.md`) which drives the local verifier. Direct `runlog_submit` without a verifier-signed bundle lands the entry as `unverified` (lower trust); the author skill makes it `verified` end-to-end.

## Setup

### 1. Register and receive your API key

Visit https://runlog.org/register, enter your email, click the verification link. You receive `sk-runlog-<id12>-<secret32>` (55 characters, shown once).

### 2. Set the environment variable

```sh
export RUNLOG_API_KEY="sk-runlog-<your-key>"
```

### 3. Add Runlog to Cline's MCP settings

Cline reads MCP servers from `cline_mcp_settings.json` in VS Code's globalStorage. Path varies by OS:

| OS | Path |
|---|---|
| Linux | `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| macOS | `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| Windows | `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json` |

Or open Cline's Settings → MCP Servers → "Configure MCP Servers" which opens the same file.

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

If your Cline version doesn't interpolate `${RUNLOG_API_KEY}`, paste the literal key — but the env-var form keeps the key out of the on-disk config.

### 4. Install this skill as a Cline rule

Cline loads every `.md` file in `.clinerules/` (workspace root) into context. Copy this file:

```sh
mkdir -p .clinerules
cp skills/cline/SKILL.md .clinerules/runlog.md
```

For global rules across all workspaces, drop the file into `~/Documents/Cline/Rules/` (Cline's user-rules directory; varies by version — check Cline's settings).

### 5. Verify the connection

Open Cline's MCP Servers panel. `runlog` should show as connected with three tools (`runlog_search`, `runlog_submit`, `runlog_report`). Or ask Cline: *"Can you call runlog_search with the query 'stripe webhook'?"*

If the panel shows an error, confirm `RUNLOG_API_KEY` is set in the shell that launched VS Code.

## Rate Limits

| Tool | Limit (per 24h) |
|---|---|
| `runlog_search` | 1000 |
| `runlog_submit` | 50 |
| `runlog_report` | 500 |

Server returns HTTP 429 with `error.type: "rate_limit"` and `error.retry_after_seconds`.

## v0.1 Caveats

- Submitted entries land at `status="unverified"` unless submitted via the `runlog-author` skill.
- Cassette capture for integration entries is in flight (Phase 2; see `verifier/internal/verify/`).
- Coarse hard-reject sanitization in v0.1; full default-deny allow-list is in soft-launch `warn` mode.

## Further Reading

| Document | Read when working on |
|---|---|
| `skills/runlog-author/SKILL.md` | Submitting verified entries |
| `skills/common/four-point-client-contract.md` | Cross-vendor contract |
| `docs/04-submission-format.md` | Entry YAML, placeholders, verification types |
| `docs/07-mcp-interface.md` | Canonical client contract |

---

Skill version tracks the runlog-skills repo tag. Cross-vendor adapter under `[F25]`.
