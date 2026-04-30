---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team memory (.cursorrules, .cursor/rules/*.mdc, project docs), only for external-dependency problems. See https://runlog.org.
---

## Runlog (Cursor adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team-memory tools (Cursor rules, CLAUDE.md, mem0, Letta); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor (Claude Code, Cursor, Cline, Continue, Windsurf, Aider, Copilot, JetBrains, Zed). Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules every Runlog client skill MUST follow
- `skills/runlog-author/SKILL.md` — write-side companion (consulted via the `runlog-author` skill below)

This file is the **Cursor-flavored read skill body**. The vendor-specific bits are: how Cursor loads rules, where `.cursor/mcp.json` lives, which file is the team-memory surface to check first, and how Cursor's agent loop dispatches MCP tool calls.

## When to Use This Skill

### Use it when

- You are about to debug or implement against a third-party system (public API, published framework, open-source library, standard protocol), **and**
- The team's own memory (`.cursorrules`, `.cursor/rules/*.mdc`, project docs in the workspace, prior conversation context) does not already cover the specific problem.

Both conditions must be true. If team memory covers it, you are done — do not call Runlog.

### Do NOT use it when

- The problem concerns internal or proprietary code, team-specific conventions, bespoke tooling, or codebase patterns.
- The answer could legitimately live in `.cursorrules` / `.cursor/rules/`. If it could, it belongs there.
- You are uncertain whether the problem is internal or external — classify it first. When in doubt, check team memory; if team memory has nothing, then classify as external-dependency and proceed to `runlog_search`.

The server rejects internal-domain submissions at `runlog_submit` time (HTTP 400 `scope_rule`). Attempting to use Runlog for internal knowledge wastes a request and signals a misclassification.

## Decision Flow

Check team memory first, every time. Runlog is never the first call.

```text
Cursor agent encounters problem
        │
        ▼
  Check Cursor rules (.cursorrules / .cursor/rules/*.mdc) and project docs
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
              │   Solve directly, update Cursor rules, done
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
          │ runlog_submit (via runlog-author)   Update Cursor rules
          │
          ▼
    runlog_report (with session_manifest)
```

## The Four-Point Client Contract

Every official Runlog MCP client skill must follow these four rules. Violating any of them collapses Runlog into a weaker competitor to team-memory tools. Canonical source: `skills/common/four-point-client-contract.md`.

1. **Cursor MUST consult Cursor rules + project docs before calling `runlog_search`.** The team's own context is faster, free, and already scoped to the codebase. Runlog is consulted only after team memory has no answer.

2. **Cursor MUST only call `runlog_search` when the problem has been classified as external-dependency.** Internal knowledge — proprietary APIs, team conventions, bespoke tooling, codebase patterns — belongs in Cursor rules.

3. **Cursor MUST route new learnings to the correct layer.** Knowledge about internal code or team conventions goes into `.cursorrules` or `.cursor/rules/`. Knowledge about a third-party system that other teams will independently hit goes to `runlog_submit` (via the companion `runlog-author` skill, see below).

4. **Cursor MUST maintain a session dependency manifest so `runlog_report` can attribute outcomes correctly.** Every entry retrieved from `runlog_search` and applied to a solve must be tracked in the manifest. The manifest is passed to `runlog_report` after the outcome is known.

## Tool Reference

### `runlog_search`

Find knowledge entries relevant to an external-dependency problem.

**When to call:** After Cursor rules have no answer and the problem has been classified as external-dependency.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | Natural-language description of the problem |
| `domain` | string[] | no | Domain tags to narrow results, e.g. `["stripe", "python"]` |
| `version_constraints` | object | no | Version filters; not enforced in v0.1 but recorded |
| `limit` | integer | no | Max results, 1–50 (default 10) |

**Success response:** Object with `hits` (ranked entries with confidence scores, status, and submitter trust), `query_id`, and `used_filters`.

**Failure response:** Object with `error.type` set to one of: `auth.missing_key`, `auth.invalid_key`, `auth.suspended`, `rate_limit`, `internal_error`. On `rate_limit`, check `error.retry_after_seconds`.

### `runlog_submit`

Contribute a new finding about a third-party system's behaviour. **Use the companion `runlog-author` skill** (see `skills/runlog-author/SKILL.md`) — it drives the local Ed25519-signed verifier so the entry lands `verified` rather than `unverified`. Direct calls without the verifier are accepted but lower-trust.

### `runlog_report`

Report whether a retrieved entry worked in the caller's context. **Always call** after applying an entry — this is how the trust system learns. Failure reports are useful too.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `entry_id` | string | yes | The `unit_id` of the entry being reported on |
| `outcome` | string | yes | `"success"` or `"failure"` |
| `session_manifest` | object | no | Dependency manifest for provenance tracking |
| `error_context` | object | no | Optional error details; include for failure outcomes |

For the manifest wire shape, see `runlog-schema/manifest.schema.yaml`. Cursor adapters typically carry the manifest in agent-loop state across turns and flush on exit / on report.

## Authoring New Findings

When you independently solve an external-dependency problem that is not yet in Runlog, run the companion `runlog-author` skill to draft, locally verify, sign, and submit the entry. Canonical body: `skills/runlog-author/SKILL.md`. The Cursor wrapper lives at `skills/cursor/runlog-author.md` and adds Cursor-specific orchestration glue (how the agent invokes the verifier through Cursor's tool-use API, agent-loop iteration on verifier rejections).

The verifier requirement is structural — `CLAUDE.md` invariant #6 ("verification happens on the submitter's machine") and `runlog-docs/03-verification-and-provenance.md §5.3` step 4. Direct `runlog_submit` without a verifier-signed bundle lands the entry as `unverified` (lower trust); the author skill makes it `verified` end-to-end.

## Setup

### 1. Register and receive your API key

Visit https://runlog.org/register, enter your email address, and click the verification link. You will receive one API key in the form `sk-runlog-<id12>-<secret32>` (55 characters total). It is shown exactly once — copy it immediately.

### 2. Set the environment variable

Set `RUNLOG_API_KEY` in your shell environment:

```sh
export RUNLOG_API_KEY="sk-runlog-<your-key>"
```

Do not commit it to any config file. If you use a `.env` file for local development, add it to `.gitignore` first.

### 3. Install the Runlog MCP server

The recommended path uses Neon's [`add-mcp`](https://github.com/neondatabase/add-mcp) — a third-party CLI that reads Runlog's [Official MCP Registry](https://registry.modelcontextprotocol.io/) entry (`org.runlog/runlog`) and writes a working config to `~/.cursor/mcp.json` (or `.cursor/mcp.json` for project scope) without hand-editing:

```sh
npx add-mcp https://api.runlog.org/mcp -a cursor
```

Drop `-a cursor` to install across every detected MCP-capable agent on the machine; pass `-g` for a global config instead of project-scoped. `add-mcp` prompts for the `Authorization: Bearer …` header and writes the entry for you.

If you'd rather edit the config by hand (or `add-mcp` isn't available), Cursor reads MCP server configuration from `~/.cursor/mcp.json` (global, applies across all projects) or `.cursor/mcp.json` (project-scoped). Use the project-scoped form when committing the config alongside the project; use the global form for personal use.

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

If your Cursor version does not support environment-variable interpolation in headers, paste the literal key with a comment — but prefer the env-var form because the literal sits in a file on disk.

### 4. Install this skill as a Cursor rule

Cursor loads rules from `.cursor/rules/*.mdc` (workspace) or `~/.cursor/rules/*.mdc` (global). Copy this `SKILL.md` to either location and rename:

```sh
# Project-scoped
mkdir -p .cursor/rules
cp skills/cursor/SKILL.md .cursor/rules/runlog.mdc

# Or global
mkdir -p ~/.cursor/rules
cp skills/cursor/SKILL.md ~/.cursor/rules/runlog.mdc
```

Cursor's `.mdc` rules format honours the YAML frontmatter (`description` is used to decide when to load the rule); the frontmatter at the top of this file is already in that shape.

For older Cursor versions that use a single `.cursorrules` file at the workspace root, append the body of this file to that file instead.

### 5. Verify the connection

Open Cursor's MCP servers panel (Settings → Cursor Settings → MCP) and confirm `runlog` shows as **connected** with three tools listed (`runlog_search`, `runlog_submit`, `runlog_report`). Or ask the agent: *"Can you call runlog_search with the query 'stripe webhook'?"* — a connected server returns hits.

If the panel shows an error, confirm `RUNLOG_API_KEY` is set in the shell that launched Cursor and the key format matches `sk-runlog-<id12>-<secret32>`.

## Rate Limits

v0.1 enforces per-key sliding-window quotas. All windows are 24 hours.

| Tool | Limit |
|---|---|
| `runlog_search` | 1000 / day |
| `runlog_submit` | 50 / day |
| `runlog_report` | 500 / day |

When a limit is exceeded the server returns HTTP 429 with `error.type: "rate_limit"` and `error.retry_after_seconds`. Wait that many seconds before retrying.

## v0.1 Caveats

- **Submitted entries land at `status="unverified"`** unless submitted via the `runlog-author` skill (which drives the local verifier).
- **Cassette capture for integration entries deferred to Phase 2** — telemetry-only in v0.1.
- **Coarse hard-reject sanitization** in v0.1; the full default-deny allow-list is in soft-launch `warn` mode.

## Further Reading

| Document | Read when working on |
|---|---|
| `skills/runlog-author/SKILL.md` | Submitting verified entries |
| `skills/common/four-point-client-contract.md` | The cross-vendor contract |
| `runlog-docs/04-submission-format.md` | Entry YAML, placeholders, verification types |
| `runlog-docs/07-mcp-interface.md` | Canonical client contract |

---

Skill version: tracks the runlog-skills repo tag (currently unreleased). Cross-vendor adapter under `[F25]`.
