---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team memory (.github/copilot-instructions.md, project docs), only for external-dependency problems. See https://runlog.org.
---

## Runlog (VS Code + GitHub Copilot adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team-memory tools (Copilot instructions, CLAUDE.md, mem0); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor. Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules
- `skills/runlog-author/SKILL.md` — write-side companion

This file is the **VS Code + Copilot-flavored read skill body**. The vendor-specific bits are: how Copilot loads instructions (`.github/copilot-instructions.md` and `.github/instructions/*.instructions.md`), how `.vscode/mcp.json` configures MCP servers, and how Copilot Chat's agent mode dispatches MCP tool calls.

## When to Use This Skill

### Use it when

- About to debug or implement against a third-party system, **and**
- Team memory (`.github/copilot-instructions.md`, `.github/instructions/`, project docs in the workspace, prior conversation context) does not cover the problem.

### Do NOT use it when

- The problem concerns internal/proprietary code or team-specific conventions.
- The answer could legitimately live in `.github/copilot-instructions.md`. Then it belongs there.

The server rejects internal-domain submissions with `scope_rule`. Misclassification wastes a request.

## Decision Flow

```
Copilot Chat encounters problem
        │
        ▼
  Check .github/copilot-instructions.md + .github/instructions/ + project docs
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
           │   Solve directly, propose addition to .github/copilot-instructions.md, done
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

1. **Copilot MUST consult `.github/copilot-instructions.md` + `.github/instructions/` + project docs before calling `runlog_search`.**
2. **Copilot MUST only call `runlog_search` when the problem has been classified as external-dependency.**
3. **Copilot MUST route new learnings to the correct layer.** Internal → propose an update to `.github/copilot-instructions.md` or a new `.github/instructions/<name>.instructions.md`. External → `runlog_submit` (via `runlog-author`).
4. **Copilot MUST maintain a session dependency manifest.** Copilot Chat's agent-mode session is the unit; carry the manifest across turns and flush via `runlog_report`.

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

Use the companion `runlog-author` skill (`skills/copilot/runlog-author.md`).

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

### 3. Add Runlog to VS Code's MCP config

VS Code reads MCP server config from `.vscode/mcp.json` (workspace) or User Settings (`mcp` field). Workspace-scoped is preferred when committing alongside the project.

`.vscode/mcp.json`:

```json
{
  "servers": {
    "runlog": {
      "type": "http",
      "url": "https://api.runlog.org/mcp",
      "headers": {
        "Authorization": "Bearer ${input:runlog-api-key}"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "runlog-api-key",
      "description": "Runlog API key (sk-runlog-...)",
      "password": true
    }
  ]
}
```

The `${input:...}` form prompts you for the key on first use and stores it in VS Code's secret store. Or use a literal `${env:RUNLOG_API_KEY}` if you prefer the env var:

```json
"Authorization": "Bearer ${env:RUNLOG_API_KEY}"
```

> **VERIFY:** VS Code's MCP config schema has evolved. Confirm the exact `servers` / `mcpServers` key name and the `type` enum against current VS Code docs.

### 4. Install this skill as a Copilot instruction

VS Code Copilot loads `.github/copilot-instructions.md` automatically when `github.copilot.chat.codeGeneration.useInstructionFiles` is `true` (default for newer versions).

**Pattern A — append to `.github/copilot-instructions.md`** (recommended for projects already using the file):

```sh
mkdir -p .github
echo '' >> .github/copilot-instructions.md
cat skills/copilot/SKILL.md >> .github/copilot-instructions.md
```

**Pattern B — separate scoped instruction** (recommended when you want Runlog to load only for certain file patterns):

```sh
mkdir -p .github/instructions
cp skills/copilot/SKILL.md .github/instructions/runlog.instructions.md
```

Add YAML frontmatter to scope the instruction (optional):

```yaml
---
applyTo: "**"
---
```

Or scope to specific patterns (e.g. only for files that interact with third-party APIs):

```yaml
---
applyTo: "src/integrations/**"
---
```

### 5. Verify the connection

Open Copilot Chat and switch to Agent mode. The available tools panel should list `runlog_search`, `runlog_submit`, `runlog_report`. Or ask:

```
@runlog can you call runlog_search with the query "stripe webhook"?
```

If the tools don't appear, run `MCP: List Servers` from the command palette and check the runlog server status. Confirm the API key was accepted on first prompt.

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

## VS Code-specific notes

- VS Code Copilot's agent mode is the surface that loads MCP tools; ask/edit modes are read-only and don't dispatch tool calls.
- The `.github/instructions/<name>.instructions.md` format supports `applyTo` frontmatter for glob-scoped instructions — useful when you want Runlog guidance only for files that interact with third-party APIs.
- `.vscode/mcp.json` is workspace-scoped; team members all get the same MCP config, but each developer enters their own API key on first use (stored in VS Code's per-user secret store).

## Further Reading

- `skills/runlog-author/SKILL.md` — submitting verified entries
- `skills/common/four-point-client-contract.md` — cross-vendor contract
- `docs/04-submission-format.md` — entry YAML, placeholders, verification types
- VS Code MCP docs — https://code.visualstudio.com/docs/copilot/

---

Skill version tracks the runlog-skills repo tag. Cross-vendor adapter under `[F25]`.
