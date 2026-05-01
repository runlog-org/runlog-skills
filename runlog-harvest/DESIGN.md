---
name: runlog-harvest-design
description: Design rationale and open questions for the runlog-harvest skill. The agent-readable body lives at SKILL.md alongside this file; this document is the rationale a human reads when modifying SKILL.md or porting harvest to a new vendor.
status: design rationale; companion to SKILL.md
companion_to: skills/runlog-harvest/SKILL.md, skills/runlog-author/SKILL.md
related_invariants: CLAUDE.md #1 (scope), #4 (sanitization), #6 (local verification)
---

# runlog-harvest — Design Rationale

> The live, agent-readable skill body is at [`./SKILL.md`](./SKILL.md). This document is the design rationale and open questions — read it when modifying `SKILL.md` or porting the skill to a new vendor. Some content here intentionally overlaps with `SKILL.md`; this file is allowed to be longer because design rationale benefits from extra context.

## Why this exists

Runlog has two natural points where a third-party-system gotcha can be captured:

1. **Mid-flow** — the moment the fix lands. The conversation is fresh, the failed approach is still in scratch buffer, the working approach was just verified. This is `runlog-author`'s job.
2. **End-of-session** — the dev is wrapping up. Several gotchas may have flown by without a publication prompt — heuristic miss, user said "not now," or the agent simply did not propose. The signal is decaying but not gone; the conversation context still has it.

`runlog-author` covers (1) well. It does not cover (2). Without a retrospective lever, an entire session's worth of external-dependency findings can ship without a single Runlog entry — the dev moves on, the conversation rolls off the host's context window, and the next agent that hits the same gotcha re-discovers it from scratch.

`runlog-harvest` is the retrospective lever. The user runs `/runlog:harvest` at the end of a session; the skill scans the in-frame conversation plus recent git commits for external-dependency findings, scores and dedups them, surfaces a numbered picker, and routes selected drafts through the canonical author flow.

The split between mid-flow and end-of-session is deliberate:

- **Different triggers.** Author fires inline ("you just solved X — publish it?"). Harvest fires on user request ("scan what just happened — anything publishable?").
- **Different UX.** Author asks one yes/no per gotcha and proceeds. Harvest surfaces a picker over multiple candidates and lets the user select a subset.
- **Different scoring.** Author has full mid-flow context — the fix just landed, the falsifiability test is trivial. Harvest has retrospective context — the four-point check has to operate on partial signal, hence the score floor and the bias toward false negatives.
- **Easier to evolve independently.** A change to the picker grammar should not require touching the author flow. A change to verifier discipline should not require touching the picker. Two skills, one shared canonical author body for the verification loop.

## Scope of this document

Originally written alongside the slice plan to lock harvest's behaviour and contract before implementation. Now retained as design rationale alongside the live `SKILL.md` body — the implementation (file layout, picker grammar, scan sources) lives there. Sections that overlap with `SKILL.md` (the four-step flow, the score floor, the MUST NOT list) are kept here because the rationale behind each rule is load-bearing context when the contract is modified or ported to a new vendor.

## Pre-conditions assumed of the user's machine

Harvest inherits all of runlog-author's pre-conditions:

1. **`runlog-verifier` binary** on `$PATH`. Harvest's Step 4 hands off to runlog-author Step 2; the verifier loop runs in the author skill, not in harvest.
2. **An Ed25519 keypair** at `~/.runlog/key` with the public half registered against the user's account. Same registration UX as runlog-author (`runlog-verifier register --email <addr>`).
3. **`RUNLOG_API_KEY`** set in the environment.
4. **The runtime the entry exercises** — Python entries need `python3`; sqlite entries need `sqlite3`; etc. Surfaced as `tier_unsupported` in the author skill's verifier loop.

Harvest adds one additional pre-condition:

5. **A workspace where session context is reachable.** The in-frame conversation history is the primary signal source. Hosts that strip or compact the session early (very small context windows, aggressive context-pruning agents) reduce harvest's signal — but harvest still has the git-log source as a backup. If both signals are empty, harvest exits cleanly with "no candidates found" rather than partial-drafting against thin air.

The pre-flight check is the same single human-readable diagnostic shape as runlog-author. If the verifier is missing, harvest cannot route its picks to the author skill, so harvest stops up front rather than letting the user pick items that will then fail to verify.

## Decision: when to offer harvest

Harvest is **explicit invocation only**. It does not auto-fire. The reasons:

- **Auto-firing on every session end is a noise generator.** Most sessions do not produce publishable external-dependency findings. Auto-firing means most invocations end with "no candidates found" — a UX papercut that erodes trust in the skill.
- **The user's mental state at session-end is not always "let me capture this."** Sometimes it's "I'm done, log off." Forcing a harvest prompt into that moment is annoying.
- **Heuristic surfacing remains acceptable.** A one-line "you might want to harvest" hint at session end is fine; running harvest unprompted is not. The line is "suggest" vs. "execute."

