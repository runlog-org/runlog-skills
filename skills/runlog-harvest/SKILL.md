---
name: runlog-harvest
description: End-of-session retrospective submission flow for Runlog. Scans the conversation context and recent git commits for external-dependency findings the agent missed in-flight, scores and dedups candidates, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Companion to runlog-author (mid-flow); does not replace it.
---

## runlog-harvest

This skill is the **retrospective** capture lever for Runlog. The mid-flow companion `runlog-author` proposes publication right after a third-party-system gotcha is solved; harvest catches the ones it missed. At the end of a session the user invokes `/runlog:harvest`, the skill scans the just-finished conversation plus the last few git commits for external-dependency findings, scores and dedups them, surfaces a numbered picker, and for each item the user picks routes the draft through the canonical [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) flow at its Step 2.

Verification, signing, and `runlog_submit` are unchanged. The only genuinely new surface is **candidate extraction from session context** plus the **picker UX**. Everything else is reuse.

## When to Use This Skill

### Use it when ALL of these hold

1. The session is winding down — work is committed, or the user has signalled they are about to step away.
2. The session touched **third-party systems** (public APIs, published frameworks, OSS libraries, standard protocols) — same scope rule as the read skill and runlog-author. Mirrors [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).
3. **Team memory does not already cover** what was learned. CLAUDE.md, Cursor rules, mem0, project docs, prior conversation are all faster and free; Runlog is the cross-org blind-spot.
4. The user invoked harvest **explicitly**. Harvest never auto-fires. Heuristics may surface "you might want to harvest" once at session end; explicit invocation is the only path that drafts.

### Do NOT use it when

- The session was internal-only — proprietary code, team conventions, bespoke tooling. Internal knowledge belongs in team memory; harvest must not draft it.
- The user's machine is missing prerequisites for the canonical author flow (verifier binary, keypair, `RUNLOG_API_KEY`). Surface a single diagnostic and stop.
- Cross-session aggregation is requested. Harvest processes one session per invocation. Harvesting across multiple past sessions is out of scope for v0.
- The user has runlog-author available mid-flow and the gotcha was just solved. Runlog-author handles that case; harvest is for the leftovers.

## Decision Flow

```text
User invokes /runlog:harvest
        │
        ▼
  Pre-flight check (verifier + keypair + RUNLOG_API_KEY)
        │
    ┌───┴───┐
    │       │
   Gap     Clean
    │       │
   surface  ▼
   missing  Step 1 — Scan candidates
   stop     (in-frame session context + git log --oneline -10)
                  │
                  ▼
          Step 2 — Score and dedup
          (four-point check per candidate; runlog_search per survivor)
                  │
              ┌───┴───┐
              │       │
            score    score
            < 0.7    >= 0.7
              │       │
            drop      ▼
                     dedup-flag matches as "similar entry: <id>"
                          │
                          ▼
                  Step 3 — Picker UX
                  (numbered list, comma-select grammar,
                   per-item edit, default skip on uncertainty)
                          │
                      ┌───┴───┐
                      │       │
                    none     1+ picked
                      │       │
                     stop     ▼
                            Step 4 — Route to runlog-author
                            (each picked item enters
                             runlog-author/SKILL.md Step 2 — Draft)
                                  │
                                  ▼
                            Verifier loop + sign + runlog_submit
                            (unchanged from runlog-author)
```

## Prerequisites

Identical to runlog-author. A **one-time pre-flight check** runs on first invocation; if any prerequisite is missing, emit a single human-readable diagnostic and stop — do not start scanning candidates.

