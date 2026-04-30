---
name: runlog-author
description: Author and submit Runlog entries from a real VS Code Copilot debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Copilot-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (VS Code Copilot adapter)

This is the Copilot wrapper of the canonical `runlog-author` skill. The four-step author flow, the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds Copilot-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. Copilot adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | VS Code Copilot specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | Plain-language request in Copilot Chat agent mode ("publish that to runlog"), or the heuristic prompt fires after a successful external-dependency fix. The `@runlog` participant scope can be invoked explicitly. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Copilot agent mode's terminal-tool integration. Each verifier invocation requires user approval (or auto-approval if the user has whitelisted `runlog-verifier` in the trust settings). |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Each retry is one agent-mode turn that runs the verifier and proposes a fix. Cap is on `runlog-verifier verify` invocations. |
| **`~/.runlog/key` access** | "Read the keypair file" | Read via the terminal tool; standard filesystem permissions. |
| **Draft persistence** | "Hold the draft in memory" | Copilot agent mode can edit files directly; write the draft to `.runlog-author/<unit_id>.yaml` (gitignored). The user can inspect the draft in the editor before approving the verifier call. |

```text
# add to your project's .gitignore:
.runlog-author/
```

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/copilot/SKILL.md`).
2. The four-step author flow.
3. **The local verifier as the submission gate.** Copilot MUST NOT call `runlog_submit` without a verifier-signed bundle. If terminal access is denied the skill MUST refuse to submit.
4. The 5-round retry cap.
5. The hard-rejects in Step 2.
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## Copilot-specific pre-flight checks

```sh
command -v runlog-verifier
test -f ~/.runlog/key
[ -n "$RUNLOG_API_KEY" ] || test -f .vscode/mcp-secrets.json
```

The last check accounts for VS Code's secret-store flow — when the API key was entered via the `${input:runlog-api-key}` prompt, it's not in the shell env but in VS Code's per-user secret store. The MCP server still receives it correctly via the `Authorization` header.

## Setup

This adapter assumes the read-side Copilot skill is already configured (see `skills/copilot/SKILL.md §Setup`). Beyond that:

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
3. **Install this adapter as a Copilot instruction**:

```sh
# Pattern A — append to .github/copilot-instructions.md
echo '' >> .github/copilot-instructions.md
cat skills/copilot/runlog-author.md >> .github/copilot-instructions.md

# Pattern B — separate scoped instruction
mkdir -p .github/instructions
cp skills/copilot/runlog-author.md .github/instructions/runlog-author.instructions.md
```

## Status

This adapter is functional end-to-end as of `runlog-verifier v0.1.0` (2026-04-28). Server-side bundle signature verification + the `register --email` UX + the release artifacts shipped under F24. The skill body is unchanged from when the prereqs were tracked.

## Copilot-specific cautions

- Copilot Chat's ask/edit modes don't dispatch MCP tool calls or terminal commands — the verification loop only works in agent mode.
- Copilot's terminal-tool requires the user to approve commands by default. Trust settings can whitelist `runlog-verifier` to reduce friction — auto-approving the local verifier binary is fine, since it's a deterministic, local, signed action that writes nothing outside `~/.runlog/`, `/tmp/`, and stdout. Auto-approving the `runlog_submit` MCP call is **NOT recommended**: submission is the final review gate, and a prompt-injected context could otherwise publish without your review.
- VS Code's secret store is per-user — when committing `.vscode/mcp.json` with `${input:...}` prompts, each team member enters their own API key on first use.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/copilot/SKILL.md` — read-side VS Code Copilot adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
