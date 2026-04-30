---
name: runlog-author
description: Author and submit Runlog entries from a real Zed Assistant debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Zed-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (Zed adapter)

This is the Zed wrapper of the canonical `runlog-author` skill. The four-step author flow, the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds Zed-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. Zed adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Zed specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | Plain-language request in Zed Assistant chat ("publish that to runlog"), or the heuristic prompt fires after a successful external-dependency fix. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Zed Assistant's terminal-tool integration. Each verifier invocation requires user approval unless allow-listed. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Each retry is one chat turn. Cap is on `runlog-verifier verify` invocations. |
| **`~/.runlog/key` access** | "Read the keypair file" | Read via the terminal tool; standard filesystem permissions. |
| **Draft persistence** | "Hold the draft in memory" | Zed Assistant can edit files directly; write the draft to `.runlog-author/<unit_id>.yaml` (gitignored). The user can inspect the draft in a Zed buffer before approving the verifier call. |

```text
# add to your project's .gitignore:
.runlog-author/
```

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/zed/SKILL.md`).
2. The four-step author flow.
3. **The local verifier as the submission gate.** Zed Assistant MUST NOT call `runlog_submit` without a verifier-signed bundle. If terminal access is denied the skill MUST refuse to submit.
4. The 5-round retry cap.
5. The hard-rejects in Step 2.
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## Zed-specific pre-flight checks

```sh
command -v runlog-verifier
test -f ~/.runlog/key
[ -n "$RUNLOG_API_KEY" ]
```

If any check fails, Zed Assistant emits the gap and a single fix command, then stops.

## Setup

This adapter assumes the read-side Zed skill is already configured (see `skills/zed/SKILL.md §Setup`). Beyond that:

1. **Install `runlog-verifier`** (one-time):

```sh
PLATFORM=linux-amd64   # or linux-arm64, darwin-amd64, darwin-arm64
BASE=https://github.com/runlog-org/runlog-verifier/releases/latest/download
curl -fLO "$BASE/runlog-verifier-$PLATFORM"
curl -fLO "$BASE/SHA256SUMS"
grep "runlog-verifier-$PLATFORM" SHA256SUMS | sha256sum --check -
install -m 0755 "runlog-verifier-$PLATFORM" ~/.local/bin/runlog-verifier
```

2. **Generate an Ed25519 keypair and register it**: `runlog-verifier register --email <your-email>` (generates the keypair at `~/.runlog/key` mode 0600 inside a 0700 dir, and uploads the pubkey; reads `RUNLOG_API_KEY` from env).
3. **Append this adapter to Zed rules**:

```sh
# Project-scoped
cat skills/zed/runlog-author.md >> .rules

# Or global
cat skills/zed/runlog-author.md >> ~/.config/zed/rules.md
```

## Status

This adapter is functional end-to-end as of `runlog-verifier v0.1.0` (2026-04-28). Server-side bundle signature verification + the `register --email` UX + the release artifacts shipped under F24. The skill body is unchanged from when the prereqs were tracked.

## Zed-specific cautions

- Zed Assistant's tool-use surface depends on the agent mode being enabled and the model supporting tool calls. Some configurations (smaller local models, completion-only mode) won't support the verification loop.
- For the stdio-bridge MCP setup: the local proxy runs as a child process of Zed; it inherits Zed's environment. Make sure `RUNLOG_API_KEY` is set in the shell that launched Zed.
- Allow-listing the local `runlog-verifier` binary is fine (deterministic, local, signed). Allow-listing or auto-approving the `runlog_submit` MCP call is **NOT recommended** — submission is the final review gate, and a prompt-injected context could otherwise publish without your review.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/zed/SKILL.md` — read-side Zed adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
