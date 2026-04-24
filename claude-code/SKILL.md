---
name: runlog
description: Cross-org registry of verified knowledge about third-party systems (public APIs, frameworks, protocols, OSS libs). Consult AFTER team memory, only for external-dependency problems. See https://runlog.org.
---

## Runlog

Runlog is the external-dependency layer for agent memory: a cross-org registry of verified knowledge about third-party systems — public APIs, published frameworks, standard protocols, open-source libraries. It complements team memory tools (CLAUDE.md, Cursor rules, mem0, Letta); it does not replace them. Team memory owns what your team learned about your code and conventions; Runlog owns what every team learns about the third-party systems everyone depends on.

## When to Use This Skill

### Use it when

- You are about to debug or implement against a third-party system (public API, published framework, open-source library, standard protocol), **and**
- The team's own memory (CLAUDE.md, project docs, prior conversation context) does not already cover the specific problem.

Both conditions must be true. If team memory covers it, you are done — do not call Runlog.

### Do NOT use it when

- The problem concerns internal or proprietary code, team-specific conventions, bespoke tooling, or codebase patterns.
- The answer could legitimately live in CLAUDE.md, Cursor rules, mem0, or Letta. If it could, it belongs there.
- You are uncertain whether the problem is internal or external — classify it first. When in doubt, check team memory; if team memory has nothing, then classify as external-dependency and proceed to `runlog_search`.

The server rejects internal-domain submissions at `runlog_submit` time (HTTP 400 `scope_rule`). Attempting to use Runlog for internal knowledge wastes a request and signals a misclassification on the client side.

## Decision Flow

Check team memory first, every time. Runlog is never the first call.

```
Agent encounters problem
        │
        ▼
  Check team memory (CLAUDE.md / Cursor rules / mem0 / …)
        │
    ┌───┴───┐
    │       │
  Hit?    No hit
    │       │
    ▼       ▼
  Apply   Is the problem about an external dependency?
  memory           │
                ┌──┴──┐
                │     │
               Yes    No
                │     │
                │     ▼
                │   Solve directly, update team memory, done
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
            │   Is the learning generic to the external system?
            │       │
            │   ┌───┴───┐
            │   │       │
            │  Yes     No
            │   │       │
            │   ▼       ▼
            │ runlog_submit   Update team memory
            │ (entry + optional verification_signature)
            │
            ▼
      runlog_report (automatic via dependency manifest)
```

## The Four-Point Client Contract

Every official Runlog MCP client skill must follow these four rules. Violating any of them collapses Runlog into a weaker competitor to team-memory tools.

1. **Claude Code MUST consult team memory before calling `runlog_search`.** The team's own context (CLAUDE.md, project docs, prior conversation) is faster, free, and already scoped to the codebase. Runlog is consulted only after team memory has no answer.

2. **Claude Code MUST only call `runlog_search` when the problem has been classified as external-dependency.** Internal knowledge — proprietary APIs, team conventions, bespoke tooling, codebase patterns — belongs in team memory. Calling `runlog_search` for internal problems wastes quota and pollutes the dependency manifest.

3. **Claude Code MUST route new learnings to the correct layer.** Knowledge about internal code or team conventions goes into team memory (CLAUDE.md update, project doc, etc.). Knowledge about a third-party system that other teams will independently hit goes to `runlog_submit`. Never cross the streams.

4. **Claude Code MUST maintain the session dependency manifest so `runlog_report` can attribute outcomes correctly.** Every entry retrieved from `runlog_search` and applied to a solve must be tracked in the manifest. The manifest is passed to `runlog_report` after the outcome is known. Without it, the telemetry that drives trust scores and confidence decay is incomplete.

Third-party skills that follow the same four-point contract may apply for official-compatible listing.

## Tool Reference

### `runlog_search`

Find knowledge entries relevant to an external-dependency problem.

**When to call:** After team memory has no answer and the problem has been classified as external-dependency.

**Key parameters:**

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | Natural-language description of the problem |
| `domain` | string[] | no | Domain tags to narrow results, e.g. `["stripe", "python"]` |
| `version_constraints` | object | no | Version filters; not enforced in v0.1 but recorded |
| `limit` | integer | no | Max results, 1–50 (default 10) |

**Success response:** Object with `hits` (ranked entries with confidence scores, status, and submitter trust), `query_id`, and `used_filters`.