A future M03 follow-up may add a "harvest reminder" hook that fires once per N sessions or once per workspace per week — a soft nudge, not an auto-run. That is explicitly out of scope for v0.

**Single-session scope** is also a deliberate constraint. v0 processes one session per invocation. Multi-session harvests would need:

- A persistent record of which gotchas were already surfaced and dismissed (to avoid re-surfacing).
- A way to distinguish "still relevant" from "this gotcha got solved differently in a later session."
- A different score model that accounts for cross-session signal.

None of those are problems v0 needs to solve. The score floor and the four-point check assume a single session's signal; raising the scope to multi-session is a follow-up.

**Score-threshold rationale (≥ 0.7).** The four-point check has four binary inputs (scope, team-memory, dedup, falsifiability). 0.7 maps to "passed three of four"; passing fewer than three is too noisy to surface. The threshold is a **soft heuristic**, not a calibrated probability — at v0 volume there is not enough harvest data to calibrate. Adapters MAY raise the threshold (a Cursor adapter that finds users want fewer false positives can raise to 0.85 — meaning all four must pass); they MUST NOT lower it.

## The harvest flow (skill behaviour)

### Step 1 — Scan candidates

Two sources, both consulted on every invocation. Neither is exhaustive on its own; the union is the candidate pool.

- **In-frame session context** is the primary signal. The model already has several thousand tokens of session history; scanning that for "user hit X, agent fixed Y on third-party-system Z" turn-pairs is cheap and accurate. The output is a one-line description per candidate; the full turn-pair stays in context for Step 2's draft pass (which is the author skill's responsibility).
- **Recent git commits** are a backup signal. Default `git log --oneline -10`; a commit message or diff that hints at a third-party system (package name, vendor API path, error string in the diff) becomes a candidate. This catches gotchas that landed mid-session and were committed but rolled out of in-frame context.

The two sources may produce duplicates (same gotcha, both in conversation and in a commit). The dedup pass in Step 2 handles that — the same `runlog_search` query collapses to the same near-match, and the higher-scored copy stays.

Per-host transcript helpers (e.g. reading `~/.claude/projects/<encoded>/<session>.jsonl` for Claude Code) are deferred. Most agents in 2026 have several thousand tokens of session context already; explicit transcript reads are a "more is better but not required" optimisation. The cross-vendor contract makes the in-frame fallback normative; per-adapter transcript discovery is allowed but not required.

### Step 2 — Score and dedup

The four-point check mirrors [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md):

1. **Scope** (third-party? not internal-only?) — invariant #1.
2. **Team memory** (does CLAUDE.md / Cursor rules / mem0 already cover this?) — rule 1.
3. **Dedup** (does `runlog_search` surface a sufficiently-similar entry?) — uniqueness.
4. **Falsifiability** (failed approach + working approach + observable difference?) — verifiability.

Score is `yes-votes / 4`. The score floor (≥ 0.7) is a soft heuristic, expressing "passed three of four." Below it, candidates are dropped silently — the picker does not show them. Above it, candidates surface; if the dedup check (point 3) flagged a near-match, the candidate is surfaced **with** the inline `similar entry: <id>` note but **not** picker-eligible, because drafting a duplicate wastes both the user's time and the verifier's effort. The user can run `runlog_report` against the existing entry instead.

The bias is deliberately toward false negatives. Surfacing a non-publishable candidate (the user picks it, the author flow fails to verify, time is wasted) is more annoying than missing a publishable one (the user can re-run harvest later, or invoke runlog-author directly on the gotcha). Empirically the dominant adoption blocker on submission is friction, not signal-acquisition; harvest is ok to be conservative.

### Step 3 — Picker UX

The numbered list + comma-select grammar + per-item edit shape is fixed by the milestone. Why these choices:

- **Numbered list** — universally legible across vendors, reads cleanly in any chat UI, no special rendering needed.
- **Comma-select** — `1, 3, skip 2` is a one-line input that handles the common case (pick most, skip a few) and the rare case (pick a few, skip most). Easier than a checkbox UI in chat.
- **`all` / `none`** — fast paths for the common cases.
- **Per-item edit-before-submit** — the one-line description in the picker is the model's framing of the gotcha; the user may want to reshape it before the author skill drafts the YAML. This is the last opportunity to reframe before YAML draft locks in.
- **Default skip on uncertainty** — when the user's input is ambiguous (typo, out-of-range integer), harvest re-prompts rather than guessing. Bias toward false negatives applies here too.

### Step 4 — Route through runlog-author

Each picked candidate enters [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at **Step 2 — Draft the entry from session context**. From there the canonical author flow takes over:

- Step 2 drafts the YAML against `runlog-schema/entry.schema.yaml`.
- Step 3 runs the local verifier loop with the 5-round retry cap.
- Step 4 signs the bundle and calls `runlog_submit`.

Harvest contributes the candidate's one-line description (which becomes the seed for the author skill's draft prompt) and the conversation context the author skill reads for the actual YAML composition. Harvest does **not** contribute draft YAML, verifier invocations, or signed bundles. The hand-off discipline is what keeps harvest a thin retrospective wrapper rather than a parallel submission path.

