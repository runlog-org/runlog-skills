---
name: runlog-author
description: Author and submit Runlog entries from a real debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Use AFTER independently solving an external-dependency gotcha that runlog_search did not surface. Companion to the read-side `runlog` skill; does not replace it.
---

## runlog-author

This skill turns the submission side of Runlog from a multi-tool toolchain (build verifier, manage Ed25519 keypair, hand-write YAML, decode typed rejection reasons by hand) into "two prompts at the end of a real debugging session." When a developer hits a third-party-system gotcha and the agent debugs it, this skill drafts the entry, calls the local verifier, fixes whatever the verifier rejected, re-runs until `status: verified`, and submits.

The verifier requirement is structural — `CLAUDE.md` invariant #6 ("verification happens on the submitter's machine") and `docs/03-verification-and-provenance.md §5.3` step 4 (mutation testing kills theatre). This skill makes the agent drive the verifier on the user's behalf. It does not weaken the verification gate.

## When to Use This Skill

### Use it when ALL of these hold

1. The fix concerns a **third-party system** (public API, published framework, OSS library, standard protocol) — same scope rule as the `runlog` read skill.
2. **Team memory does not already cover it** (CLAUDE.md / Cursor rules / mem0 / project docs / prior conversation). Mirrors the four-point client contract from [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
3. **`runlog_search` did not surface a sufficiently-similar entry.** The skill MUST run a search before drafting and surface near-matches to the user.
4. The gotcha has a **falsifiable shape** — a concrete failed approach, a concrete working approach, and an observable difference. "I read the docs more carefully" is not falsifiable; the skill must decline to draft.

### Do NOT use it when

- The user has not explicitly asked to publish, or a heuristic-detected proposal was declined.
- The fix is in internal/proprietary code or team-specific conventions.
- The user's machine is not configured (see Prerequisites — surface a single diagnostic, do not partial-draft).
- A near-duplicate entry already exists in Runlog (`runlog_report` against the existing entry instead).

The skill MUST NOT propose publication on every external-dependency fix. Default is silence; propose only when all four conditions hold. Heuristics propose; explicit invocation (`/runlog-publish`) always works.

## Decision Flow

```
External-dependency fix just succeeded
        │
        ▼
  Did the user say "publish" / accept the heuristic prompt?
        │
    ┌───┴───┐
    │       │
   No      Yes
    │       │
   stop     ▼
       Pre-flight check (Prerequisites table)
            │
        ┌───┴───┐
        │       │
      Gap     Clean
        │       │
       surface ▼
       missing  runlog_search(query, domain)
       prereq         │
        stop      ┌───┴───┐
                  │       │
                Match    No match / weak
                  │           │
                  ▼           ▼
            Offer        Step 2 — draft
            runlog_report     │
            instead           ▼
                        Step 3 — local verify loop
                              │
                          ┌───┴───┐
                          │       │
                       verified  rejected (>5 retries)
                          │           │
                          ▼           ▼
                    Step 4 —    Hand back to user
                    sign+submit  with verifier output
```

## Prerequisites

A **one-time pre-flight check** runs on first invocation. If any prerequisite is missing, emit a single human-readable diagnostic naming the gap and stop — do not start drafting.

| Prerequisite | Check | Today's user action if missing |
|---|---|---|
| `runlog-verifier` binary on `$PATH` | `command -v runlog-verifier` | `cd verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/` (release-artifact UX is a tracked prerequisite to the skill) |
| Ed25519 keypair at `~/.runlog/key` | `test -f ~/.runlog/key` | `runlog-verifier keygen --out ~/.runlog/key && chmod 600 ~/.runlog/key` |
| Public key registered against the user's account | (server-side check on submit; client cannot pre-flight today) | `runlog-verifier register --email <addr>` (UX is a tracked prerequisite) |
| `RUNLOG_API_KEY` set | `[ -n "$RUNLOG_API_KEY" ]` | Already required by the read skill — see [`../claude-code/SKILL.md`](../claude-code/SKILL.md) §Setup |
| Runtime the entry exercises | `command -v <tool>` per `verification.type` / `cassette.runtime.tool` | Install the matching tool, or surface `tier_unsupported` (Step 3) without retry |

The release-artifact UX (so users don't need a Go toolchain), the public-key registration flow, and the `runlog-verifier register --email` UX are tracked separately as the skill's structural prerequisites. Until they ship, the manual workarounds in this table apply. The skill body itself is unaffected — pre-flight still surfaces a single diagnostic; the user resolves the gap and re-runs.

## The Author Flow

Four steps, run in order. Steps may not be skipped or reordered. The skill MUST NOT submit an unverified entry under any circumstance.

### Step 1 — Classify and search

- **Classify the gotcha** against the four-point client contract:
  - Team memory checked first?
  - External-dependency? (Internal code → reject the proposal here, never draft.)
  - The fix is generic, not specific to the team's codebase?
- **Run `runlog_search`** against a working draft of the gotcha (use the conversation's keywords — domain tags, package names, error strings).
  - If a high-confidence match exists, surface it: *"this looks like `<entry_id>` at distance N; want to call `runlog_report` against it instead of submitting a duplicate?"*
  - If no match or weak match, proceed to Step 2.
- **Confirm scope**: every domain tag must resolve to a public source. If the conversation reveals an obviously-internal codebase (proprietary domains in `version_constraints.packages`, internal hostnames in API examples), warn before drafting. The server-side `runlog_submit` `scope_rule` rejection will catch a slip; the skill catches it client-side as a usability matter.

### Step 2 — Draft the entry from session context

Generate `entry.yaml` against [`../../schema/entry.schema.yaml`](https://github.com/runlog-org/runlog-schema/blob/main/entry.schema.yaml). The skill MUST:

- **Read the schema at draft time.** Do not hardcode field names; the schema is the cross-language contract and evolves.
- **Pick the correct `verification.type`** per the entry's nature:
  - `assertion_only` — last resort. Only when no runnable code exists. Discouraged except for protocol-shape claims; the entry will not earn the verified stamp via runtime checks.
  - `unit` — pure-function gotchas, no external state. Default for language/library behaviour.
  - `integration` mode `replay` — HTTP/RPC API gotcha. Cassette steps are recorded from the conversation's actual exchange (or composed from observed responses).
  - `integration` mode `reexecute` — process / DB / filesystem gotcha. Today the verifier drives `shell` and `sqlite`; `postgres`, `redis`, `git`, `docker` are runtime-tool slices in flight (see `verifier/internal/verify/integration.go` `runtime_tool_not_yet_implemented` cases).
- **Convert real values to placeholders** per `docs/04-submission-format.md §7`: `$PAYLOAD`, `$TOKEN`, `$ENDPOINT`, `$CREDENTIAL`, etc. Real credentials, internal hostnames, or PII MUST NEVER appear inline in the draft, even if the user asks. The hard-reject layer (`server/src/runlog/sanitize/tokens.py`) catches them server-side; the skill catches them client-side.
- **Declare `$LITERAL_N`** for every non-routine literal that survives sanitization (timeouts, magic numbers, error codes, status codes). For each declared literal, ask the user to **confirm the `reason:` in plain language**. The reason is the human-in-the-loop guard against literal abuse described in `docs/05-sanitization.md §8.2` — the skill must not rubber-stamp it.
- **Compose at least two mutations.** Each mutation must, when applied, plausibly change outcome — at least one mutation must invalidate the working approach. The verifier surfaces single-mutation no-discriminators as `mutation_did_not_discriminate` (see Step 3 fix table); pre-empt by reasoning about each mutation's expected effect before running the verifier.

The skill SHOULD pattern-match on the working session for cassette content: HTTP calls already made in the debugging session (with literals → placeholders) become `cassette.steps`; shell/SQL already executed becomes `cassette.runtime` reexecute steps with `setup_script` that reproduces the sandbox.

### Step 3 — Local verification loop

Run `runlog-verifier verify <draft>.yaml` via Bash. Decode the JSON result.

| Verifier outcome | Skill response |
|---|---|
| `status: verified` | Capture the signed bundle output. Proceed to Step 4. |
| `status: rejected, reasons: [...]` | Map each reason to a fix strategy (table below). Apply, re-verify. **Cap at 5 retry rounds**; on cap, hand back to the user with the last verifier output and a plain-language summary. |
| `status: tier_unsupported, reason: ...` | Surface the named tier / tool / strategy. Either downgrade `verification.type`, drop the unsupported mutation, or explain that this gotcha cannot be verified yet on the local toolchain. **Never** silently strip a mutation to make the verifier accept the entry. |
| Non-zero exit, no parseable JSON | Treat as environmental error (verifier missing, key missing, runtime-not-installed, etc.). Surface diagnostics. Do not retry. |

Typed-reason → fix-strategy table (subset; full set in `verifier/internal/verify/`):

| Reason | Likely fix |
|---|---|
| `mutation_did_not_discriminate` | The mutation produces byte-different but observationally-identical output (e.g. `swap_identifier` with consistent renames). Pick a token that actually invalidates the working approach — usually a load-bearing function call rather than a local variable. |
| `mutation_target_invalid` | Token lookup failed (e.g. `\bTOKEN\b` regex no-op on a non-word boundary, or `target:` not branch-prefixed). Reshape `target:` / `token:`. |
| `mutation_no_expectation` | Mutation targets a branch with no applicable `expected_result` / `expected_branch_outcome.<branch>`. Add explicit `branch:`. |
| `mutation_strategy_unsupported` | Strategy is on the schema enum but the verifier doesn't drive it on this tier (e.g. `mutate_cassette_response` only at integration replay; `custom` everywhere). Drop or replace the mutation. |
| `cassette_unmatched_request` | Cassette declared step doesn't match the request the action made. Inspect declared method / path / query vs. observed (F19 matches method+path; F20 matches query strings exactly when declared). |
| `cassette_sequence_underrun` / `cassette_unused` / `cassette_step_unknown` | Per-branch `*_replay_sequence` count or step IDs are wrong. Adjust to match what the action consumes. |
| `wrong_return_type` | Matcher shape mismatched with action's return shape. Add a `path:` extractor (F13 — dotted-key access into dict returns) or fix the `value_equals` shape. |
| `runtime_tool_not_yet_implemented` | The verifier doesn't drive this tool yet (today: `postgres`, `redis`, `docker` for reexecute). Either pick a supported tool, or report this gotcha as not-yet-authorable on the current verifier. |
| `isolation_unsupported` / `isolation_unknown` | Driver registry doesn't have this isolation, or the value is outside the schema enum. Same response as above. |
| `contamination` (sanitizer, not verifier) | A token in the entry hit the hard-reject blocklist (credentials, PII, private keys). Remove and re-draft; `$LITERAL_N` does NOT override hard-rejects. |

The loop is **bounded**. If the skill cannot get to `verified` within the retry cap, it MUST hand back to the user with the last verifier output and a plain-language summary. **Never** silently submit an unverified entry.

### Step 4 — Sign and submit

When `verify` returns `verified`, the verifier has produced a signed Ed25519 bundle over the canonical-JSON of `{entry, fingerprint, verification_result}`. Call `runlog_submit` with `entry` + `verification_signature: <bundle>`.

Possible final-mile errors and responses:

| `error.type` | Cause | Skill response |
|---|---|---|
| `scope_rule` | Server-side scope check rejected a domain tag the local skill missed | Surface to user; do not retry blindly with a different tag |
| `contamination` | Hard-reject blocklist hit a token the local sanitizer didn't catch | Surface; user removes and re-runs Step 2 |
| `signature_invalid` | The signing key is not registered against the API key's account | Direct user to `runlog-verifier register`; do not retry |
| `rate_limit` | Quota exhausted | Wait `retry_after_seconds`, single retry |
| `internal_error` | Server-side bug | Surface; do not retry |

On success, confirm to the user with the new `entry_id`, `status` (`verified` end-to-end with a real signed bundle), and a one-line note that future agents hitting the same gotcha will retrieve the entry via `runlog_search`.

## What This Skill MUST NOT Do

Derived from the load-bearing invariants in `CLAUDE.md`. Violating any of them collapses the product.

- **MUST NOT submit unverified.** If the verification loop fails to converge within the retry cap, hand back to the user. The verifier is the gate, not a suggestion. (Invariant #6.)
- **MUST NOT inline real credentials, internal hostnames, or PII** in the draft, even if the user requests it. Hard-reject is a server-side last line of defence; the skill catches them client-side as a usability matter. (Invariant #4.)
- **MUST NOT propose entries that would fail the scope rule.** Internal-code knowledge belongs in team memory; do not draft it. (Invariant #1.)
- **MUST NOT silently weaken mutation testing** to make the verifier accept a draft (e.g. dropping a mutation that fails to discriminate instead of fixing it). Either fix the mutation or report the entry as unauthorable on the current verifier. (Invariant #6 / `docs/03-verification-and-provenance.md §5.3` step 4.)
- **MUST NOT replace `skills/claude-code/SKILL.md`.** It is a companion. The read side stays as-is; this skill fires only on the proposal-to-publish path.

## Out of Scope for v0

- **Multi-language entries.** v0 picks one language per entry (the language the conversation was conducted in).
- **Decay re-verification.** The decay/re-verification flow (`CLAUDE.md` invariant #8) is a separate `runlog-refresh` skill (planned, not yet drafted). This skill handles initial submission only.
- **Authoring against tools the verifier doesn't yet drive.** Surface the typed reason; do not invent workarounds.
- **Bulk import** of existing knowledge (CLAUDE.md, Notion notes). The skill is conversation-driven by design; bulk import is a separate problem and a separate tool.
- **Web UI mirror.** Always CLI / agent-driven; web authoring is a separate product surface.

## Cross-Vendor Parity

This skill body is deliberately framework-agnostic. The canonical body lives at `skills/runlog-author/SKILL.md`; per-vendor adapters under `skills/<vendor>/runlog-author/` swap orchestration glue (how the skill is invoked, how local Bash is dispatched, how the agent loop iterates on verifier rejections) — they do **not** re-author the contract.

Target vendor priority: **Cursor → Cline → Continue → Windsurf → Aider → Copilot via VS Code MCP → JetBrains AI → Zed.** Cross-vendor coverage is structurally important for Runlog: the defensive moat against agent-platform incumbents shipping their own knowledge layers is being the layer that works across all of them. See [`../README.md`](../README.md) for the cross-vendor expansion plan and [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) for the invariants every vendor adapter MUST preserve.

## Setup

This skill assumes the read-side `runlog` skill is already configured (see [`../claude-code/SKILL.md`](../claude-code/SKILL.md) §Setup). Beyond the read-side prerequisites:

1. **Build / install `runlog-verifier`.** From the repo: `cd verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/`. A release-artifact UX (so users don't need Go on their machine) is tracked as a structural prerequisite.
2. **Generate an Ed25519 keypair**: `runlog-verifier keygen --out ~/.runlog/key` (mode 0600).
3. **Register the public half against your account**: `runlog-verifier register --email <addr>` (UX deferred; today the public key is registered manually against the API key's account row).

The skill performs a one-time pre-flight check on first invocation and surfaces missing prerequisites as a single diagnostic.

## Further Reading

| Document | Read when working on |
|---|---|
| [`./DESIGN.md`](./DESIGN.md) | Design rationale and open questions for this skill |
| [`../claude-code/SKILL.md`](../claude-code/SKILL.md) | Read-side companion (`runlog_search` / `runlog_report` flow) |
| [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md) | The cross-vendor read+write client contract |
| [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) | Author-side cross-vendor invariants |
| `runlog-docs/04-submission-format.md` | Full submission spec: entry YAML, placeholders, verification types, cassettes, scope rules |
| `runlog-docs/05-sanitization.md` | Allow-list pipeline, declared literals, hard-rejects |
| `runlog-docs/03-verification-and-provenance.md` | Verifier invariants — differential execution, mutation testing, signed bundles |
| `verifier/internal/verify/` | Source of truth for typed rejection reasons |

---

Skill version follows the runlog-skills repo tag (currently unreleased; will accompany the read-side skill at first publication).
