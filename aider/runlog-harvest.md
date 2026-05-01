---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for Aider. Scans the in-frame conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Aider-specific orchestration around the canonical body at runlog-harvest/SKILL.md.
---

## runlog-harvest (Aider adapter)

This is the Aider wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan → Score+Dedup → Pick → Route-to-author), the four-point classification check, the score floor (≥ 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from `runlog-harvest/SKILL.md`. **Read that file first** — this adapter only adds Aider-specific glue.

Harvest-side cross-vendor invariants live at [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). Aider adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Aider specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | User explicit only — Aider doesn't have a heuristic prompt surface. The user runs `/ask harvest this session to runlog` or types `harvest that session to runlog` directly. Explicit invocation is the only path. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Aider's `/run` command runs shell commands and pipes output back into the chat. During Step 4 the agent issues `/run runlog-verifier verify .runlog-author/<unit_id>.yaml` for each picked candidate. User confirms each `/run`. |
| **Agent-loop iteration** | "Sequential per-candidate route to runlog-author" | Each picked candidate is its own complete pass through runlog-author Step 2 → 3 → 4, expressed as a sequence of chat turns and `/run` invocations. The 5-round verifier retry cap (inherited from runlog-author) applies per-candidate. |
| **Session-transcript discovery** | "In-frame fallback; per-host transcript optional" | Aider keeps `.aider.chat.history.md` in the working directory. Per harvest contract OQ #3 the canonical body falls back to in-frame conversation context; the chat-history file is an OPTIONAL convenience for users who want explicit transcript scanning (`/run cat .aider.chat.history.md` to feed it into the agent). The default and normative path is in-frame. |
| **Picker rendering** | "Numbered list, comma-select grammar" | Aider's chat output renders the numbered list as plain text. User replies in chat following the comma-select grammar. Per-item edit-before-submit is a follow-up turn where the user replies with the rewritten one-line summary for a given candidate. |
| **Draft persistence** | "Vendor scratch dir" | Write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` in the workspace, edited as normal repo files via `/code` or `/edit`. Each draft is a real file the user can inspect before approving the verifier call. Distinct from runlog-author's `.runlog-author/` so the two skills do not clobber each other's scratch state. Gitignored; cleaned up on successful submit. |

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
6. **Routing through runlog-author for verification + submission.** Aider MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; the verifier loop and signed bundle are produced there. If the user denies `/run` for the verifier, the skill MUST refuse to submit.
7. The MUST NOT list in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## Aider-specific pre-flight check

The agent issues a chained check via `/run` on first invocation and parses the output:

```sh
command -v runlog-verifier && \
  test -f ~/.runlog/key && \
  test -n "$RUNLOG_API_KEY" && \
  echo "OK"
```

If the chained check returns anything other than `OK`, the agent surfaces a single diagnostic and stops. The user resolves and re-invokes.

If the workspace has no git history (`.git` absent), harvest still runs against the in-frame conversation alone — the git source is a backup, not a hard dependency. If `.aider.chat.history.md` is present and the user opts into transcript scanning, the agent reads it via `/run cat`.

## Aider-specific invocation

Aider has no heuristic prompt surface. Invocation is always explicit. The published literal is:

```text
> /ask harvest this session to runlog
```

Plain-language equivalents typed directly also route into the same flow:

```text
> harvest that session to runlog
> scan this session for runlog candidates
```

The `/ask` prefix is the natural verbal-invocation form when the user wants the agent to drive a multi-step flow without immediately editing code. The agent then writes per-candidate drafts via `/code` (so the user can inspect and edit), surfaces the numbered picker in chat, parses the comma-select reply, offers per-item edit-before-submit, and proposes the `/run runlog-verifier verify` for each picked candidate. The user approves each step.

## Setup

This adapter assumes the read-side Aider skill and the `runlog-author` Aider adapter are already configured (see `skills/aider/SKILL.md §Setup` and [`./runlog-author.md`](./runlog-author.md) §Setup). Harvest adds no new prerequisites beyond those — the verifier binary, the keypair, and `RUNLOG_API_KEY` are inherited.

Append this adapter to `CONVENTIONS.md` or load via `--read`:

```sh
# Pattern A
echo '' >> CONVENTIONS.md
cat skills/aider/runlog-harvest.md >> CONVENTIONS.md

# Pattern B
cp skills/aider/runlog-harvest.md .aider/runlog-harvest.md
# then: aider --read .aider/runlog-harvest.md
```

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 2). End-to-end functionality depends on the same F24 prerequisites runlog-author depends on (verifier release artifact, public-key registration, `runlog-verifier register --email` UX) — all shipped under F24 (2026-04-28).

## Aider-specific cautions

- Aider's `/run` requires user approval per command. The verification loop will trigger 1–N approval prompts where N ≤ 5, **per picked candidate**. Users who want to streamline this can use Aider's `--yes-always` flag, but auto-approving the `runlog_submit` MCP call is **NOT recommended** — a prompt-injected context could otherwise publish without your review.
- Aider's chat history is the manifest carrier. Long sessions accumulate context, which is fine for harvest's in-frame scan but may slow turn latency on very long sessions.
- Aider's diff-based editing means draft YAML changes show up as repo diffs in `.runlog-harvest/` — a feature, not a bug, for review before approving the verifier call.

## Further Reading

- [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md) — canonical harvest body (READ FIRST)
- [`../runlog-harvest/DESIGN.md`](../runlog-harvest/DESIGN.md) — design rationale and open questions
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — harvest-side cross-vendor invariants
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 4 hand-off target
- [`./runlog-author.md`](./runlog-author.md) — Aider author adapter (mid-flow companion)
- [`./SKILL.md`](./SKILL.md) — read-side Aider adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
