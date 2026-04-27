---
name: runlog-author
description: Author and submit Runlog entries from a real Continue debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Continue-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (Continue.dev adapter)

This is the Continue wrapper of the canonical `runlog-author` skill. The four-step author flow, the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds Continue-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. Continue adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Continue specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | Plain-language request in chat ("publish that to runlog"), or the heuristic prompt fires after a successful external-dependency fix in agent mode. Continue's slash-command surface is per-version; explicit invocation works regardless. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Continue's terminal-tool integration (varies by version — some support agent-driven shell commands, others require the user to run them and paste output). When terminal access is unavailable the adapter MUST refuse to submit. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Continue's agent-mode session is the unit of iteration; each retry is one verifier invocation. Cap is on `runlog-verifier verify` calls, not chat turns. |
| **`~/.runlog/key` access** | "Read the keypair file" | Continue accesses via the terminal tool. Filesystem access depends on Continue's permission model in the version installed. |
| **Draft persistence** | "Hold the draft in memory" | Write to `.runlog-author/<unit_id>.yaml` (workspace-scoped, gitignored). Continue's file-write tool persists across the agent-mode session. |

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/continue/SKILL.md` is the read counterpart).
2. The four-step author flow.
3. **The local verifier as the submission gate.** Continue MUST NOT call `runlog_submit` without a verifier-signed bundle. If Continue's terminal access is unavailable in the installed version, the skill MUST refuse to submit.
4. The 5-round retry cap.
5. The hard-rejects in Step 2.
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## Continue-specific pre-flight checks

```sh
command -v runlog-verifier   # verifier binary on $PATH
test -f ~/.runlog/key        # Ed25519 keypair generated
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If terminal-tool access is unavailable in the installed Continue version, surface a single diagnostic and stop. The user can fall back to running the verifier manually and pasting the signed bundle into the chat — but the adapter MUST validate the bundle shape before calling `runlog_submit`.

## Setup

This adapter assumes the read-side Continue skill is already configured (see `skills/continue/SKILL.md §Setup`). Beyond that:

1. **Build / install `runlog-verifier`** (one-time): `cd verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/`. F24 release-artifact UX is tracked.
2. **Generate an Ed25519 keypair**: `runlog-verifier keygen --out ~/.runlog/key`.
3. **Register the public half**: `runlog-verifier register --email <addr>` (UX tracked under F24).
4. **Add this adapter as a Continue rule** in `config.yaml`:

```yaml
rules:
  - name: runlog-author
    rule: |
      <paste the body of skills/continue/runlog-author.md here>
```

Or commit `skills/continue/runlog-author.md` to the workspace and reference via Continue's context-provider / @file mechanism (per the version installed).

## End-to-end functionality is gated on F24 prerequisites

Three structural prerequisites are NOT yet built (verifier release artifact, server-side public-key registration, `runlog-verifier register --email` UX). See `skills/runlog-author/DESIGN.md §Status` for the tracker.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/continue/SKILL.md` — read-side Continue adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
