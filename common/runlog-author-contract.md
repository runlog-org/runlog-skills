---
name: runlog-author-contract
description: Cross-vendor invariants every Runlog author skill MUST preserve. Per-vendor adapters under <vendor>/runlog-author.md may vary orchestration glue but MUST honour every rule in this document.
---

# runlog-author Contract

Author skills are a strict superset of read skills. Every rule in [`four-point-client-contract.md`](./four-point-client-contract.md) applies to author skills too; this document adds the rules specific to the submission flow.

The canonical author body lives at [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md). Per-vendor adapters — at `cursor/runlog-author.md`, `cline/runlog-author.md`, etc. — MAY vary:

- How the skill is invoked (slash command, hotkey, automatic heuristic)
- How local Bash is dispatched (vendor's tool-use API)
- How the agent loop persists state across iterations
- How the user is prompted (vendor's chat UI vs. command palette vs. inline)
- How `~/.runlog/key` is read (filesystem vs. vendor-managed secrets)

Per-vendor adapters MUST NOT vary:

1. **The four-point client contract** ([`four-point-client-contract.md`](./four-point-client-contract.md)). Author skills inherit every rule.
2. **The four-step author flow** (Classify+Search → Draft → Local verify loop → Sign+Submit). Steps may not be skipped or reordered.
3. **The local verifier as the submission gate.** Submission without a verifier-signed bundle is forbidden, even when the verifier reports `tier_unsupported`. Adapters that cannot dispatch the local binary MUST refuse to submit.
4. **The retry cap on the verification loop.** Default 5 rounds. Adapters MAY surface the cap as a configurable; they MUST NOT remove it.
5. **The hard-rejects in Step 2.** Real credentials, internal hostnames, PII, private keys are forbidden in drafts client-side. The server-side hard-reject layer is a last line of defence, not the primary gate.
6. **The "MUST NOT" list** in [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md). Each rule is load-bearing per a `CLAUDE.md` invariant; violating any collapses the product.

## What "the verifier is the gate" means in practice

When the verifier returns `tier_unsupported` (e.g. the entry uses `cassette.runtime.tool: postgres` which the verifier doesn't drive yet), an adapter MAY:

- Surface the typed reason to the user.
- Help the user reshape the entry to a supported tier.

An adapter MUST NOT:

- Submit the entry with `verification_signature: null` and let the server land it as `unverified`.
- Submit a hand-crafted bundle that bypasses the verifier.
- Rebrand `tier_unsupported` as a transient retryable error.

The verifier's gate is what allows the trust system to compute trust without humans in the loop (`CLAUDE.md` invariants #3, #6, #7). Bypassing it locally to "ship something" silently invalidates the cross-org guarantee.

## Vendor implementation checklist

For a per-vendor adapter to be conformant:

- [ ] Read-side skill is in place (`skills/<vendor>/SKILL.md` or equivalent — references [`four-point-client-contract.md`](./four-point-client-contract.md)).
- [ ] Pre-flight check fires once per session and surfaces every missing prerequisite in one diagnostic.
- [ ] The four-step author flow is implemented in order, with each step gated on the previous.
- [ ] Verifier rejection table (Step 3) handles the typed reasons listed in [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md). Unknown reasons are surfaced verbatim, not retried.
- [ ] Retry cap is enforced.
- [ ] Hard-rejects (Step 2) are checked client-side before drafting.
- [ ] The "MUST NOT" list is honoured.
- [ ] Submission flow MUST NOT proceed without a verifier-signed bundle.

Tracker: `[F25]` in the project backlog. References: `runlog-docs/07-mcp-interface.md` §10.4, [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md), `runlog-verifier/internal/verify/`.
