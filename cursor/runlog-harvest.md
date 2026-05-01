---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for Cursor. Scans the in-frame conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Cursor-specific orchestration around the canonical body at skills/runlog-harvest/SKILL.md.
---

## runlog-harvest (Cursor adapter)

This is the Cursor wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan → Score+Dedup → Pick → Route-to-author), the four-point classification check, the score floor (≥ 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from `skills/runlog-harvest/SKILL.md`. **Read that file first** — this adapter only adds Cursor-specific glue.

Harvest-side cross-vendor invariants live at [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). Cursor adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Cursor specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | `@runlog harvest` in Cursor's agent mode is the documented form; if the user's Cursor build exposes a slash-command surface, the same literal works there. Plain-language requests ("harvest this session to runlog", "scan the session for runlog candidates") route into the same flow. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Cursor's terminal-tool grant — same prerequisite as Cursor's `runlog-author` adapter. Required to drive the runlog-author verifier loop in Step 4 of the harvest flow. If terminal access is blocked, surface a single diagnostic asking the user to grant it for this session. |
| **Agent-loop iteration** | "Sequential per-candidate route to runlog-author" | Each picked candidate is its own complete pass through runlog-author Step 2 → 3 → 4. Cursor's agent stays in the loop across turns; the 5-round verifier retry cap (inherited from runlog-author) applies per-candidate. |
| **Session-transcript discovery** | "In-frame fallback; per-host transcript optional" | Cursor stores chat history in IndexedDB under `.cursor/chat-history`, which is not directly readable from the agent. Per the harvest contract's OQ #3 resolution, this adapter falls back to in-frame conversation context — the model's existing turn buffer is the primary signal. The recent-commits scan source uses `/run git log --oneline -10` via Cursor's terminal tool. |
| **Picker rendering** | "Numbered list, comma-select grammar" | Cursor's chat panel renders the numbered list inline. The user replies in chat following the comma-select grammar (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`). Per-item edit-before-submit is a follow-up turn: the agent surfaces the candidate's one-line summary, the user edits it inline, the agent then drafts. |
| **Draft persistence** | "Vendor scratch dir" | Write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` in the workspace (gitignored). Distinct from `runlog-author`'s `.runlog-author/` so the two skills do not clobber each other's scratch state. The directory is cleaned up after every selected candidate has been successfully submitted. |

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
6. **Routing through runlog-author for verification + submission.** Cursor MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; the verifier loop and signed bundle are produced there. If terminal access is blocked or the verifier binary is missing, the skill MUST refuse to submit.
7. The MUST NOT list in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## Cursor-specific pre-flight checks

Run on first invocation per session. All gaps surface as a single human-readable diagnostic; do not partial-scan or partial-draft.

```sh
command -v runlog-verifier   # verifier binary on $PATH (inherited from runlog-author)
test -f ~/.runlog/key        # Ed25519 keypair generated and registered
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If `runlog-verifier` is missing, instruct the user to install it (see [`./runlog-author.md`](./runlog-author.md) §Setup for the platform-keyed download).

If `~/.runlog/key` is missing:

```sh
runlog-verifier register --email <your-email>
```

If `$RUNLOG_API_KEY` is unset, instruct the user to set it in the shell that launched Cursor (Cursor inherits the parent shell's env; values must be set before launch or via Cursor's own env-var settings).

If the workspace has no git history (`.git` absent), harvest still runs against the in-frame conversation alone — the git source is a backup, not a hard dependency.

## Cursor-specific invocation patterns

The agent-mode literal is the primary entry point:

- **`@runlog harvest`** — Cursor agent-mode. This is the documented form; users see it via Cursor's agent affordances.

If the user's Cursor build exposes a slash-command surface, the same literal works there (`/runlog-harvest`). Plain-language invocations also route into the same flow:

- "harvest this session to runlog"
- "scan this session for runlog candidates"
- "any external-dep findings worth publishing?"

All routes converge on the same four-step flow.

## Setup

This adapter assumes the read-side Cursor skill and the `runlog-author` Cursor adapter are already configured (see [`./SKILL.md`](./SKILL.md) §Setup and [`./runlog-author.md`](./runlog-author.md) §Setup). Harvest adds no new prerequisites beyond those — the verifier binary, the keypair, and `RUNLOG_API_KEY` are inherited from runlog-author.

Install this adapter as a Cursor rule:

```sh
# Project-scoped (recommended for repos with shared harvest conventions)
mkdir -p .cursor/rules
cp skills/cursor/runlog-harvest.md .cursor/rules/runlog-harvest.mdc

# Global
mkdir -p ~/.cursor/rules
cp skills/cursor/runlog-harvest.md ~/.cursor/rules/runlog-harvest.mdc
```

The adapter loads alongside the read-side `runlog.mdc` and the `runlog-author.mdc` rule. All three together implement the four-point contract end-to-end.

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 2). End-to-end functionality depends on the same F24 prerequisites the Cursor `runlog-author` adapter depends on.

## Further Reading

- [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md) — canonical harvest body (READ FIRST)
- [`../runlog-harvest/DESIGN.md`](../runlog-harvest/DESIGN.md) — design rationale and open questions
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — harvest-side cross-vendor invariants
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 4 hand-off target
- [`./runlog-author.md`](./runlog-author.md) — Cursor `runlog-author` adapter
- [`./SKILL.md`](./SKILL.md) — read-side Cursor adapter

---

Adapter version tracks the runlog-skills repo tag.