If multiple candidates are picked, they route sequentially through runlog-author. Each is its own complete pass; they do not share verifier state, draft files, or signed bundles. This costs verifier wall-time on long picks (5 candidates × 5-round retry cap × verifier verification time) but trades cleanly against the simpler state model.

## Open questions

The slice plan ([`/home/vo/share/runlog/.hv/plans/M01-S03.md`](https://github.com/runlog-org/runlog/blob/main/.hv/plans/M01-S03.md), §"Open questions") carries five OQs. Their plan-time recommendations are repeated here for context, with status:

1. **Slash-command form for non-Claude-Code vendors.** Should the contract require all 9 to expose a user-typed invocation literal? **Recommendation (resolved at plan time):** yes, each adapter publishes its literal up front. **Status:** resolved before T3 dispatches.

2. **Confidence-score threshold for candidate surfacing.** Single number in canonical body, or a floor adapters can raise? **Recommendation (resolved at plan time):** single threshold (`score ≥ 0.7`) in canonical body, expressed as a soft heuristic on the four-point check; adapters MAY raise but MUST NOT lower. **Status:** resolved; encoded in `SKILL.md` Step 2 and in the cross-vendor contract.

3. **Session transcript access varies by host.** Should the canonical body specify a fallback to in-frame context, or should each adapter ship a transcript-discovery helper? **Recommendation (resolved at plan time):** fall back to in-frame context; defer per-adapter helpers as a follow-up. **Status:** resolved; encoded in `SKILL.md` Step 1 and in the cross-vendor contract.

4. **Harvest adapter file location: flat sibling vs subdir.** **Recommendation (resolved at plan time):** flat sibling — `<vendor>/runlog-harvest.md` — matches existing convention. **Status:** resolved; the claude-code adapter is at `claude-code/runlog-harvest.md` per this convention.

5. **Server-side provenance for harvest-vs-author.** Should the server track which capture lever produced an entry? **Recommendation (resolved at plan time):** defer; track client-side via local logs only; revisit after M01 ships and we have real harvest volume. **Status:** deferred (still open in the longer-term sense). Worth revisiting in M03 once harvest volume justifies the schema train.

## What harvest does NOT do (recap)

These are the same MUST NOT rules as in [`./SKILL.md`](./SKILL.md), restated here with rationale:

- **No auto-submit without explicit user confirmation.** The picker IS the confirmation. Heuristic surfacing is permitted; auto-drafting without user input is not. The submission decision is the human-in-the-loop point in an otherwise no-humans-in-the-loop trust system.
- **No drafting candidates that failed any of the four-point checks.** The score floor is the gate. Below it, candidates do not enter the picker. The score floor exists to keep harvest conservative — bias toward false negatives is the design intent, not a bug.
- **No bypass of the runlog-author verification loop.** Selected candidates route through runlog-author Step 2; the verifier discipline is inherited verbatim. There is no shortcut path. (This is the load-bearing rule that keeps the trust system honest — see [`../runlog-author/DESIGN.md`](../runlog-author/DESIGN.md) §"What the skill MUST NOT do".)
- **No real credentials, internal hostnames, or PII** in drafted candidates. Harvest's Step 4 hands off to the author skill, which handles sanitisation; harvest's job is to not introduce contamination at the candidate-description stage.
- **No cross-session aggregation.** One session per invocation. Multi-session is a different problem with a different score model; defer.

## Cross-references

- [`./SKILL.md`](./SKILL.md) — canonical agent-readable body.
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 2 hand-off target.
- [`../runlog-author/DESIGN.md`](../runlog-author/DESIGN.md) — shared verifier discipline; harvest inherits the verifier-is-the-gate posture.
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — cross-vendor invariants for harvest adapters.
- [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) — author-side cross-vendor invariants harvest inherits via Step 4.
- [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md) — read-side four-point check that harvest's score model mirrors.

## Status

**Skill body shipped at [`./SKILL.md`](./SKILL.md) (M01-S03, wave 1).** The Claude Code orchestration glue (`../claude-code/runlog-harvest.md`) and the `/runlog:harvest` plugin slash command (`../commands/harvest.md`) ship in the same wave. Wave 2 brings the eight remaining vendor adapters; wave 3 brings docs updates.

End-to-end functionality depends on the same three F24 prerequisites runlog-author depends on (verifier release artifact, public-key registration flow on the server, `runlog-verifier register --email` UX) — all shipped under F24 (2026-04-28). Harvest adds no new server-side surface; the dependency on F24's pipeline is one-way and explicit.

Originating discussion: M01 milestone planning (2026-04-29) noted that author covers mid-flow capture but leaves end-of-session capture as a gap. Harvest's design follows from F24's runlog-author shape: same canonical body + cross-vendor contract + per-vendor adapter pattern, with the new surface confined to candidate extraction and picker UX.
