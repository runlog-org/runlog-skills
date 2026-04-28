---
name: runlog-author
description: Author and submit Runlog entries from a real Windsurf debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Windsurf-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (Windsurf adapter)

This is the Windsurf wrapper of the canonical `runlog-author` skill. The four-step author flow, the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds Windsurf-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. Windsurf adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Windsurf specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | Plain-language request in Cascade ("publish that to runlog"), or the heuristic prompt fires after a successful external-dependency fix in Write mode. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Cascade's terminal tool. Each verifier invocation is a single command; user approval per command unless allow-listed in Windsurf's terminal-tool settings. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Each retry is a Cascade turn. Cap is on `runlog-verifier verify` invocations. |
| **`~/.runlog/key` access** | "Read the keypair file" | Cascade reads via the terminal tool. Standard filesystem permissions apply. |
| **Draft persistence** | "Hold the draft in memory" | Write to `.runlog-author/<unit_id>.yaml` (workspace-scoped, gitignored). Cascade's file-write tool persists across turns. Or use a Windsurf memory to carry the draft state if the workspace is read-only. |

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/windsurf/SKILL.md`).
2. The four-step author flow.
3. **The local verifier as the submission gate.** Cascade MUST NOT call `runlog_submit` without a verifier-signed bundle. If terminal access is blocked the skill MUST refuse to submit.
4. The 5-round retry cap.
5. The hard-rejects in Step 2.
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## Windsurf-specific pre-flight checks

```sh
command -v runlog-verifier
test -f ~/.runlog/key
[ -n "$RUNLOG_API_KEY" ]
```

If terminal access is denied (Windsurf supports per-workspace approval), surface a single diagnostic and stop.

## Setup

1. **Build / install `runlog-verifier`** (one-time): `git clone https://github.com/runlog-org/runlog-verifier && cd runlog-verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/`. F24 release-artifact UX is tracked.
2. **Generate an Ed25519 keypair**: `runlog-verifier keygen --out ~/.runlog/key`.
3. **Register the public half**: `runlog-verifier register --email <addr>` (UX tracked under F24).
4. **Append this adapter to `.windsurfrules`** (or paste into Windsurf's global rules):

```sh
echo '' >> .windsurfrules
cat skills/windsurf/runlog-author.md >> .windsurfrules
```

Or keep it as a separate workspace doc and reference it from `.windsurfrules` with a one-line pointer.

## End-to-end functionality is gated on F24 prerequisites

See `skills/runlog-author/DESIGN.md §Status` for the full tracker.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/windsurf/SKILL.md` — read-side Windsurf adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
