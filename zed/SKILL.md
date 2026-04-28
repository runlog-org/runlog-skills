---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team memory (.rules/, project docs), only for external-dependency problems. See https://runlog.org.
---

## Runlog (Zed adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team-memory tools (Zed rules, project docs, CLAUDE.md, mem0); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor. Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules
- `skills/runlog-author/SKILL.md` — write-side companion

This file is the **Zed-flavored read skill body**. The vendor-specific bits are: how Zed loads context (rules and slash commands), how `context_servers` configures MCP servers in `~/.config/zed/settings.json`, and how Zed Assistant's agent mode dispatches MCP tool calls.

## When to Use This Skill

### Use it when

- About to debug or implement against a third-party system, **and**
- Team memory (Zed rules, project docs, prior conversation context) does not cover the problem.

### Do NOT use it when

- The problem concerns internal/proprietary code or team-specific conventions.
- The answer could legitimately live in Zed rules. Then it belongs there.

The server rejects internal-domain submissions with `scope_rule`. Misclassification wastes a request.

## Decision Flow

```
Zed Assistant encounters problem
        │
        ▼
  Check Zed rules + project docs + chat history
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
           │   Solve directly, propose Zed rule addition, done
           ▼
     runlog_search (via context_server)
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

1. **Zed Assistant MUST consult Zed rules + project docs + chat history before calling `runlog_search`.**
2. **Zed Assistant MUST only call `runlog_search` when the problem has been classified as external-dependency.**
3. **Zed Assistant MUST route new learnings to the correct layer.** Internal → propose addition to Zed rules. External → `runlog_submit` (via `runlog-author`).
4. **Zed Assistant MUST maintain a session dependency manifest.** Zed Assistant chat is the session; carry the manifest across the chat and flush via `runlog_report`.

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

Use the companion `runlog-author` skill (`skills/zed/runlog-author.md`) — it drives the local Ed25519-signed verifier so the entry lands `verified` rather than `unverified`. Direct calls without the verifier are accepted but lower-trust.

### `runlog_report`

Always call after applying an entry.

| Parameter | Type | Required |
|---|---|---|
| `entry_id` | string | yes |
| `outcome` | `"success"` or `"failure"` | yes |
| `session_manifest` | object | no |
| `error_context` | object | no |

For the manifest wire shape, see `runlog-schema/manifest.schema.yaml`.

## Setup

### 1. Register and receive your API key

Visit https://runlog.org/register, click the verification email link. You receive `sk-runlog-<id12>-<secret32>` (shown once).

### 2. Set the environment variable

```sh
export RUNLOG_API_KEY="sk-runlog-<your-key>"
```

### 3. Add Runlog to Zed's context_servers config

Zed configures MCP servers via `context_servers` in `~/.config/zed/settings.json` (global) or `.zed/settings.json` (workspace). Zed historically supported only stdio-launched MCP servers; HTTP transport support has been added in newer versions.

#### HTTP transport (newer Zed versions)

```json
{
  "context_servers": {
    "runlog": {
      "source": "custom",
      "command": null,
      "url": "https://api.runlog.org/mcp",
      "headers": {
        "Authorization": "Bearer ${RUNLOG_API_KEY}"
      }
    }
  }
}
```

> **VERIFY against current Zed docs** at https://zed.dev/docs/. Zed's `context_servers` schema has evolved — the exact field names for HTTP transport (`url` / `transport` / `source`) may differ in your Zed version.

#### stdio bridge (older Zed versions or for stricter sandboxing)

If your Zed version doesn't yet support HTTP `context_servers`, run a small stdio-to-HTTP bridge locally. Use the `mcp-proxy` package or any equivalent:

```json
{
  "context_servers": {
    "runlog": {
      "command": {
        "path": "npx",
        "args": ["-y", "mcp-proxy", "--http", "https://api.runlog.org/mcp"],
        "env": {
          "MCP_PROXY_AUTH_HEADER": "Authorization: Bearer ${RUNLOG_API_KEY}"
        }
      }
    }
  }
}
```

The bridge approach also helps if you want to redact / log MCP traffic locally for debugging.

### 4. Install this skill as a Zed rule

Zed loads rules from a `.rules` file in the workspace root, or `~/.config/zed/rules.md` globally. Drop the body of this file:

```sh
# Project-scoped
cp skills/zed/SKILL.md .rules

# Or global
mkdir -p ~/.config/zed
cp skills/zed/SKILL.md ~/.config/zed/rules.md
```

Zed Assistant reads these rules into the chat context automatically.

> **VERIFY:** Zed's rule-file format and location is configurable; check Settings → Open Rules File for your version.

### 5. Verify the connection

Open Zed Assistant (Cmd+? / Ctrl+? on default keymap). The available tools panel or the `/tools` slash command should show `runlog_search`, `runlog_submit`, `runlog_report`. Or ask:

> *Can you call runlog_search with the query "stripe webhook"?*

If the tools don't appear, check the context_servers status (Settings → Context Servers, or via `:` command palette).

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

## Zed-specific notes

- Zed Assistant's slash commands (`/file`, `/tab`, `/symbols`, etc.) inject context into the chat. The Runlog skill body, when installed as a rule, is loaded automatically and doesn't need an explicit slash command.
- Zed's HTTP `context_servers` support is newer than its stdio support. If you hit issues, the stdio-bridge fallback (mcp-proxy or similar) is a reliable workaround that also lets you inspect MCP traffic locally.
- Workspace-scoped `.rules` is preferred when committing the Runlog skill alongside the project — every team member sees the same Runlog guidance without per-developer config.

## Further Reading

- `skills/runlog-author/SKILL.md` — submitting verified entries
- `skills/common/four-point-client-contract.md` — cross-vendor contract
- `runlog-docs/04-submission-format.md` — entry YAML, placeholders, verification types
- Zed Assistant docs — https://zed.dev/docs/

---

Skill version tracks the runlog-skills repo tag. Cross-vendor adapter under `[F25]`.
