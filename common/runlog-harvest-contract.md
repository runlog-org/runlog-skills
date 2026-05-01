---
name: runlog-harvest-contract
description: Cross-vendor invariants every Runlog harvest skill MUST preserve. Per-vendor adapters under <vendor>/runlog-harvest.md may vary orchestration glue but MUST honour every rule in this document.
---

# runlog-harvest Contract

Harvest skills are a strict superset of author skills. Every rule in [`runlog-author-contract.md`](./runlog-author-contract.md) applies to harvest skills via the Step 4 hand-off, and every rule in [`four-point-client-contract.md`](./four-point-client-contract.md) applies to the four-point classification check harvest runs in Step 2. This document adds the rules specific to the retrospective capture flow.

The canonical harvest body lives at [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md). Per-vendor adapters — under `<vendor>/runlog-harvest.md` — MAY vary:

- **Invocation literal.** Each adapter publishes its own (slash command, palette command, agent-mode prompt). The literal MUST be visible up front in the adapter file's table; users must not have to guess.
- **Picker prompt rendering.** The vendor's chat UI specifics (markdown table vs. plain numbered list, inline edit affordance vs. separate command, etc.). The grammar is fixed; the rendering is not.
- **Session-transcript discovery.** Each host stores conversation history differently (Claude Code: `~/.claude/projects/<encoded>/<session>.jsonl`; Cursor: IndexedDB; Aider: `.aider.chat.history.md`). When an adapter knows its host's path it MAY use it as a richer signal; if it does not, the adapter falls back to the in-frame context the model already sees.
- **Draft-persistence directory.** Each vendor scratch dir name is per-adapter. Harvest writes drafts to `<vendor's harvest scratch dir>/` (typically `.runlog-harvest/`); the dir is gitignored and cleaned up on successful submit.

Per-vendor adapters MUST NOT vary:

1. **The four-point client contract** ([`four-point-client-contract.md`](./four-point-client-contract.md)). The four-point classification check on each candidate inherits every rule.
2. **The four-step harvest flow** (Scan → Score+Dedup → Pick → Route-to-author). Steps may not be skipped or reordered.
3. **The score floor (≥ 0.7).** Adapters MAY raise the threshold (e.g. require all four checks to pass — `score = 1.0`); adapters MUST NOT lower it. Bias toward false negatives is the design intent.
4. **The comma-select picker grammar.** Input shape is `<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`. The vendor's UI may render differently; the grammar is normative.
5. **Per-item edit-before-submit.** Every adapter MUST offer the user the chance to rewrite the one-line candidate description before the candidate routes to runlog-author Step 2.
6. **Routing through runlog-author for verification + submission.** Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at its Step 2. There is no alternative submit path. Harvest MUST NOT reimplement the verifier loop and MUST NOT call `runlog_submit` directly.
7. **The "MUST NOT" list** in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md). Each rule is load-bearing; violating any collapses the product.

## What "route through runlog-author" means in practice

When harvest reaches Step 4 and the user has picked one or more candidates, an adapter MAY:

- Hold the picked candidate's one-line description and the relevant conversation context in its own scratch state.
- Render a per-candidate progress UI as runlog-author runs.
- Surface runlog-author's verifier rejection messages in the host's idiomatic chat shape.

An adapter MUST NOT:

- Skip the verifier loop, even when the candidate's score was 1.0. The score is a surfacing heuristic, not a verification result; the verifier is still the gate.
- Hand-craft a signed bundle, or any bundle. Only the local `runlog-verifier` binary produces valid bundles.
- Call `runlog_submit` directly from harvest. The submit call lives in runlog-author Step 4; harvest's job ends when the picked candidate is handed to runlog-author Step 2.
- Bypass any of runlog-author's MUST NOT rules. Hard-rejects, scope checks, mutation discipline — all inherited.

Harvest is the picker; runlog-author is the gate. The split is the integrity boundary that keeps the trust system honest (`CLAUDE.md` invariants #3, #6, #7).

## Vendor implementation checklist

For a per-vendor harvest adapter to be conformant:

- [ ] Read-side skill is in place (`<vendor>/SKILL.md` — references [`four-point-client-contract.md`](./four-point-client-contract.md)).
- [ ] Author-side skill is in place (`<vendor>/runlog-author.md` — references [`runlog-author-contract.md`](./runlog-author-contract.md)).
- [ ] Pre-flight check fires once per session and surfaces every missing prerequisite in one diagnostic; same prerequisites as runlog-author.
- [ ] The four-step harvest flow is implemented in order, with each step gated on the previous.
- [ ] The four-point classification check runs on every candidate; the score floor (≥ 0.7) is enforced.
- [ ] The comma-select picker grammar is parsed correctly; ambiguous input re-prompts rather than guessing.
- [ ] Per-item edit-before-submit is offered.
- [ ] Selected candidates route through [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) Step 2; no alternative submit path.
- [ ] The MUST NOT list is honoured.
- [ ] Invocation literal is documented in the adapter table; users do not have to guess.

Tracker: `M01-S03` in the project backlog. References: [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md), [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md), [`runlog-author-contract.md`](./runlog-author-contract.md), [`four-point-client-contract.md`](./four-point-client-contract.md).
