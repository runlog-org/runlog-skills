---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for Zed Assistant. Scans the in-frame conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Zed-specific orchestration around the canonical body at skills/runlog-harvest/SKILL.md.
---

## runlog-harvest (Zed adapter)

This is the Zed wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan → Score+Dedup → Pick → Route-to-author), the four-point classification check, the score floor (≥ 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from `skills/runlog-harvest/SKILL.md`. **Read that file first** — this adapter only adds Zed-specific glue.

Harvest-side cross-vendor invariants live at [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). Zed adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Zed specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | Plain-language request in the Zed agent panel ("harvest this session to runlog", "scan for runlog candidates"), or `@runlog harvest` if the user has configured Zed's mention surface for the runlog scope. Zed's slash-command surface evolves across releases; explicit verbal invocation is the stable form. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Zed agent's terminal tool. Required for Step 4's verifier loop. Each invocation requires user approval unless allow-listed. If terminal access is denied the skill MUST refuse to submit. |
| **Agent-loop iteration** | "Sequential per-candidate route to runlog-author" | Each picked candidate is its own complete pass through runlog-author Step 2 → 3 → 4. The 5-round verifier retry cap (inherited from runlog-author) applies per-candidate. |
| **Session-context discovery** | "In-frame fallback; per-host transcript optional" | Zed does not expose a stable on-disk transcript path the adapter can rely on. Falls back to in-frame conversation context — the normative fallback per the cross-vendor contract — and uses the agent's terminal tool for the recent-commits scan (`git log --oneline -10`). |
| **Picker rendering** | "Numbered list, comma-select grammar" | The Zed agent panel renders the numbered list inline. The user replies in chat following the comma-select grammar from the canonical body (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`). Per-item edit-before-submit is offered as a follow-up agent turn before the verifier dispatches. |
| **Draft persistence** | "Hold the draft in memory" | Zed Assistant can edit files directly; write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` in the workspace (gitignored). Distinct from runlog-author's `.runlog-author/` so the two skills do not clobber each other's scratch state. The user can inspect the draft in a Zed buffer before approving the verifier call. Cleaned up on successful submit. |

```text
# add to your project's .gitignore:
.runlog-harvest/
```

**Invocation literal published:** plain-language `"harvest this session to runlog"` in the Zed agent panel. Zed's mention surface is too platform-fragmented to fix a single literal across releases; verbal invocation is the stable form.

## What this adapter MUST NOT change

Per [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md):

1. The four-point client contract ([`../common/four-point-client-contract.md`](../common/four-point-client-contract.md)) — the four-point check on each candidate.
2. The four-step harvest flow (steps may not be skipped or reordered).
3. The score floor (≥ 0.7). The adapter MAY raise it; MUST NOT lower it.
4. The comma-select picker grammar (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`).
5. Per-item edit-before-submit availability.
6. **Routing through runlog-author for verification + submission.** Zed MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; the verifier loop and signed bundle are produced there. If terminal access is blocked or the verifier binary is missing, the skill MUST refuse to submit.
7. The MUST NOT list in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## Zed-specific pre-flight checks

Run on first invocation per session. All gaps surface as a single human-readable diagnostic; do not partial-scan or partial-draft.

```sh
command -v runlog-verifier
test -f ~/.runlog/key
[ -n "$RUNLOG_API_KEY" ]
```

If any check fails, the agent emits the gap and a single fix command, then stops. If `runlog-verifier` is missing, see [`./runlog-author.md`](./runlog-author.md) §Setup for the platform-keyed download. If `~/.runlog/key` is missing, run `runlog-verifier register --email <your-email>`.

If the workspace has no git history (`.git` absent), harvest still runs against the in-frame conversation alone — the git source is a backup, not a hard dependency.

## Setup

This adapter assumes the read-side Zed skill and the Zed `runlog-author` adapter are already configured (see [`./SKILL.md`](./SKILL.md) §Setup and [`./runlog-author.md`](./runlog-author.md) §Setup). Harvest adds no new prerequisites beyond those.

Append this adapter to Zed rules:

```sh
# Project-scoped
cat skills/zed/runlog-harvest.md >> .rules

# Or global
cat skills/zed/runlog-harvest.md >> ~/.config/zed/rules.md
```

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 2). End-to-end functionality depends on the same F24 prerequisites runlog-author depends on.

## Zed-specific cautions

- Zed Assistant's tool-use surface depends on agent mode being enabled and the model supporting tool calls. Some configurations (smaller local models, completion-only mode) will not support the harvest verifier loop and the skill MUST refuse to submit.
- For the stdio-bridge MCP setup the local proxy runs as a child process of Zed and inherits Zed's environment; ensure `RUNLOG_API_KEY` is set in the shell that launched Zed.
- Allow-listing the local `runlog-verifier` binary is fine (deterministic, local, signed). Allow-listing or auto-approving the `runlog_submit` MCP call is **NOT recommended** — the user-confirmed picker is the surfacing gate, but the verifier-signed submit is the final integrity gate.
- Picker input arrives as ordinary chat text. Unrecognised tokens (typos, out-of-range integers) MUST surface a single diagnostic and re-prompt — never interpret as "skip everything" or "pick everything." Ambiguity goes back to the user.

## Further Reading

- [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md) — canonical harvest body (READ FIRST)
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — harvest-side cross-vendor invariants
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 4 hand-off target
- [`./runlog-author.md`](./runlog-author.md) — Zed author adapter
- [`./SKILL.md`](./SKILL.md) — read-side Zed adapter

---

Adapter version tracks the runlog-skills repo tag.
