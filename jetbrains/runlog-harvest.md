---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for JetBrains AI Assistant. Scans the in-frame conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. JetBrains-specific orchestration around the canonical body at runlog-harvest/SKILL.md.
---

## runlog-harvest (JetBrains AI Assistant adapter)

This is the JetBrains wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan → Score+Dedup → Pick → Route-to-author), the four-point classification check, the score floor (≥ 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from `runlog-harvest/SKILL.md`. **Read that file first** — this adapter only adds JetBrains-specific glue.

Harvest-side cross-vendor invariants live at [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). JetBrains adapters MAY vary orchestration glue but MUST NOT vary the contract.

> **VERIFY against current JetBrains AI Assistant docs** before publishing. The plugin's tool-use, terminal access, and file-edit capabilities vary across IDE products and plugin versions.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | JetBrains specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | Plain-language verbal request in the AI Assistant chat panel: `harvest this session to runlog`. Slash-command and mention surfaces evolve per IDE/plugin version; explicit verbal invocation is the stable form and the published literal. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Junie's terminal-tool integration (when supported in the installed plugin version). During Step 4 the agent runs `runlog-verifier verify .runlog-author/<unit_id>.yaml` for each picked candidate. User approves each command unless an allow-list is configured. If terminal-tool execution is not available in the installed AI Assistant version, the adapter MUST refuse to invoke Step 4. |
| **Session-context discovery** | "In-frame fallback; per-host transcript optional" | Falls back to in-frame conversation context. Recent-commits scan via the IDE's built-in terminal driven by AI Assistant on supported versions. No JetBrains-specific transcript file is consulted. |
| **Picker rendering** | "Numbered list + comma-select grammar" | The AI Assistant chat panel renders the numbered list. User replies in chat following the comma-select grammar. Per-item edit-before-submit is a follow-up turn where the user replies with the rewritten one-line summary. |
| **Draft persistence** | "Vendor scratch dir" | Write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` in the workspace. Visible in the IDE's project tool window; the user can inspect and edit through the editor before approving the verifier call. Distinct from runlog-author's `.runlog-author/` so the two skills do not clobber each other's scratch state. Gitignored; cleaned up on successful submit. |

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
6. **Routing through runlog-author for verification + submission.** AI Assistant MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; the verifier loop and signed bundle are produced there. If terminal access is unavailable in the installed plugin version, the skill MUST refuse to submit.
7. The MUST NOT list in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## JetBrains-specific pre-flight check

```sh
command -v runlog-verifier
test -f ~/.runlog/key
[ -n "$RUNLOG_API_KEY" ]
```

Also verify the AI Assistant version exposes terminal-tool execution. If terminal-tool access is not available, surface a single diagnostic and stop. The user can fall back to running the verifier manually outside the IDE for runlog-author's loop, but harvest's Step 4 MUST refuse to invoke without terminal access.

## JetBrains-specific invocation

JetBrains AI Assistant's slash-command and mention surfaces evolve per IDE version, so the adapter publishes a stable plain-language literal. The published invocation is:

```text
harvest this session to runlog
```

Type it into the AI Assistant chat panel (Junie or chat mode, depending on installed version). Plain-language equivalents also work:

```text
scan this session for runlog candidates
any external-dep findings worth publishing?
```

The agent then writes per-candidate drafts to `.runlog-harvest/`, surfaces the numbered picker in the chat panel, parses the comma-select reply, offers per-item edit-before-submit, and runs the verifier via the terminal tool for each picked candidate.

## Setup

This adapter assumes the read-side JetBrains skill and the `runlog-author` JetBrains adapter are already configured (see `skills/jetbrains/SKILL.md §Setup` and [`./runlog-author.md`](./runlog-author.md) §Setup). Harvest adds no new prerequisites beyond those — the verifier binary, the keypair, and `RUNLOG_API_KEY` are inherited.

Add this adapter to the project's AI guidelines (Settings → Tools → AI Assistant → Guidelines, or the project-scoped guidelines file) — same surface as the read skill and the author adapter.

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 2). End-to-end functionality depends on the same F24 prerequisites runlog-author depends on (verifier release artifact, public-key registration, `runlog-verifier register --email` UX) — all shipped under F24 (2026-04-28).

## JetBrains-specific cautions

- AI Assistant's classic chat mode may not support tool use; Junie (the agent mode) is the surface that dispatches MCP tool calls and terminal commands. Confirm you're in the right mode before invoking harvest.
- JetBrains AI's tool-use guarantees vary across IDE products and plugin versions. If the verification loop can't run end-to-end (no terminal tool), the skill MUST hand back to the user rather than partial-submit.
- The IDE's environment variables are inherited from the launching shell on Linux/macOS. On Windows or when launching from a desktop launcher, set `RUNLOG_API_KEY` via the IDE's environment-variable settings.

## Further Reading

- [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md) — canonical harvest body (READ FIRST)
- [`../runlog-harvest/DESIGN.md`](../runlog-harvest/DESIGN.md) — design rationale and open questions
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — harvest-side cross-vendor invariants
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 4 hand-off target
- [`./runlog-author.md`](./runlog-author.md) — JetBrains author adapter (mid-flow companion)
- [`./SKILL.md`](./SKILL.md) — read-side JetBrains adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
