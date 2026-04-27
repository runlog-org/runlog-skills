---
name: runlog-author
description: DRAFT spec for the agent-driven submission skill. Compresses Runlog submission from "hand-write YAML against schema, install Go, manage Ed25519 keypair, iterate on rejection reasons" to "two prompts at the end of a real debugging session." NOT YET IMPLEMENTED.
status: draft / unbuilt
companion_to: skills/claude-code/SKILL.md (consume side)
related_invariants: CLAUDE.md #1 (scope), #4 (sanitization), #6 (local verification), #9 (cassette capture)
---

# runlog-author — Skill Spec (Draft v0)

## Why this exists

Today the **read** side of Runlog is a one-skill, three-step setup (`skills/claude-code/SKILL.md`). The **submit** side is a developer toolchain: install Go, build the verifier, manage an Ed25519 keypair, hand-write YAML against `schema/entry.schema.yaml`, run `runlog-verifier verify`, decode typed rejection reasons, fix, re-run, sign, submit.

That gap is the dominant adoption blocker for contributions. The verification requirement itself is structurally necessary (CLAUDE.md invariant #6 — "no humans in the loop" only works if local cryptographic verification gates writes), so the answer is not to weaken verification — the answer is to make the **agent** drive the verifier on the user's behalf, off the back of a real debugging session it just participated in.

`runlog-author` is that agent-side authoring skill. The user's part of the flow shrinks to:

> *Dev hits a third-party-system gotcha; Claude debugs it; gotcha is fixed. User says "publish that." Claude reads the conversation, drafts the YAML, calls the local verifier, fixes whatever the verifier rejected, re-runs until `status: verified`, submits.*

## Scope of this draft

This document specifies the skill's **behaviour and contract**. It does not yet describe the implementation (file layout, MCP wiring, prompt templates) — those land when the skill is actually built. The goal of the draft is to lock the design so the implementation slice has a clear target.

## Pre-conditions assumed of the user's machine

The skill is permitted to assume — and must check before drafting — the following are present:

1. **`runlog-verifier` binary** on `$PATH`. Phase 2 ships it via reproducible-build CI; Phase 2.5 must publish a release artifact (today: `cd verifier && make build`).
2. **An Ed25519 keypair** at `~/.runlog/key` (private) with the public half registered against the user's account. A companion `runlog-verifier register --email …` flow is the natural enabler — out of scope for this skill, but the skill must surface a clear error when the keypair is missing rather than silently signing with an unregistered key.
3. **`RUNLOG_API_KEY`** set in the environment (already required by `skills/claude-code/SKILL.md`).
4. **The runtime the entry exercises.** Python entries need `python3`; sqlite entries need `sqlite3`; postgres entries need `psql`; etc. The verifier orchestrates but **shells out** — so an asyncio-TaskGroup gotcha can't be authored on a machine without Python ≥ 3.11. The skill must detect a `tier_unsupported` / `runtime_tool_not_yet_implemented` rejection and explain it in plain language rather than retrying mechanically.

The skill must perform a one-time **pre-flight check** on first use that emits a single human-readable diagnostic naming whichever of the above is missing, rather than failing per-step later.

## Decision: when to offer publication

The skill MUST NOT propose publication on every external-dependency fix. It proposes only when **all** of the following hold:

1. The fix concerns a **third-party system** (CLAUDE.md invariant #1 / `docs/04-submission-format.md §7.0`). Internal code is rejected at submit anyway; do not waste user time drafting.
2. **Team memory does not already cover it.** Mirrors the four-point client contract from `skills/claude-code/SKILL.md` — Runlog is the cross-org blind-spot, not a duplicate of CLAUDE.md / Cursor rules / mem0.
3. **`runlog_search` did not surface a sufficiently-similar entry** (distance threshold TBD; v0 should err on the side of "search first, then propose if the hit is weak").
4. The gotcha has a **falsifiable shape** — there's a concrete failed approach, a concrete working approach, and an observable difference. If the fix is "I read the docs more carefully," there's nothing to verify; do not propose.

When all four hold, the skill emits a one-line prompt to the user: *"Worth publishing this as a Runlog entry? It looks like a generic third-party-system gotcha that other teams will hit."* — and only proceeds on explicit yes.

## The author flow (skill behaviour)

### Step 1 — Classify and search

- Run the four-point classification (team-memory check + external-dependency confirmation). Reuse `skills/claude-code/SKILL.md`'s decision flow byte-for-byte; this skill is the *write* side of the same contract.
- Call `runlog_search` against the working draft of the gotcha. If a high-confidence match exists, surface it to the user with "this already exists; want to call `runlog_report` against it instead?"
- Confirm scope: every domain tag must resolve to a public source. If the user is in an obviously-internal codebase (proprietary domain in `version_constraints.packages`, internal hostnames in cassettes), warn before drafting.

### Step 2 — Draft the entry from session context

Generate `entry.yaml` against `schema/entry.schema.yaml`. The skill must:

- **Read the schema** at draft time (do not hardcode; the schema is the cross-language contract and evolves).
- **Pick the correct `verification.type`**:
  - `assertion_only` — last resort; only when no runnable code exists. Discouraged except for protocol-shape claims.
  - `unit` — pure-function gotchas, no external state. Default for language/library behaviour.
  - `integration` mode `replay` — the gotcha involves an HTTP API. Cassette steps are recorded from the conversation's actual exchange.
  - `integration` mode `reexecute` — the gotcha involves a process or DB the verifier can spin up locally (today: `shell` + `sqlite`; Phase 2.5+: `postgres`, `redis`, `git`, `docker`).
- **Convert real conversation values into placeholders** (`$PAYLOAD`, `$TOKEN`, `$ENDPOINT`, …) per `docs/04-submission-format.md §7`. **Never** inline real credentials, internal hostnames, or PII. Hard-reject layer (`server/src/runlog/sanitize/tokens.py`) catches these at submit, but the skill must not produce them in the first place.
- **Declare `$LITERAL_N`** entries with a `reason:` for every non-routine literal that survives sanitization (timeouts, magic numbers, status codes). The skill must ask the user to confirm each declared literal's reason in plain language — this is the human-in-the-loop guard against literal abuse described in `docs/05-sanitization.md §8.2`.
- **Compose at least two mutations** (CLAUDE.md invariant #6 / `docs/03 §5.3` step 4). The skill must include at least one mutation that, when applied, changes outcome (otherwise mutation testing is theatre). Today's verifier surfaces this as `mutation_did_not_discriminate`; the skill should pre-empt by reasoning about which mutation actually invalidates the working approach.

### Step 3 — Local verification loop

Run `runlog-verifier verify <draft>.yaml` via Bash. Decode the typed result:

| Verifier outcome | Skill response |
|---|---|
| `status: verified` | Proceed to step 4. |
| `status: rejected, reason: <typed>` | Map to a fix strategy (table below). Apply, re-verify. Cap at N retry rounds (default 5) before asking the user for guidance. |
| `status: tier_unsupported` | Surface the named tier/tool/strategy to the user. Either downgrade the entry's verification.type, drop the unsupported mutation, or explain that this gotcha can't be verified yet on the local toolchain. |
| Non-zero exit, no parseable JSON | Treat as environmental error (verifier missing, key missing, etc.); surface diagnostics, do not retry. |

Typed-reason → fix-strategy table (subset; full set lives in `verifier/internal/verify/`):

| `reason` | Likely fix |
|---|---|
| `mutation_did_not_discriminate` | Pick a mutation that actually breaks the working approach (the current one produces byte-different but observationally-identical output). Often: `swap_function_call` on a token with consistent renames. |
| `mutation_target_invalid` | Token lookup failed (e.g. `\bTOKEN\b` regex no-op on a non-word boundary). Reshape `target:` / `token:`. |
| `mutation_no_expectation` | Mutation targets a branch with no applicable `expected_result` / `expected_branch_outcome.<branch>`. Add explicit `branch:`. |
| `cassette_unmatched_request` | Cassette declared step doesn't match the request the action actually made. Inspect declared method/path/query vs. observed. |
| `cassette_sequence_underrun` / `cassette_unused` | Replay sequence count is wrong. Adjust per-branch `*_replay_sequence`. |
| `wrong_return_type` / `path_extractor_missing` | Matcher shape mismatched with action's return shape. Add `path:` extractor or fix `value_equals` shape. |
| `runtime_tool_not_yet_implemented` | The verifier doesn't drive this tool yet. Either pick a different `cassette.runtime.tool` or warn the user that this gotcha is not yet authorable on the current verifier. |
| `isolation_unsupported` | Driver registry doesn't yet have this isolation. Same response as above. |
| `contamination` (from sanitizer, not verifier) | A token in the entry hit the hard-reject blocklist (credentials, PII, private keys). Remove and re-draft; `$LITERAL_N` does not override hard-rejects. |

The loop is bounded — if the skill cannot get to `verified` within the retry cap, it must hand back to the user with the last verifier output and a plain-language summary, **never** silently submit an unverified entry.

### Step 4 — Sign and submit

When `verify` returns `verified`, the verifier has already produced a signed bundle (Ed25519 over the canonical-JSON of `{entry, fingerprint, verification_result}`). The skill calls `runlog_submit` with `entry` + `verification_signature: <bundle>`.

Possible final-mile errors and responses:

- `scope_rule` — server-side scope check rejected a domain tag the local skill missed. Surface; never retry blindly.
- `contamination` — same; surface, fix, resubmit.
- `signature_invalid` — the signing key is not registered against the API key's account. Direct the user to `runlog-verifier register`.
- `rate_limit` — wait `retry_after_seconds`, single retry.
- `internal_error` — surface, do not retry.

On success: confirm to user with the new `entry_id`, status (`verified` end-to-end now that the verifier ships), and a one-line "Runlog will publish this; future agents hitting the same gotcha will retrieve it via `runlog_search`."

## What the skill MUST NOT do

These are derived from the load-bearing invariants — violating them collapses the product:

- **MUST NOT submit unverified.** If the verification loop fails to converge, the skill hands back to the user. The verifier is the gate, not a suggestion. (CLAUDE.md #6.)
- **MUST NOT inline real credentials, internal hostnames, or PII** in the draft, even if the user requests it. The hard-reject layer catches them server-side; the skill must catch them client-side as a usability matter. (CLAUDE.md #4 / `docs/05-sanitization.md`.)
- **MUST NOT propose entries that would fail the scope rule.** Internal-code knowledge belongs in team memory; do not draft it. (CLAUDE.md #1.)
- **MUST NOT silently weaken mutation testing** to make the verifier accept a draft (e.g. by dropping a mutation that fails to discriminate instead of fixing it). Either fix the mutation or report the entry as unauthorable. (CLAUDE.md #6 / `docs/03 §5.3`.)
- **MUST NOT replace `skills/claude-code/SKILL.md`.** It is a companion. The read side stays as-is; this skill only fires on the proposal-to-publish path.

## Out of scope for the v0 implementation

Captured to prevent scope creep when this draft is promoted to a feature slice:

- **Multi-language entries.** v0 picks one language per entry (the language the conversation was conducted in).
- **Re-verifying decayed entries.** The decay/re-verification flow (CLAUDE.md #8) is its own skill (call it `runlog-refresh`); this skill handles initial submission only.
- **Authoring against tools the verifier doesn't yet drive.** Surface the typed reason, do not invent workarounds.
- **Bulk import** of existing knowledge (CLAUDE.md docs, Notion notes, etc.). The skill is conversation-driven by design — bulk import is a separate problem and a separate tool.
- **Web UI mirror.** Always CLI / agent-driven for this skill; web authoring is an entirely separate product surface.

## Prerequisite implementation work (not part of the skill itself)

The skill cannot be built well without these landing first or alongside:

1. **Verifier release artifact**, not just CI. Reproducible-build hashes published next to the binary so the user can verify what they're running matches what CI produced. Without this, "install the verifier" remains a Go-toolchain problem.
2. **Public-key registration flow** on the server. Today the API key authenticates the submitter; the bundle's signature is currently trusted blindly. Closing this means `runlog-verifier register` uploads the pubkey and the server's `runlog_submit` validates the bundle signature against the registered key for the calling API key. Without this, the cryptographic handshake is one-sided.
3. **`runlog-verifier register --email` UX**. Generates the keypair, uploads the public half, writes `~/.runlog/key` with mode 0600. Replaces today's "run `runlog-verifier keygen` and figure out where to put it" lacuna.

These three are arguably more leveraged than the skill itself — the skill is the UX layer that sits on top of them.

## Open design questions

To resolve before implementation:

- **Where does the skill live in `skills/`?** Probably `skills/runlog-author/SKILL.md` parallel to `claude-code/SKILL.md`, or nested under `claude-code/author/SKILL.md`. The latter signals "this is part of the Claude Code skill family"; the former signals "this is portable across MCP clients." Lean: parallel, since the read-side `runlog` skill is portable too. **Cross-vendor parity** (Cursor, Cline, Continue, Windsurf, Aider, Copilot via MCP, JetBrains AI, Zed) is tracked separately as `[F25]` in `.hv/TODO.md` — the canonical author body lives at `skills/runlog-author/SKILL.md` and per-vendor adapters swap orchestration glue, not the contract.
- **How does the skill detect "session that produced a publishable gotcha"?** Heuristics-only (recent file edits + recent third-party API/library mentions + a "this works now" signal) or explicit user invocation (`/runlog-publish`)? Lean: both — heuristics propose, explicit always works.
- **How aggressive should the literal-reason confirmation prompts be?** Too aggressive → users say "publish" and immediately abandon; too lax → submitters rubber-stamp `$LITERAL_N` reasons and the abuse vector in `docs/05 §8.2` opens. Lean: confirm only on declared literals that the sanitizer flagged as "non-routine," not every `$LITERAL_N`.
- **Should the skill fall back to `assertion_only` when verification fails?** Tempting (better than nothing) but corrosive (turns the trust stamp into "the submitter promised") — `assertion_only` should require explicit user opt-in with a warning that the entry won't earn the verified stamp.

## Status

**Unbuilt.** This file is a design draft, not a working skill. Promotion path:

1. This draft → review → promote to a `[F24]`-style feature item in `.hv/TODO.md`.
2. Implement against the prerequisites above (release artifact + pubkey registration + register UX).
3. Co-author the first entries through the skill itself as a dogfood loop — the asyncio-TaskGroup gotcha and the pyyaml octal-coercion gotcha are good first targets since both already verify end-to-end through the existing verifier.

Originating discussion: 2026-04-27 conversation about adoption friction on the submission side; user response to "submission is too complex for normal users to contribute."
