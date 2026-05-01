---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for Windsurf. Scans the in-frame Cascade conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Windsurf-specific orchestration around the canonical body at runlog-harvest/SKILL.md.
---

## runlog-harvest (Windsurf adapter)

This is the Windsurf wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan -> Score+Dedup -> Pick -> Route-to-author), the four-point classification check, the score floor (>= 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md). **Read that file first** — this adapter only adds Windsurf-specific glue.

Harvest-side cross-vendor invariants live at [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md). Windsurf adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Windsurf specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | Plain-language request in Cascade (`"harvest this session to runlog"`, "scan this session for runlog candidates"). Cascade's agent mode is the natural execution context. If the user has configured a runlog mention, `@runlog harvest` also routes here; mention availability is user-config-dependent, so the verbal form is the published literal. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Cascade's terminal tool — same as Windsurf's runlog-author adapter. Recent-commits scan is `git log --oneline -10` via Cascade's terminal grant. Each verifier invocation in Step 4 is a single command; user approval per command unless allow-listed. Allow-listing the local `runlog-verifier` binary is fine (deterministic, local, signed); allow-listing or auto-approving `runlog_submit` is **NOT recommended** — submission is the final review gate. If terminal access is denied the adapter MUST refuse to invoke Step 4 (the verifier loop cannot run). |
| **Agent-loop iteration** | "Sequential per-candidate route to runlog-author" | Each picked candidate is its own complete pass through runlog-author Step 2 -> 3 -> 4 across Cascade turns. The 5-round verifier retry cap (inherited from runlog-author) applies per-candidate. |
| **Session-transcript discovery** | "In-frame fallback; per-host transcript optional" | Cascade exposes no stable on-disk transcript path the adapter can rely on, so harvest falls back to in-frame conversation context (per harvest contract OQ #3). The fallback is normative and works on every Windsurf install. |
| **Picker rendering** | "Numbered list, comma-select grammar" | Cascade renders the numbered list inline in chat. User replies follow the comma-select grammar from the canonical body (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`). Per-item edit-before-submit is offered as a follow-up turn after the user picks. |
| **Draft persistence** | "Vendor scratch dir" | Write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` (workspace-scoped, gitignored). Cascade's file-write tool persists across turns. Distinct from runlog-author's `.runlog-author/` so the two skills do not clobber each other's scratch state. Or use a Windsurf memory to carry draft state if the workspace is read-only. Cleaned up on successful submit. |

```text
# add to your project's .gitignore:
.runlog-harvest/
```

## What this adapter MUST NOT change

Per [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md):

1. The four-point client contract ([`../common/four-point-client-contract.md`](../common/four-point-client-contract.md)) — the four-point check on each candidate.
2. The four-step harvest flow (steps may not be skipped or reordered).
3. The score floor (>= 0.7). The adapter MAY raise it; MUST NOT lower it.
4. The comma-select picker grammar.
5. Per-item edit-before-submit availability.
6. **Routing through runlog-author for verification + submission.** Cascade MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) at Step 2; the verifier loop and signed bundle are produced there. If Cascade's terminal access is denied the skill MUST refuse to invoke Step 4.
7. The MUST NOT list in [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md).

## Windsurf-specific pre-flight checks

Run on first invocation per session. All gaps surface as a single human-readable diagnostic; do not partial-scan or partial-draft.

```sh
command -v runlog-verifier   # verifier binary on $PATH (inherited from runlog-author)
test -f ~/.runlog/key        # Ed25519 keypair generated and registered
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If terminal access is denied (Windsurf supports per-workspace approval), surface a single diagnostic and stop before scanning candidates — without the terminal tool, the verifier loop in Step 4 cannot run, so drafting is pointless.

If the workspace has no git history (`.git` absent), harvest still runs against the in-frame Cascade conversation alone — the git source is a backup, not a hard dependency.

## Windsurf-specific invocation patterns

The plain-language form is the published invocation literal:

- `"harvest this session to runlog"` — the canonical verbal form in Cascade chat. Documented and stable.

Other natural phrasings route into the same flow:

- "scan this session for runlog candidates"
- "any external-dep findings worth publishing?"

`@runlog harvest` works only if the user has configured the runlog mention in Windsurf's mention surface; the verbal form above is the one users should reach for.

## Setup

This adapter assumes the read-side Windsurf skill ([`./SKILL.md`](./SKILL.md)) and the Windsurf runlog-author adapter ([`./runlog-author.md`](./runlog-author.md)) are already configured. Harvest adds no new prerequisites beyond those — the verifier binary, the keypair, and `RUNLOG_API_KEY` are inherited from runlog-author.

Append this adapter to `.windsurfrules` (or paste into Windsurf's global rules):

```sh
echo '' >> .windsurfrules
cat windsurf/runlog-harvest.md >> .windsurfrules
```

Or keep it as a separate workspace doc and reference it from `.windsurfrules` with a one-line pointer.

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 2). End-to-end functionality depends on the same F24 prerequisites runlog-author depends on (verifier release artifact, public-key registration flow, `runlog-verifier register --email` UX) — all shipped under F24 (2026-04-28).

## Further Reading

- [`../runlog-harvest/SKILL.md`](../runlog-harvest/SKILL.md) — canonical harvest body (READ FIRST)
- [`../runlog-harvest/DESIGN.md`](../runlog-harvest/DESIGN.md) — design rationale and open questions
- [`../common/runlog-harvest-contract.md`](../common/runlog-harvest-contract.md) — harvest-side cross-vendor invariants
- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — Step 4 hand-off target
- [`./runlog-author.md`](./runlog-author.md) — mid-flow companion (Windsurf adapter)
- [`./SKILL.md`](./SKILL.md) — read-side Windsurf adapter

---

Adapter version tracks the runlog-skills repo tag.
