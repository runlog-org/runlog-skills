---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team memory (project guidelines, AI Assistant custom prompts), only for external-dependency problems. See https://runlog.org.
---

## Runlog (JetBrains AI Assistant adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team-memory tools (JetBrains AI guidelines, custom prompts, project docs); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor. Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules
- `skills/runlog-author/SKILL.md` — write-side companion

This file is the **JetBrains AI Assistant-flavored read skill body**. JetBrains AI Assistant's MCP support and configuration model varies across the IDE family (IntelliJ IDEA, PyCharm, WebStorm, GoLand, Rider, RubyMine, PhpStorm, CLion, RustRover) and across plugin versions.

> **VERIFY against current JetBrains AI Assistant docs** before publishing your config. The JetBrains AI plugin's MCP integration is evolving — exact menu paths, config file locations, and supported transports may differ from what's described below.

## When to Use This Skill

### Use it when

- About to debug or implement against a third-party system, **and**
- Team memory (project guidelines, AI Assistant custom prompts, project docs in the workspace) does not cover the problem.

### Do NOT use it when

- The problem concerns internal/proprietary code or team-specific conventions.
- The answer could legitimately live in your project's AI Assistant guidelines. Then it belongs there.

The server rejects internal-domain submissions with `scope_rule`. Misclassification wastes a request.

## Decision Flow

```
JetBrains AI Assistant encounters problem
        │
        ▼
  Check project AI guidelines + custom prompts + project docs
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
           │   Solve directly, propose addition to AI guidelines, done
           ▼
     runlog_search (via MCP)
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

1. **AI Assistant MUST consult project AI guidelines + custom prompts + project docs before calling `runlog_search`.**
2. **AI Assistant MUST only call `runlog_search` when the problem has been classified as external-dependency.**
3. **AI Assistant MUST route new learnings to the correct layer.** Internal → propose an update to the project's AI guidelines. External → `runlog_submit` (via `runlog-author`).
4. **AI Assistant MUST maintain a session dependency manifest.** AI Assistant chat sessions are the unit; carry the manifest across turns and flush via `runlog_report`.

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

Use the companion `runlog-author` skill (`skills/jetbrains/runlog-author.md`) — it drives the local Ed25519-signed verifier so the entry lands `verified` rather than `unverified`. Direct calls without the verifier are accepted but lower-trust.

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

### 3. Add Runlog as an MCP server in JetBrains AI Assistant

JetBrains AI Assistant's MCP integration exposes server config through Settings. The path varies across IDE products:

- **IntelliJ IDEA / PyCharm / WebStorm / GoLand etc.**: Settings (or Preferences on macOS) → Tools → AI Assistant → MCP Servers (or similar; the exact menu item may be named differently across versions).

> **VERIFY:** The exact settings path and config schema is plugin-version-dependent. Check the JetBrains AI Assistant documentation for your installed plugin version.

For plugins that read MCP config from a JSON file, the pattern is consistent with other vendors:

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

For plugins that configure servers through a settings UI: enter the URL `https://api.runlog.org/mcp`, transport `http` or `streamable-http`, and add a custom header `Authorization: Bearer ${RUNLOG_API_KEY}` (or the literal key).

### 4. Install this skill as an AI Assistant guideline

JetBrains AI Assistant supports project-scoped guidelines. The exact mechanism varies by version:

- **Newer versions**: project AI rules / guidelines stored in `.junie/guidelines.md` or `.idea/aiAssistant.xml` (varies; check Settings → Tools → AI Assistant → Guidelines).
- **Custom prompts**: AI Assistant's prompt library can hold the body of this skill as a custom prompt invoked by name.

Recommended: place the body of this file in the project's AI guidelines surface so all AI Assistant interactions on the project pick it up.

### 5. Verify the connection

Open AI Assistant chat (the "AI" tool window or sidebar). Check the available tools — `runlog_search`, `runlog_submit`, `runlog_report` should appear when MCP is wired correctly. Or ask:

> *Can you call runlog_search with the query "stripe webhook"?*

If the tools don't appear, restart the IDE and confirm `RUNLOG_API_KEY` is set in the shell that launched the IDE (or in the IDE's environment-variable settings).

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

## JetBrains-specific notes

- The JetBrains AI Assistant's MCP support quality varies by IDE product and plugin version. Some products may not yet expose MCP tool calls in the chat surface; in that case the read skill cannot run end-to-end and you should track the upstream plugin updates.
- JetBrains AI Assistant offers Junie (the agent mode) which supports tool use; classic AI Assistant chat may not. Confirm the agent-mode surface is what you're using.
- Settings → Tools → AI Assistant gives you per-IDE control over which MCP servers are enabled. Useful for selectively scoping Runlog access to specific projects (e.g. only enable for projects that integrate with public APIs).

## Further Reading

- `skills/runlog-author/SKILL.md` — submitting verified entries
- `skills/common/four-point-client-contract.md` — cross-vendor contract
- `runlog-docs/04-submission-format.md` — entry YAML, placeholders, verification types
- JetBrains AI Assistant docs — https://www.jetbrains.com/help/ai-assistant/

---

Skill version tracks the runlog-skills repo tag. Cross-vendor adapter under `[F25]`.
