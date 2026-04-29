---
name: runlog-author
description: Author and submit Runlog entries from a real JetBrains AI Assistant debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. JetBrains-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (JetBrains AI Assistant adapter)

This is the JetBrains wrapper of the canonical `runlog-author` skill. The four-step author flow, the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds JetBrains-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. JetBrains adapters MAY vary orchestration glue but MUST NOT vary the contract.

> **VERIFY against current JetBrains AI Assistant docs** before publishing. The plugin's tool-use, terminal access, and file-edit capabilities vary across IDE products and plugin versions.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | JetBrains specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | Plain-language request in AI Assistant chat ("publish that to runlog"), or the heuristic prompt fires after a successful external-dependency fix in Junie agent mode. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Junie's terminal-tool integration (when supported in the installed plugin version). User approves each command unless an allow-list is configured. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Each retry is one Junie agent-mode turn. Cap is on `runlog-verifier verify` invocations. |
| **`~/.runlog/key` access** | "Read the keypair file" | Read via the terminal tool; standard filesystem permissions. |
| **Draft persistence** | "Hold the draft in memory" | Junie can edit files directly via JetBrains' refactoring-aware edit surface; write the draft to `.runlog-author/<unit_id>.yaml` (gitignored). The user can inspect the draft in the editor before approving the verifier call. |

```
# add to your project's .gitignore:
.runlog-author/
```

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/jetbrains/SKILL.md`).
2. The four-step author flow.
3. **The local verifier as the submission gate.** AI Assistant MUST NOT call `runlog_submit` without a verifier-signed bundle. If terminal access is unavailable in the installed plugin version, the skill MUST refuse to submit.
4. The 5-round retry cap.
5. The hard-rejects in Step 2.
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## JetBrains-specific pre-flight checks

```sh
command -v runlog-verifier
test -f ~/.runlog/key
[ -n "$RUNLOG_API_KEY" ]
```

If terminal-tool access is not available in the installed AI Assistant version, surface a single diagnostic and stop. The user can fall back to running the verifier manually outside the IDE and pasting the signed bundle into the chat — but the adapter MUST validate the bundle shape before calling `runlog_submit`.

## Setup

This adapter assumes the read-side JetBrains skill is already configured (see `skills/jetbrains/SKILL.md §Setup`). Beyond that:

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
3. **Add this adapter to the project's AI guidelines** (or as a custom prompt) — same surface as the read skill (Settings → Tools → AI Assistant → Guidelines, or the project-scoped guidelines file).

## Status

This adapter is functional end-to-end as of `runlog-verifier v0.1.0` (2026-04-28). Server-side bundle signature verification + the `register --email` UX + the release artifacts shipped under F24. The skill body is unchanged from when the prereqs were tracked.

## JetBrains-specific cautions

- AI Assistant's classic chat mode may not support tool use; Junie (the agent mode) is the surface that dispatches MCP tool calls and terminal commands. Confirm you're in the right mode.
- JetBrains AI's tool-use guarantees vary across IDE products and plugin versions. If the verification loop can't run end-to-end on your installed version (e.g. no terminal tool), the skill MUST hand back to the user rather than partial-submit.
- The IDE's environment variables are inherited from the launching shell on Linux/macOS. On Windows or when launching from a desktop launcher, set `RUNLOG_API_KEY` via the IDE's environment-variable settings.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/jetbrains/SKILL.md` — read-side JetBrains adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
