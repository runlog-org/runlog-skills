---
name: runlog-author
description: Author and submit Runlog entries from a real Cline debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Cline-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (Cline adapter)

This is the Cline wrapper of the canonical `runlog-author` skill. The four-step author flow (Classify+Search → Draft → Local verify loop → Sign+Submit), the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds Cline-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. Cline adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Cline specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | Plain-language request in chat (e.g. "publish that to runlog"), or the heuristic prompt fires after a successful external-dependency fix in Act mode. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Cline's `execute_command` tool. Each verifier run is a single command requiring user approval (or auto-approval if the user has whitelisted `runlog-verifier`). Cline shows the command and the JSON result inline. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Each retry is a Plan-mode → Act-mode round. The agent should keep the draft in scratch state and re-issue `execute_command` with the patched YAML; the cap is on `runlog-verifier verify` invocations, not on Plan/Act transitions. |
| **`~/.runlog/key` access** | "Read the keypair file" | Cline accesses via the terminal tool. `~/.runlog/key` should be readable by the user that runs VS Code. |
| **Draft persistence** | "Hold the draft in memory" | Write to `.runlog-author/<unit_id>.yaml` (workspace-scoped, gitignored). Cline's file-write tool persists across plan/act transitions cleanly. |
| **MCP `runlog_submit` call** | "Pass `verification_signature: <bundle>`" | Cline's MCP integration handles the call; the agent assembles the JSON arguments per the standard MCP tool-call shape. |

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/cline/SKILL.md` is the read counterpart).
2. The four-step author flow (steps may not be skipped or reordered).
3. **The local verifier as the submission gate.** Cline MUST NOT call `runlog_submit` without a verifier-signed bundle. If `execute_command` is denied or the binary is missing, the skill MUST refuse to submit.
4. The 5-round retry cap on the verification loop.
5. The hard-rejects in Step 2 (no real credentials / hostnames / PII in drafts).
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## Cline-specific pre-flight checks

Run on first invocation. All gaps surface as a single diagnostic; do not partial-draft.

```sh
command -v runlog-verifier   # verifier binary on $PATH
test -f ~/.runlog/key        # Ed25519 keypair generated
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If any check fails, Cline emits the gap and a single fix command, then stops. The user resolves and re-runs the heuristic prompt.

## Cline-specific invocation patterns

**Heuristic prompt** (after a successful external-dependency fix in Act mode):

> *"This looks like a generic third-party-system gotcha that other teams will hit. Want me to publish it to Runlog as a verified entry? I'll draft the YAML, run `runlog-verifier verify` locally to make sure it actually discriminates, fix anything the verifier rejects, and submit. ~3-5 minutes plus per-command approvals."*

**Explicit invocation** — the user types one of:

- "publish that to runlog"
- "submit this gotcha as a runlog entry"
- "/runlog-publish"

Both heuristic and explicit invocations route into the same four-step flow.

## Auto-approval suggestions

To reduce friction during the verification loop, the user MAY auto-approve `runlog-verifier` in Cline's settings. This auto-approves only the verifier binary, not arbitrary commands — the verifier reads only the draft file and writes nothing outside `~/.runlog/`, `/tmp/`, and stdout.

The `runlog_submit` MCP call is separate from `execute_command` and uses Cline's MCP auto-approve list. Adding `runlog_submit` to the auto-approve list is optional and risk-managed: a forged signature can't bypass server-side validation, but auto-approving submission means the user doesn't get a final "ship it?" prompt before the entry is published.

## Setup

This adapter assumes the read-side Cline skill is already configured (see `skills/cline/SKILL.md §Setup`). Beyond that:

1. **Install `runlog-verifier`** (one-time):

```sh
PLATFORM=linux-amd64   # or linux-arm64, darwin-amd64, darwin-arm64
BASE=https://github.com/runlog-org/runlog-verifier/releases/latest/download
curl -fLO "$BASE/runlog-verifier-$PLATFORM"
curl -fLO "$BASE/SHA256SUMS"
sha256sum --check --ignore-missing SHA256SUMS
install -m 0755 "runlog-verifier-$PLATFORM" ~/.local/bin/runlog-verifier
```

2. **Generate an Ed25519 keypair and register it**: `runlog-verifier register --email <your-email>` (generates the keypair at `~/.runlog/key` mode 0600 inside a 0700 dir, and uploads the pubkey; reads `RUNLOG_API_KEY` from env).
3. **Install this adapter as a Cline rule**:

```sh
mkdir -p .clinerules
cp skills/cline/runlog-author.md .clinerules/runlog-author.md
```

Cline loads every `.md` in `.clinerules/`; this adapter loads alongside the read-side `runlog.md`.

## Status

This adapter is functional end-to-end as of `runlog-verifier v0.1.0` (2026-04-28). Server-side bundle signature verification + the `register --email` UX + the release artifacts shipped under F24. The skill body is unchanged from when the prereqs were tracked.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/cline/SKILL.md` — read-side Cline adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
