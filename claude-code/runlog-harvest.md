---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for Claude Code. Scans the in-frame conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Claude-Code-specific orchestration around the canonical body at runlog-harvest/SKILL.md.
---

## runlog-harvest (Claude Code adapter)

This is the Claude Code wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan → Score+Dedup → Pick → Route-to-author), the four-point classification check, the score floor (≥ 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from `runlog-harvest/SKILL.md`. **Read that file first** — this adapter only adds Claude-Code-specific glue.

Harvest-side cross-vendor invariants live at [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). Claude Code adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Claude Code specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | `/runlog:harvest` slash command, surfaced via the plugin's `commands/harvest.md`. Plain-language invocations ("harvest the session", "scan for runlog candidates") also route into the same flow. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Claude Code's Bash tool. The agent must have Bash access; if blocked, surface a single diagnostic asking the user to grant Bash use for this session. |
| **Agent-loop iteration** | "Sequential per-candidate route to runlog-author" | Each picked candidate is its own complete pass through runlog-author Step 2 → 3 → 4. Claude Code's agent stays in the loop across turns; the 5-round verifier retry cap (inherited from runlog-author) applies per-candidate. |
| **Session-transcript discovery** | "In-frame fallback; per-host transcript optional" | Claude Code stores transcripts at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl` — the adapter MAY read this for richer signal, but the in-frame conversation is the normative fallback and works on every machine. |
| **Picker rendering** | "Numbered list, comma-select grammar" | Claude Code's chat panel renders the numbered list inline; user replies in chat with the comma-select grammar (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`). Per-item edit-before-submit is a follow-up turn — the agent surfaces the candidate's one-line summary, the user edits it inline, and only then does the verifier dispatch. |
| **Draft persistence** | "Vendor scratch dir" | Write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` in the workspace (gitignored). Distinct from runlog-author's `.runlog-author/` so the two skills do not clobber each other's scratch state. Cleaned up on successful submit. |

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
6. **Routing through runlog-author for verification + submission.** Claude Code MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; the verifier loop and signed bundle are produced there. If Bash access is blocked or the verifier binary is missing, the skill MUST refuse to submit.
7. The MUST NOT list in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## Claude-Code-specific pre-flight check

Run on first invocation per session. All gaps surface as a single human-readable diagnostic; do not partial-scan or partial-draft.

```sh
command -v runlog-verifier   # verifier binary on $PATH (inherited from runlog-author)
test -f ~/.runlog/key        # Ed25519 keypair generated and registered
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If `runlog-verifier` is missing, instruct the user to install it (see [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) §Setup for the platform-keyed download).

If `~/.runlog/key` is missing:

```sh
runlog-verifier register --email <your-email>
```

If `$RUNLOG_API_KEY` is unset, instruct the user to set it in the shell that launched Claude Code (the plugin install path also writes it via the read-side setup; see [`./SKILL.md`](./SKILL.md) §Setup).

If the workspace has no git history (`.git` absent), harvest still runs against the in-frame conversation alone — the git source is a backup, not a hard dependency.

## Claude-Code-specific invocation patterns

The slash command is the primary entry point:

- `/runlog:harvest` — surfaced by the plugin via `commands/harvest.md`. This is the documented form; users see it via Claude Code's `/help`.

Plain-language invocations also work:

- "harvest the session"
- "scan this session for runlog candidates"
- "any external-dep findings worth publishing?"

All routes converge on the same four-step flow.

## Setup

This adapter assumes the read-side `runlog` skill and the `runlog-author` skill are already configured (see [`./SKILL.md`](./SKILL.md) §Setup and [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) §Setup). Harvest adds no new prerequisites beyond those.

The plugin marketplace install (path 1 in [`../README.md`](../README.md) §Install) is the smoothest:

```text
/plugin marketplace add runlog-org/runlog-skills
/plugin install runlog
```

Once installed, `/runlog:harvest` is available in any session. The slash command stub at `commands/harvest.md` delegates to this adapter, which delegates to the canonical body at [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 1). End-to-end functionality depends on the same F24 prerequisites runlog-author depends on (verifier release artifact, public-key registration flow, `runlog-verifier register --email` UX) — all shipped under F24 (2026-04-28).

## Further Reading

- [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md) — canonical harvest body (READ FIRST)
- [`../runlog-harvest/DESIGN.md`](../runlog-harvest/DESIGN.md) — design rationale and open questions
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — harvest-side cross-vendor invariants
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 4 hand-off target
- [`./SKILL.md`](./SKILL.md) — read-side Claude Code adapter

---

Adapter version tracks the runlog-skills repo tag.
