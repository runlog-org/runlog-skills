---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems. Consult AFTER team conventions (CONVENTIONS.md, project docs), only for external-dependency problems. See https://runlog.org.
---

## Runlog (Aider adapter)

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team conventions (`CONVENTIONS.md`, project docs); it does not replace them.

**Cross-vendor contract:** the contract this skill implements is identical across every supported vendor. Canonical sources:

- `skills/common/four-point-client-contract.md` — the four rules
- `skills/runlog-author/SKILL.md` — write-side companion

This file is the **Aider-flavored read skill body**. Aider is CLI-native, so the orchestration model differs from IDE-based agents — there's no agent panel or chat surface; Aider operates on diff cycles in the terminal.

## When to Use This Skill

### Use it when

- About to debug or implement against a third-party system, **and**
- Team conventions (`CONVENTIONS.md`, files Aider has been told to `--read`, prior conversation in the current Aider session) do not cover the problem.

### Do NOT use it when

- The problem concerns internal/proprietary code or team-specific conventions.
- The answer could legitimately live in `CONVENTIONS.md`. Then it belongs there.

The server rejects internal-domain submissions with `scope_rule`. Misclassification wastes a request.

## Decision Flow (Aider-shaped)

```
Aider receives /ask or /code about a problem
        │
        ▼
  Check CONVENTIONS.md + --read'd files + session history
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
           │   Solve directly, propose a CONVENTIONS.md addition
           ▼
     runlog_search (via MCP tool)
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

1. **Aider MUST consult `CONVENTIONS.md` + `--read`'d files + session history before calling `runlog_search`.** Aider's prompt context is the team-memory layer.
2. **Aider MUST only call `runlog_search` when the problem has been classified as external-dependency.**
3. **Aider MUST route new learnings to the correct layer.** Internal → propose a `CONVENTIONS.md` addition (Aider edits it as a normal file). External → `runlog_submit` (via the companion `runlog-author` skill).
4. **Aider MUST maintain a session dependency manifest.** Aider sessions are bounded by the CLI lifetime; carry the manifest in the Aider chat history and flush via `runlog_report` before exiting.

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

Use the companion `runlog-author` skill (`skills/aider/runlog-author.md`) — it drives the local Ed25519-signed verifier so the entry lands `verified` rather than `unverified`. Direct calls without the verifier are accepted but lower-trust.

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

### 3. Add Runlog as an MCP server in Aider

Aider's MCP support varies by version. Recent versions support MCP servers via `--mcp-server` flags or in `.aider.conf.yml`. Check the version installed:

```sh
aider --version
```

> **VERIFY against current Aider docs** at https://aider.chat/docs/ before publishing — Aider's MCP integration is evolving and the exact flag/config shape may differ from the example below.

In `.aider.conf.yml` (per-project) or `~/.aider.conf.yml` (global):

```yaml
mcp-servers:
  - name: runlog
    transport: streamable-http
    url: https://api.runlog.org/mcp
    headers:
      Authorization: "Bearer ${RUNLOG_API_KEY}"
```

Or via the CLI:

```sh
aider --mcp-server "runlog=https://api.runlog.org/mcp" \
      --mcp-header "runlog:Authorization=Bearer ${RUNLOG_API_KEY}"
```

If your Aider version does not support MCP yet, the read skill cannot run end-to-end on Aider; track the upstream and re-evaluate.

### 4. Install this skill as a CONVENTIONS reference

Aider's idiomatic "rules" surface is `CONVENTIONS.md` plus any `--read` files. Two install patterns work:

**Pattern A — append to CONVENTIONS.md:**

```sh
echo '' >> CONVENTIONS.md
cat skills/aider/SKILL.md >> CONVENTIONS.md
```

**Pattern B — separate file referenced via `--read`:**

```sh
cp skills/aider/SKILL.md .aider/runlog.md
```

Then in `.aider.conf.yml`:

```yaml
read:
  - .aider/runlog.md
```

Or via CLI:

```sh
aider --read .aider/runlog.md
```

Pattern B keeps `CONVENTIONS.md` focused on team-specific code conventions and Runlog as a separate concern.

### 5. Verify the connection

In Aider chat:

```
> Can you call runlog_search with the query "stripe webhook"?
```

A connected MCP server returns hits. If Aider says the tool isn't available, confirm the MCP config and that `RUNLOG_API_KEY` is set in the shell that launched Aider.

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

## Aider-specific notes

- Aider's default operation is `/code` (apply diff) and `/ask` (read-only). Both modes can call MCP tools when MCP is enabled.
- Aider does not maintain an agent loop across sessions — each `aider` invocation is a fresh chat. The session dependency manifest is bounded by the chat; flushing on exit means calling `runlog_report` before `/exit`.
- Token budget: Aider's chat context grows with conversation length. Keep `runlog_search` queries focused (use `domain` filters) so result payloads stay small.

## Further Reading

- `skills/runlog-author/SKILL.md` — submitting verified entries
- `skills/common/four-point-client-contract.md` — cross-vendor contract
- `runlog-docs/04-submission-format.md` — entry YAML, placeholders, verification types

---

Skill version tracks the runlog-skills repo tag. Cross-vendor adapter under `[F25]`.