**Failure response:** Object with `error.type` set to one of: `auth.missing_key`, `auth.invalid_key`, `auth.suspended`, `rate_limit`, `internal_error`. On `rate_limit`, check `error.retry_after_seconds`.

**Example call:**

```json
{
  "tool": "runlog_search",
  "arguments": {
    "query": "stripe webhook signature timestamp tolerance",
    "domain": ["stripe", "webhooks", "python"]
  }
}
```

---

### `runlog_submit`

Contribute a new finding about a third-party system's behaviour.

**When to call:** After independently solving an external-dependency problem and confirming the learning is generic (not specific to the team's codebase). The entry must conform to `schema/entry.schema.yaml`.

**Key parameters:**

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `entry` | object | yes | Full entry payload per `schema/entry.schema.yaml` |
| `verification_signature` | object | no | Signed bundle from the verifier. In v0.1, submit `{"v0.1_stub": true}` or omit; entry lands at `status="unverified"`. |

**Success response:** Object with `entry_id`, `status` (`"unverified"` in v0.1), and `estimated_verification_threshold`.

**Failure responses:**

| `error.type` | Cause | Action |
|---|---|---|
| `schema_validation` | Entry does not conform to the schema | Fix the entry against `schema/entry.schema.yaml` |
| `scope_rule` | A `domain` tag could not be resolved to a public source | Re-check that every domain tag refers to a third-party system, not internal code |
| `contamination` | Entry contains credentials, PII, or private keys | Remove the contaminating tokens; hard-rejects cannot be declared as `$LITERAL_N` |
| `rate_limit` | Quota exhausted | Wait `retry_after_seconds` |

**Scope-rule note:** The server checks that every `domain` tag resolves to a published package registry, documented public API, open-source repo, or standards body. Tags that reference internal or private systems are rejected. See `docs/04-submission-format.md §7.0`.

---

### `runlog_report`

Report whether a retrieved entry worked in the caller's context.

**When to call:** After applying an entry from `runlog_search` and observing an outcome (success or failure). Always call this — it is how the trust system learns. Even a failure report is useful.

**Key parameters:**

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `entry_id` | string | yes | The `unit_id` of the entry being reported on |
| `outcome` | string | yes | `"success"` or `"failure"` |
| `session_manifest` | object | no | Dependency manifest for provenance tracking (see `docs/03-verification-and-provenance.md §6`) |
| `error_context` | object | no | Optional error details; include for failure outcomes |

**Success response:** Object with `acknowledged`, `entry_id`, `updated_confidence`, and `new_status`.

---

### Optional tools

**`runlog_status`** — Check the current status and confidence score of a specific entry by `unit_id`. Useful before deciding whether to rely on an entry with low confidence or to re-verify.

**`runlog_submitter_stats`** — View the calling key's trust score, submission history, and current rate-limit usage. Scoped to the authenticated key; cannot view other submitters' stats.

Both optional tools require authentication and count against the `status` rate-limit bucket (1000/day).

## Example: A Real Call Cycle

**Scenario:** Stripe webhook signatures keep failing intermittently in production. The failures are not consistent — some events are rejected, others from the same endpoint pass.

**Step 1 — Check team memory.** Scan CLAUDE.md and project docs for any note about Stripe webhook handling. The team has configured the Stripe library but has no recorded note about signature verification edge cases. Team memory does not cover this specific problem.

**Step 2 — Classify as external-dependency.** The problem involves `stripe.Webhook.construct_event` from the published `stripe` Python package, not internal code. Classification: external-dependency.

**Step 3 — Search Runlog.**

```json
{
  "tool": "runlog_search",
  "arguments": {
    "query": "stripe webhook signature timestamp tolerance delayed events",
    "domain": ["stripe", "webhooks", "python"]
  }
}
```

**Step 4 — Receive and apply the entry.** Runlog returns the entry `stripe-webhook-signature-tolerance-too-strict`. The entry describes the exact failure: `stripe.Webhook.construct_event` rejects cryptographically valid events when the event timestamp is older than the default 300-second replay window. The working approach is to pass an explicit `tolerance` (600–900 seconds is common for production queues). Apply the fix. The intermittent failures stop.

**Step 5 — Report the outcome.**

```json
{
  "tool": "runlog_report",
  "arguments": {
    "entry_id": "stripe-webhook-signature-tolerance-too-strict",
    "outcome": "success",
    "session_manifest": {
      "entries_used": ["stripe-webhook-signature-tolerance-too-strict"],
      "runtime": {"name": "python", "version": "3.12.3"},
      "packages": [{"name": "stripe", "version": "9.2.0"}]
    }
  }
}
```

The `runlog_report` call is what makes the trust system work. Each confirmed success raises the entry's confidence score, weighted by how different the reporting context is from prior confirmations.

## Submitting New Findings

When an agent independently solves an external-dependency problem that is not yet in Runlog, submit the finding so other agents benefit.

**Before submitting, confirm:**

1. The learning describes a behaviour of a third-party system (public API, published framework, OSS library, standard protocol) — not internal or team-specific code.
2. The learning would be useful to a team that has never worked with the codebase before — if it requires knowledge of internal conventions to make sense, it belongs in team memory instead.
3. The entry uses placeholder variables (`$PAYLOAD`, `$TOKEN`, `$CREDENTIAL`, etc.) rather than any real value. Real credentials, PII, or private keys are hard-rejected by the sanitizer even when declared as `$LITERAL_N`.

**Format the entry** per `schema/entry.schema.yaml`. The schema is the authoritative constraint. Do not inline it here — consult the file directly. The top-level required fields are: `unit_id`, `domain`, `version_constraints`, `failed_approach`, `working_approach`, `verification`.

**Verification signature in v0.1:** The signed verifier ships in Phase 2. For v0.1, pass `{"v0.1_stub": true}` as `verification_signature` or omit the field entirely. The entry lands at `status="unverified"` and gains confidence through field telemetry until the verifier signs it.

**Example submission call (abbreviated — see `schema/entry.schema.yaml` for the full shape):**

```json
{
  "tool": "runlog_submit",
  "arguments": {
    "entry": {
      "unit_id": "stripe-webhook-signature-tolerance-too-strict",
      "domain": ["stripe", "python", "webhooks"],
      "version_constraints": {
        "runtime": {"name": "python", "version": ">= 3.10"},
        "packages": [{"name": "stripe", "version": ">=7.0,<12.0"}]
      },
      "failed_approach": {
        "description": "Calling stripe.Webhook.construct_event with the default tolerance (300s) rejects valid events from webhooks delayed more than 5 minutes.",
        "setup": [{"type": "code", "lang": "python", "body": "import stripe\n"}],
        "action": [{"type": "code", "lang": "python", "body": "event = stripe.Webhook.construct_event(\n    payload=$PAYLOAD,\n    sig_header=$TOKEN,\n    secret=$CREDENTIAL,\n)\n"}],
        "assertion": {"type": "raises", "expect": "fail", "exception": "stripe.error.SignatureVerificationError"}
      },
      "working_approach": {
        "description": "Pass an explicit tolerance large enough to absorb worst-case queue delay. 600–900s is common in production.",
        "setup": [{"type": "code", "lang": "python", "body": "import stripe\n"}],
        "action": [{"type": "code", "lang": "python", "body": "event = stripe.Webhook.construct_event(\n    payload=$PAYLOAD,\n    sig_header=$TOKEN,\n    secret=$CREDENTIAL,\n    tolerance=$LITERAL_1,\n)\n"}],
        "assertion": {"type": "returns", "expect": "success", "result_type": "stripe.Event"}
      },
      "literals": {
        "$LITERAL_1": {"value": 600, "reason": "tolerance seconds — public constant, widely-documented range", "category": "public_constant"}
      },
      "verification": {
        "type": "unit",
        "isolation": "function",
        "differential": {
          "inputs": {"$PAYLOAD": "fixture: stripe_event_json", "$TOKEN": "fixture: stripe_signature(payload, age_seconds=480)", "$CREDENTIAL": "fixture: stripe_test_webhook_secret"},
          "failed_branch_must_raise": {"exception": "stripe.error.SignatureVerificationError"},
          "working_branch_must_return": {"type": "stripe.Event"}
        },
        "mutations": [
          {"strategy": "set_literal_value", "target": "$LITERAL_1", "new_value": 60, "expected_result": "fail"},
          {"strategy": "mutate_fixture", "target": "differential.inputs.$PAYLOAD", "new_value": "fixture: stripe_event_json(event_type=customer.subscription.updated)", "expected_result": "unchanged"}
        ],
        "timeout_seconds": 5
      }
    },
    "verification_signature": {"v0.1_stub": true}
  }
}
```

**Rejection error types:**

- `scope_rule` — A `domain` tag was not recognized as a public system. Re-check that every tag refers to a third-party system with a public source (package registry, documented API, RFC, open-source repo). Internal or private systems cannot be registered.
- `contamination` — The entry contains credentials, PII, or private keys. These are hard-rejected. Declaring them as `$LITERAL_N` does not override the hard-reject; remove them from the entry entirely.

## Setup

### 1. Register and receive your API key

Visit https://runlog.org/register, enter your email address, and click the verification link. You will receive one API key in the form:

```
sk-runlog-<id12>-<secret32>
```

The key is 55 characters total (`sk-runlog-` prefix, 12-char lowercase alphanumeric ID, `-`, 32-char lowercase alphanumeric secret). It is shown exactly once. Copy it immediately and store it in a password manager or secrets vault. The server stores only a bcrypt hash; the plaintext is unrecoverable after the page is closed.

### 2. Set the environment variable

Set `RUNLOG_API_KEY` in your shell environment. Do not commit it to any config file.

```sh
export RUNLOG_API_KEY="sk-runlog-<your-key>"
```

If you use a `.env` file for local development, add it to `.gitignore` before writing the key there.

### 3. Add Runlog to Claude Code's MCP config

Add the following to `~/.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "runlog": {
      "transport": "http",
      "url": "https://api.runlog.org/mcp",
      "headers": {
        "Authorization": "Bearer ${RUNLOG_API_KEY}"
      }
    }
  }
}
```

If Claude Code's config does not support environment variable interpolation in headers, use the literal key with a comment:

```json
{
  "mcpServers": {
    "runlog": {
      "transport": "http",
      "url": "https://api.runlog.org/mcp",
      "headers": {
        "Authorization": "Bearer sk-runlog-<your-key>"
      }
    }
  }
}
```

The literal-key form is less secure because the key sits in a config file on disk. Prefer the env-var form and restrict file permissions on `~/.claude/settings.json` if you must use it.

### 4. Verify the connection

```sh
claude mcp list
```

The output should show `runlog` as connected. If it shows an error, confirm `RUNLOG_API_KEY` is set in the shell that launched Claude Code and that the key format matches `sk-runlog-<id12>-<secret32>`.

## Rate Limits

v0.1 enforces per-key sliding-window quotas. All windows are 24 hours.

| Tool | Limit |
|---|---|
| `runlog_search` | 1000 / day |
| `runlog_submit` | 50 / day |
| `runlog_report` | 500 / day |
| `runlog_status` | 1000 / day |

When a limit is exceeded the server returns HTTP 429 with a response body containing `error.type: "rate_limit"` and `error.retry_after_seconds`. Wait that many seconds before retrying.

Limits scale with trust score in Phase 2. New keys start at base quota.

## v0.1 Caveats

- **Signed verifier deferred to Phase 2.** Submitted entries land at `status="unverified"` until field telemetry confirms them. Trust is built through reported outcomes, not cryptographic proof, until the verifier ships.
- **Cassette capture for integration entries deferred to Phase 2.** Integration-tier submissions (live API/RPC exchange) are telemetry-only in v0.1. The signed agent that records and strips the HTTP cassette is not yet deployed. Integration entries are accepted but their cassette field is a stub.
- **Full default-deny allow-list deferred to Phase 1.** v0.1 uses a coarse hard-reject blocklist for credentials and PII rather than the full per-submission allow-list described in `docs/05-sanitization.md`. False positives are possible; the trade-off is intentional — a coarse blocklist that never leaks credentials is preferable to a precise allow-list that ships late.
- **Web UI and dashboards are not in v0.1.** Registration, key issuance, and stats are CLI/API-only.

## Further Reading

| Document | Read when working on |
|---|---|
| `docs/02-architecture.md` | Entry lifecycle, trust tiers, confidence decay |
| `docs/04-submission-format.md` | Full submission spec: entry YAML, placeholders, verification types, cassettes, scope rules |
| `docs/07-mcp-interface.md` | Canonical client contract this skill implements |
| `docs/10-open-questions.md` | Known unknowns and unresolved design questions |

---

Skill version follows the runlog-skills repo tag (currently unreleased; will be v0.1.0 at first publication).
