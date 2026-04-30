---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team memory (.continue/, project docs), only for external-dependency problems. See https://runlog.org.
---

## Runlog (Continue.dev adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team-memory tools (Continue rules, CLAUDE.md, mem0); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor. Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules every Runlog client skill MUST follow
- `skills/runlog-author/SKILL.md` — write-side companion

This file is the **Continue-flavored read skill body**. The vendor-specific bits are: how Continue loads rules through `config.yaml` / `config.json`, how MCP servers are configured, and how Continue's agent mode dispatches MCP tool calls.

## When to Use This Skill

### Use it when

- You are about to debug or implement against a third-party system, **and**
- The team's own memory (`.continue/config.yaml` rules, project docs in the workspace, prior conversation context) does not already cover the specific problem.

### Do NOT use it when

- The problem concerns internal or proprietary code, team-specific conventions, or codebase patterns.
- The answer could legitimately live in `.continue/` rules. If it could, it belongs there.

The server rejects internal-domain submissions at `runlog_submit` time with `scope_rule`. Misclassification wastes a request.

## Decision Flow

```text
Continue agent encounters problem
        │
        ▼
  Check .continue/ rules + project docs
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
              │   Solve directly, update Continue rules, done
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
          │ runlog_submit (via runlog-author)   Update Continue rules
          │
          ▼
    runlog_report (with session_manifest)
```

## The Four-Point Client Contract

Canonical source: `skills/common/four-point-client-contract.md`.

1. **Continue MUST consult `.continue/` rules + project docs before calling `runlog_search`.**
2. **Continue MUST only call `runlog_search` when the problem has been classified as external-dependency.**
3. **Continue MUST route new learnings to the correct layer.** Internal → `.continue/config.yaml` rules. External → `runlog_submit` (via the companion `runlog-author` skill).
4. **Continue MUST maintain a session dependency manifest.** Continue's agent state survives across the agent-mode session; carry the manifest there.

## Tool Reference

### `runlog_search`

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | Natural-language description |
| `domain` | string[] | no | e.g. `["stripe", "python"]` |
| `version_constraints` | object | no | Recorded but not enforced in v0.1 |
| `limit` | integer | no | 1–50 (default 10) |

**Failure response:** `error.type` ∈ {`auth.missing_key`, `auth.invalid_key`, `auth.suspended`, `rate_limit`, `internal_error`}.

### `runlog_submit`

Use the companion `runlog-author` skill (`skills/continue/runlog-author.md`) — it drives the local Ed25519-signed verifier so the entry lands `verified` rather than `unverified`.

### `runlog_report`

Always call after applying an entry.

| Parameter | Type | Required |
|---|---|---|
| `entry_id` | string | yes |
| `outcome` | `"success"` or `"failure"` | yes |
| `session_manifest` | object | no |
| `error_context` | object | no |

For the manifest wire shape, see `runlog-schema/manifest.schema.yaml`.

## Authoring New Findings

Run the companion `runlog-author` skill (`skills/continue/runlog-author.md`) which drives the local verifier. Direct `runlog_submit` without a verifier-signed bundle lands the entry as `unverified` (lower trust); the author skill makes it `verified` end-to-end.

## Setup

### 1. Register and receive your API key

Visit https://runlog.org/register, enter your email, click the verification link. You receive `sk-runlog-<id12>-<secret32>` (55 characters, shown once).

### 2. Set the environment variable

```sh
export RUNLOG_API_KEY="sk-runlog-<your-key>"
```

### 3. Add Runlog to Continue's config

Continue 1.0+ uses YAML configuration at `~/.continue/config.yaml` (global) or `.continue/config.yaml` (workspace). Older versions used `~/.continue/config.json`. Both forms are documented below.

#### YAML (preferred, Continue 1.0+)

Add to `~/.continue/config.yaml`:

```yaml
mcpServers:
  - name: runlog
    type: streamable-http
    url: https://api.runlog.org/mcp
    requestOptions:
      headers:
        Authorization: "Bearer ${RUNLOG_API_KEY}"

rules:
  - name: runlog
    rule: |
      <paste the body of skills/continue/SKILL.md here, or reference it via @file>
```

#### JSON (legacy)

Add to `~/.continue/config.json`:

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

> **VERIFY:** Continue's MCP config schema has evolved across versions (`experimental.modelContextProtocolServers` → `mcpServers`). Confirm against the current Continue docs at https://docs.continue.dev/ before publishing your config. The exact key name and shape may differ in the version you have installed.

### 4. Install this skill as a Continue rule

Continue 1.0+ loads every `.md` file under `.continue/rules/` (workspace) or `~/.continue/rules/` (global) into the agent's context. The simplest install drops the body there:

```sh
mkdir -p .continue/rules
cp skills/continue/SKILL.md .continue/rules/runlog.md
```

This is also the path the `npx @runlog/install continue --write` installer writes to.

For older Continue versions (or when you want everything in one place), Continue's `rules` section in `config.yaml` accepts inline rule blocks or `@file` references:

```yaml
rules:
  - name: runlog
    rule: |
      Consult Runlog (cross-org registry of third-party-system gotchas) AFTER checking team memory and only for external-dependency problems. Tools: runlog_search, runlog_submit, runlog_report. Full body: see skills/continue/SKILL.md in the workspace.
```

For the full body, copy `skills/continue/SKILL.md` content into the `rule:` block (note YAML escaping for the multi-line content). Or commit the file to the workspace and reference it via Continue's context provider system.

### 5. Verify the connection

Open Continue's panel and check the tool list — `runlog_search`, `runlog_submit`, `runlog_report` should be available. Or ask: *"Can you call runlog_search with the query 'stripe webhook'?"*

If the tools don't appear, confirm `RUNLOG_API_KEY` is set in the shell that launched VS Code (or your IDE) and reload the Continue extension.

## Rate Limits

| Tool | Limit (per 24h) |
|---|---|
| `runlog_search` | 1000 |
| `runlog_submit` | 50 |
| `runlog_report` | 500 |

Server returns HTTP 429 with `error.type: "rate_limit"` and `error.retry_after_seconds`.

## v0.1 Caveats

- Submitted entries land at `status="unverified"` unless submitted via the `runlog-author` skill.
- Cassette capture for integration entries is in flight (Phase 2).
- Coarse hard-reject sanitization in v0.1; full default-deny allow-list is in soft-launch `warn` mode.

## Further Reading

| Document | Read when working on |
|---|---|
| `skills/runlog-author/SKILL.md` | Submitting verified entries |
| `skills/common/four-point-client-contract.md` | Cross-vendor contract |
| `runlog-docs/04-submission-format.md` | Entry YAML, placeholders, verification types |
| `runlog-docs/07-mcp-interface.md` | Canonical client contract |

---

Skill version tracks the runlog-skills repo tag. Cross-vendor adapter under `[F25]`.