| Prerequisite | Check | User action if missing |
|---|---|---|
| `runlog-verifier` binary on `$PATH` | `command -v runlog-verifier` | Install from [the latest release](https://github.com/runlog-org/runlog-verifier/releases/latest); see [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) §Setup |
| Ed25519 keypair at `~/.runlog/key` | `test -f ~/.runlog/key` | `runlog-verifier register --email <addr>` |
| `RUNLOG_API_KEY` set | `[ -n "$RUNLOG_API_KEY" ]` | See [`../claude-code/SKILL.md`](../claude-code/SKILL.md) §Setup |
| Reachable session context | In-frame conversation history (fallback) or host transcript file | Adapter publishes the discovery path; falls back to in-frame context per the contract |

## The Harvest Flow

Four steps, run in order. Steps may not be skipped or reordered.

### Step 1 — Scan candidates

Two sources, both consulted on every invocation:

1. **In-frame session context.** The conversation the model already sees. For each turn-pair where the agent solved a problem on a third-party system, emit a one-line description: *"user hit X on third-party-system Y; agent fixed by doing Z."* Most modern hosts give the model several thousand tokens of session context already; this is the primary signal.
2. **Recent git commits in the workspace.** Default `git log --oneline -10`. Commit messages or diffs that hint at an external-dependency fix (third-party API path in the diff, package name in the message, error string copied from a vendor's error response) become candidates. Each emits the same one-line description shape.

Some hosts expose a readable session transcript on disk (e.g. `~/.claude/projects/<encoded>/<session>.jsonl` for Claude Code). Per the cross-vendor contract, when an adapter knows its host's transcript path it MAY use it as a richer signal — but the canonical body assumes the in-frame fallback because it works on every host.

### Step 2 — Score and dedup

Each candidate gets the four-point classification check, mirroring [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md):

1. **Scope.** Is the fix on a third-party system (public API, published framework, OSS library, standard protocol)? Internal code → reject the candidate here, never surface.
2. **Team memory.** Does the team's own memory (CLAUDE.md, Cursor rules, mem0, project docs) already cover this? If yes, drop.
3. **Dedup.** Run `runlog_search` against the candidate's keywords. If a sufficiently-similar entry exists, flag the candidate inline as *"similar entry: `<entry_id>`"* and drop from the picker — surface for `runlog_report` instead, do not draft a duplicate.
4. **Falsifiability.** Does the candidate have a concrete failed approach + concrete working approach + observable difference? "I read the docs more carefully" is not falsifiable. Drop.

The score is `yes-votes / 4`. **Surface only candidates with score ≥ 0.7.** That maps to "passed three of four"; passing fewer than three is too noisy to surface and bias toward false negatives is the design intent. Adapters MAY raise the threshold; they MUST NOT lower it.

The dedup check is the only one that produces an inline note — flagged candidates are visible to the user as *"similar entry: <id>"* but are not picker-eligible. Score-floor drops are silent.

### Step 3 — Picker UX

Render surviving candidates as a numbered list. Each row shows the one-line description and the score:

```text
1. user hit X on third-party-system Y; agent fixed by Z. [score 0.75]
2. user hit P on Q; agent fixed by R. [score 1.00]
3. user hit M on N; agent fixed by O. [score 0.75; similar entry: kb-1234]
```

(Row 3 is dedup-flagged and not picker-eligible — shown for transparency, marked accordingly.)

Accept user input following the comma-select grammar (formalised in §Picker Contract below). Bias toward false negatives: the prompt defaults to *"skip"* when in doubt. The skill MUST NOT auto-pick anything; explicit confirmation is required.

Per-item **edit-before-submit** is available. Before routing a picked candidate to runlog-author, offer the user the chance to rewrite the one-line description inline. This is the last opportunity to reshape the framing before the runlog-author Step 2 draft pass takes over.

### Step 4 — Route through runlog-author

Each selected candidate enters [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at its **Step 2 — Draft the entry from session context**. From there the canonical author flow takes over: it drafts the YAML against `runlog-schema/entry.schema.yaml`, runs the local verifier loop with the 5-round retry cap, and on `verified` calls `runlog_submit` with the signed bundle.

Harvest MUST NOT reimplement the verifier loop. Harvest MUST NOT have its own submit path. Harvest's job ends when the picked candidate is handed to runlog-author Step 2; everything after that is the author skill's responsibility.

If multiple candidates are picked, route them sequentially through runlog-author. Each candidate is its own complete pass through the author flow (Steps 2 → 3 → 4); they do not share verifier state.

## Picker Contract

The user input grammar is fixed:

```text
selection := <item>(',' <item>)* | 'all' | 'none'
item      := <n> | 'skip' <n>
n         := positive integer matching a row number
```

- `1, 3` — pick rows 1 and 3.
- `all` — pick every picker-eligible row (dedup-flagged rows are never picker-eligible).
- `none` (or empty input) — pick nothing; harvest exits without drafting.
- `skip 2` — explicitly mark row 2 as skipped. Useful when combined with `all` to express "all except 2" as `all, skip 2`.

The grammar is the same on every adapter. The vendor's chat UI may render the prompt differently; the input shape is normative.

When parsing input, unrecognised tokens (typos, out-of-range integers) MUST surface a single diagnostic and re-prompt — they MUST NOT be interpreted as "skip everything" or "pick everything." Ambiguity goes back to the user.

## What This Skill MUST NOT Do

Derived from the load-bearing invariants in `CLAUDE.md` and the cross-vendor contracts. Violating any of them collapses the product.

- **MUST NOT auto-submit any candidate** without explicit user confirmation in the picker. Heuristic surfacing is allowed; auto-drafting is not. (CLAUDE.md invariant on "no humans in the loop" applies to trust scoring, not to the submission gate; the human IS the loop on the submission decision.)
- **MUST NOT submit candidates that failed any of the four-point checks** (scope, team-memory, dedup, falsifiability). The score floor is the gate; below it the candidate is invisible to the picker. (Mirrors [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).)
- **MUST NOT bypass the runlog-author verification loop.** Selected candidates route through [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; there is no alternative submit path. (Mirrors [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) — the verifier is the gate, not a suggestion.)
- **MUST NOT include real credentials, internal hostnames, or PII** in drafted candidates. Hard-rejects are caught client-side as a usability matter; the server-side blocklist is a last line of defence. (CLAUDE.md invariant #4.)
- **MUST NOT process more than one session per `/runlog:harvest` invocation.** Cross-session aggregation is out of scope for v0; the score floor and dedup pass assume a single session's signal.

## Out of Scope for v0

- **Cross-session aggregation.** One session per invocation. Multi-session harvests are a measurement question, not a correctness one — defer until real harvest volume justifies it.
- **Calibrated probability scores.** The four-point check produces a soft heuristic (`yes-votes / 4`), not a calibrated probability. Revisit in M03 if calibration becomes meaningful.
- **Per-host transcript helpers.** The canonical body assumes in-frame session context; per-adapter transcript-discovery helpers may ship later as an optimisation. Not a blocker today.
- **Auto-fire on session end.** Harvest is explicit-invocation only. Heuristics may suggest harvest at session end; they MUST NOT run it.
- **Server-side `submission_source: harvest | author` provenance.** Tracked client-side via local logs only; adding a schema field cuts a schema train and is deferred.

## Cross-Vendor Parity

This skill body is deliberately framework-agnostic. The canonical body lives at this file's path. Per-vendor adapters under `<vendor>/runlog-harvest.md` swap orchestration glue (how the skill is invoked, how the picker prompt is rendered, where the draft is persisted on disk, how the host's session transcript is discovered) — they do **not** re-author the contract.

The cross-vendor invariants every adapter MUST preserve live in [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). Author-side invariants the harvest flow inherits via Step 4 are in [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md). Read-side invariants the four-point check inherits are in [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md).

## Setup

Harvest assumes the read-side `runlog` skill and the `runlog-author` skill are already configured (see [`../claude-code/SKILL.md`](../claude-code/SKILL.md) §Setup and [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) §Setup). Harvest adds no new prerequisites beyond those — the verifier binary, the keypair, and `RUNLOG_API_KEY` are inherited from runlog-author.

The vendor-specific invocation literal (`/runlog:harvest` for Claude Code; `@runlog harvest` for Cursor; etc.) is published per-adapter. See your host's `<vendor>/runlog-harvest.md` for the literal that surfaces this skill in your environment.

## Further Reading

| Document | Read when working on |
|---|---|
| [`./DESIGN.md`](./DESIGN.md) | Design rationale and open questions for harvest |
| [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) | Canonical author body — Step 2 is the hand-off point from harvest |
| [`../runlog-author/DESIGN.md`](../runlog-author/DESIGN.md) | Author-side design rationale; harvest inherits the verifier discipline |
| [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) | Harvest-side cross-vendor invariants |
| [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) | Author-side cross-vendor invariants (inherited via Step 4) |
| [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md) | The cross-vendor read+write client contract |
| [`../claude-code/SKILL.md`](../claude-code/SKILL.md) | Read-side companion (`runlog_search` / `runlog_report` flow) |

---

Skill version follows the runlog-skills repo tag.
