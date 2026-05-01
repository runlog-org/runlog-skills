---
name: runlog-harvest
description: End-of-session retrospective Runlog submission flow for Continue.dev. Scans the in-frame conversation and recent git commits for missed external-dependency findings, scores and dedups, surfaces a numbered picker, and routes selected drafts through the canonical runlog-author verification + signing + runlog_submit pipeline. Continue-specific orchestration around the canonical body at skills/runlog-harvest/SKILL.md.
---

## runlog-harvest (Continue.dev adapter)

This is the Continue wrapper of the canonical `runlog-harvest` skill. The four-step harvest flow (Scan -> Score+Dedup -> Pick -> Route-to-author), the four-point classification check, the score floor (>= 0.7), the comma-select picker grammar, and the MUST-NOT list are inherited verbatim from `skills/runlog-harvest/SKILL.md`. **Read that file first** — this adapter only adds Continue-specific glue.

Harvest-side cross-vendor invariants live at `skills/common/runlog-harvest-contract.md`. Continue adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Continue specifics |
|---|---|---|
| **Invocation** | "User invokes harvest explicitly" | Plain-language request in chat (`"harvest this session to runlog"`, "scan this session for runlog candidates"). If Continue's slash-command surface is enabled in the installed version, `/harvest` also routes here; availability is per-version, so the verbal form is the published literal. |
| **Local Bash dispatch** | "Run `git log` and the verifier via Bash" | Continue's terminal-tool integration (varies by version — some support agent-driven shell commands, others require the user to run them and paste output). Recent-commits scan is `git log --oneline -10` via the terminal tool. When terminal access is unavailable the adapter MUST refuse to invoke Step 4 (route-to-runlog-author), since the verifier loop cannot run. |
| **Agent-loop iteration** | "Sequential per-candidate route to runlog-author" | Continue's agent-mode session is the unit of iteration. Each picked candidate is its own complete pass through runlog-author Step 2 -> 3 -> 4; the 5-round verifier retry cap (inherited from runlog-author) applies per-candidate. |
| **Session-context discovery** | "In-frame fallback; per-host transcript optional" | Continue exposes no stable on-disk transcript path the adapter can rely on across versions, so harvest falls back to in-frame conversation context (per harvest contract OQ #3). The fallback is normative and works on every Continue install. |
| **Picker rendering** | "Numbered list, comma-select grammar" | Continue's chat panel renders the numbered list inline. User replies follow the comma-select grammar from the canonical body (`<n>(',' <n>)* | 'skip' <n> | 'all' | 'none'`). Per-item edit-before-submit is offered as a follow-up turn after the user picks — Continue's chat affordances are turn-based, not inline. |
| **Draft persistence** | "Vendor scratch dir" | Write per-candidate drafts to `.runlog-harvest/<unit_id>.yaml` in the workspace (gitignored). Distinct from runlog-author's `.runlog-author/` so the two skills do not clobber each other's scratch state. Cleaned up on successful submit. |

```text
# add to your project's .gitignore:
.runlog-harvest/
```

## What this adapter MUST NOT change

Per `skills/common/runlog-harvest-contract.md`:

1. The four-point client contract (`skills/common/four-point-client-contract.md`) — the four-point check on each candidate.
2. The four-step harvest flow (steps may not be skipped or reordered).
3. The score floor (>= 0.7). The adapter MAY raise it; MUST NOT lower it.
4. The comma-select picker grammar.
5. Per-item edit-before-submit availability.
6. **Routing through runlog-author for verification + submission.** Continue MUST NOT call `runlog_submit` directly from harvest. Selected candidates enter `skills/runlog-author/SKILL.md` at Step 2; the verifier loop and signed bundle are produced there. If Continue's terminal access is unavailable in the installed version, the skill MUST refuse to invoke Step 4.
7. The MUST NOT list in `skills/runlog-harvest/SKILL.md`.

## Continue-specific pre-flight checks

Run on first invocation per session. All gaps surface as a single human-readable diagnostic; do not partial-scan or partial-draft.

```sh
command -v runlog-verifier   # verifier binary on $PATH (inherited from runlog-author)
test -f ~/.runlog/key        # Ed25519 keypair generated and registered
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If terminal-tool access is unavailable in the installed Continue version, surface a single diagnostic and stop before scanning candidates — without the terminal tool, the verifier loop in Step 4 cannot run, so drafting is pointless. The user can fall back to running the canonical runlog-author flow manually after the picker.

If the workspace has no git history (`.git` absent), harvest still runs against the in-frame conversation alone — the git source is a backup, not a hard dependency.

## Continue-specific invocation patterns

The plain-language form is the published invocation literal:

- `"harvest this session to runlog"` — the canonical verbal form. Documented and stable across Continue versions.

Other natural phrasings route into the same flow:

- "scan this session for runlog candidates"
- "any external-dep findings worth publishing?"

If the installed Continue version exposes slash commands, `/harvest` also routes here. Continue's slash-command surface is too version-fragmented to commit to a single literal; the verbal form above is the one users should reach for.

## Setup

This adapter assumes the read-side Continue skill (`skills/continue/SKILL.md`) and the Continue runlog-author adapter (`skills/continue/runlog-author.md`) are already configured. Harvest adds no new prerequisites beyond those — the verifier binary, the keypair, and `RUNLOG_API_KEY` are inherited from runlog-author.

Add this adapter as a Continue rule in `config.yaml`:

```yaml
rules:
  - name: runlog-harvest
    rule: |
      <paste the body of skills/continue/runlog-harvest.md here>
```

Or commit `skills/continue/runlog-harvest.md` to the workspace and reference via Continue's context-provider / @file mechanism (per the version installed).

## Status

Adapter shipped 2026-05-01 alongside the canonical harvest body (M01-S03 wave 2). End-to-end functionality depends on the same F24 prerequisites runlog-author depends on (verifier release artifact, public-key registration flow, `runlog-verifier register --email` UX) — all shipped under F24 (2026-04-28).

## Further Reading

- `skills/runlog-harvest/SKILL.md` — canonical harvest body (READ FIRST)
- `skills/runlog-harvest/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-harvest-contract.md` — harvest-side cross-vendor invariants
- `skills/runlog-author/SKILL.md` — Step 4 hand-off target
- `skills/continue/runlog-author.md` — mid-flow companion (Continue adapter)
- `skills/continue/SKILL.md` — read-side Continue adapter

---

Adapter version tracks the runlog-skills repo tag.
