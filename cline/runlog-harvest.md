---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for Cline. Scans the in-frame conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Cline-specific orchestration around the canonical body at skills/runlog-harvest/SKILL.md.
---

## runlog-harvest (Cline adapter)

This is the Cline wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan → Score+Dedup → Pick → Route-to-author), the four-point classification check, the score floor (≥ 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from `skills/runlog-harvest/SKILL.md`. **Read that file first** — this adapter only adds Cline-specific glue.

Harvest-side cross-vendor invariants live at [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). Cline adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Cline specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | Plain-language request in chat — `"harvest this session to runlog"` is the documented invocation literal. Cline does not have a built-in slash-command surface, so explicit verbal invocation is the primary path. If Cline's Plan/Act flow surfaces a session-end heuristic in a given build, the heuristic MAY suggest harvest at session end; it MUST NOT auto-fire. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Cline's `execute_command` tool. Each verifier run (in Step 4 of harvest, which routes to runlog-author) is a single command requiring user approval, or auto-approval if the user has whitelisted `runlog-verifier`. The recent-commits scan in Step 1 also goes through `execute_command`, calling `git log --oneline -10`. |
| **Agent-loop iteration** | "Sequential per-candidate route to runlog-author" | Each picked candidate is its own complete pass through runlog-author Step 2 → 3 → 4. The 5-round verifier retry cap (inherited from runlog-author) applies per-candidate; each retry is a Plan-mode → Act-mode round, the cap is on `runlog-verifier verify` invocations, not on Plan/Act transitions. |
| **Session-transcript discovery** | "In-frame fallback; per-host transcript optional" | Cline's chat history is held inside the VS Code extension's storage and is not directly readable from the agent. Per the harvest contract's OQ #3 resolution, this adapter falls back to in-frame conversation context — the model's existing turn buffer is the primary signal. |
| **Picker rendering** | "Numbered list, comma-select grammar" | Cline's chat panel renders the numbered list. The user replies in chat with the comma-select grammar (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`). Per-item edit-before-submit is a follow-up Plan-mode turn: the agent surfaces the candidate's one-line summary, the user edits it, and only then does Act-mode kick the verifier. |
| **Draft persistence** | "Vendor scratch dir" | Write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` (workspace-scoped, gitignored). Cline's file-write tool persists across Plan/Act transitions cleanly. Distinct from `runlog-author`'s `.runlog-author/` so the two skills do not clobber each other's scratch state. |

```text
# add to your project's .gitignore:
.runlog-harvest/
```

## What this adapter MUST NOT change

Per [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md):

1. The four-point client contract ([`../common/four-point-client-contract.md`](../common/four-point-client-contract.md)) — the four-point check on each candidate.
2. The four-step harvest flow (steps may not be skipped or reordered).
3. The score floor (≥ 0.7). The adapter MAY raise it; MUST NOT lower it.
4. The comma-select picker grammar (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`).
5. Per-item edit-before-submit availability.
6. **Routing through runlog-author for verification + submission.** Cline MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; the verifier loop and signed bundle are produced there. If `execute_command` is denied or the verifier binary is missing, the skill MUST refuse to submit.
7. The MUST NOT list in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## Cline-specific pre-flight checks

Run on first invocation per session. All gaps surface as a single diagnostic; do not partial-scan or partial-draft.

```sh
command -v runlog-verifier   # verifier binary on $PATH (inherited from runlog-author)
test -f ~/.runlog/key        # Ed25519 keypair generated and registered
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If any check fails, Cline emits the gap and a single fix command, then stops. The user resolves and re-runs the harvest invocation.

If the workspace has no git history (`.git` absent), harvest still runs against the in-frame conversation alone — the git source is a backup, not a hard dependency.

## Cline-specific invocation patterns

The published invocation literal is plain-language:

- **`"harvest this session to runlog"`** — typed verbatim into Cline's chat. Cline doesn't have its own slash-command literal, so this is the documented form.

Other plain-language invocations route into the same flow:

- "scan this session for runlog candidates"
- "any external-dep findings worth publishing?"
- "run runlog harvest on this session"

If a Cline build surfaces a session-end heuristic, the heuristic MAY suggest harvest; explicit user confirmation is still required before drafting.

## Auto-approval suggestions

To reduce friction during Step 4 (which routes to runlog-author and runs the verifier loop), the user MAY auto-approve `runlog-verifier` in Cline's settings. The verifier reads only the draft file and writes nothing outside `~/.runlog/`, `/tmp/`, and stdout, so auto-approval is safe.

Auto-approving the `runlog_submit` MCP call is **NOT recommended**. Submission is the final review gate; harvest's picker is the surfacing heuristic, not the submission gate. Keep `runlog_submit` off Cline's MCP auto-approve list.

## Setup

This adapter assumes the read-side Cline skill and the `runlog-author` Cline adapter are already configured (see [`./SKILL.md`](./SKILL.md) §Setup and [`./runlog-author.md`](./runlog-author.md) §Setup). Harvest adds no new prerequisites beyond those — the verifier binary, the keypair, and `RUNLOG_API_KEY` are inherited from runlog-author.

Install this adapter as a Cline rule:

```sh
mkdir -p .clinerules
cp skills/cline/runlog-harvest.md .clinerules/runlog-harvest.md
```

Cline loads every `.md` in `.clinerules/`; this adapter loads alongside the read-side `runlog.md` and the `runlog-author.md` rule.

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 2). End-to-end functionality depends on the same F24 prerequisites the Cline `runlog-author` adapter depends on.

## Further Reading

- [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md) — canonical harvest body (READ FIRST)
- [`../runlog-harvest/DESIGN.md`](../runlog-harvest/DESIGN.md) — design rationale and open questions
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — harvest-side cross-vendor invariants
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 4 hand-off target
- [`./runlog-author.md`](./runlog-author.md) — Cline `runlog-author` adapter
- [`./SKILL.md`](./SKILL.md) — read-side Cline adapter

---

Adapter version tracks the runlog-skills repo tag.
