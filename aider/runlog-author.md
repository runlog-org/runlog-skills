---
name: runlog-author
description: Author and submit Runlog entries from a real Aider debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Aider-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (Aider adapter)

This is the Aider wrapper of the canonical `runlog-author` skill. The four-step author flow, the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds Aider-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. Aider adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Aider specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | User explicit only — Aider doesn't have a heuristic prompt surface like an IDE agent. The user runs `/ask publish that gotcha to runlog` or types it directly. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Aider's `/run` command runs shell commands and pipes the output back into the chat. The agent issues `/run runlog-verifier verify .runlog-author/<unit_id>.yaml`. User confirms each `/run`. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Each retry is a chat turn followed by another `/run`. Cap is on `runlog-verifier verify` invocations, not chat turns. The chat history naturally records the loop. |
| **`~/.runlog/key` access** | "Read the keypair file" | Aider reads via `/run cat ~/.runlog/key` if needed (rarely — the verifier reads the key directly). Standard filesystem permissions apply. |
| **Draft persistence** | "Hold the draft in memory" | Aider edits `.runlog-author/<unit_id>.yaml` as a normal repo file via `/code`. The draft becomes a real file the user can inspect; gitignore the directory. |

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/aider/SKILL.md`).
2. The four-step author flow.
3. **The local verifier as the submission gate.** Aider MUST NOT call `runlog_submit` without a verifier-signed bundle. If the user denies `/run` for the verifier, the skill MUST refuse to submit.
4. The 5-round retry cap.
5. The hard-rejects in Step 2.
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## Aider-specific pre-flight checks

The agent issues these via `/run` on first invocation and parses the output:

```sh
command -v runlog-verifier && \
  test -f ~/.runlog/key && \
  test -n "$RUNLOG_API_KEY" && \
  echo "OK"
```

If the chained check returns anything other than `OK`, the agent surfaces a single diagnostic and stops. The user resolves and re-invokes.

## Aider-specific invocation

Aider has no heuristic prompt surface. Invocation is always explicit:

```
> publish that gotcha to runlog
> /ask draft a runlog entry for the python_expr issue we just fixed
> /run runlog-verifier verify .runlog-author/foo.yaml
```

The agent should write the draft via `/code` (so the user can inspect and edit before verification), then propose the `/run` for the verifier. The user approves each step.

## Setup

This adapter assumes the read-side Aider skill is already configured (see `skills/aider/SKILL.md §Setup`). Beyond that:

1. **Build / install `runlog-verifier`** (one-time): `cd verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/`. F24 release-artifact UX is tracked.
2. **Generate an Ed25519 keypair**: `runlog-verifier keygen --out ~/.runlog/key`.
3. **Register the public half**: `runlog-verifier register --email <addr>` (UX tracked under F24).
4. **Append this adapter to CONVENTIONS.md** or load via `--read`:

```sh
# Pattern A
echo '' >> CONVENTIONS.md
cat skills/aider/runlog-author.md >> CONVENTIONS.md

# Pattern B
cp skills/aider/runlog-author.md .aider/runlog-author.md
# then: aider --read .aider/runlog-author.md
```

## End-to-end functionality is gated on F24 prerequisites

See `skills/runlog-author/DESIGN.md §Status` for the tracker.

## Aider-specific cautions

- Aider's `/run` requires user approval per command. The verification loop will trigger 1–N approval prompts where N ≤ 5. Users who want to streamline this can use Aider's `--yes-always` flag (caution: applies to all commands in the session, not just verifier ones).
- Aider's chat history is the manifest carrier — long sessions accumulate context. Flush `runlog_report` before `/exit` to ensure outcomes are reported.
- Aider's diff-based editing means draft YAML changes show up as repo diffs — a feature, not a bug, for review.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/aider/SKILL.md` — read-side Aider adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
