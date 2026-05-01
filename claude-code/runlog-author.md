---
name: runlog-author
description: Author and submit Runlog entries from a real Claude Code debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Claude-Code-specific orchestration around the canonical body at runlog-author/SKILL.md.
---

## runlog-author (Claude Code adapter)

This is the Claude Code wrapper of the canonical `runlog-author` skill. The four-step author flow (Classify+Search → Draft → Local verify loop → Sign+Submit), the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md). **Read that file first** — this adapter only adds Claude-Code-specific glue.

Author-side cross-vendor invariants live at [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md). Claude Code adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Claude Code specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | `/runlog:publish` slash command, surfaced via the plugin's `commands/publish.md`. Plain-language requests ("publish that to runlog", "submit this finding") also route into the same flow. The heuristic prompt may fire after a successful external-dependency fix; user always confirms before drafting. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Claude Code's Bash tool. The agent must have Bash access; if blocked, surface a single diagnostic asking the user to grant Bash use for this session. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Claude Code's agent stays in the verification loop across turns; each retry is a new tool turn, the cap applies to the count of `runlog-verifier verify` invocations on the same draft. |
| **`~/.runlog/key` access** | "Read the keypair file" | Claude Code reads via the Bash tool (no special secret-store integration today). Filesystem access prompt may fire on first run. |
| **Draft persistence** | "Hold the draft in memory" | Write the draft to `.runlog-author/<unit_id>.yaml` in the workspace (a gitignored scratch dir Claude Code's agent owns). Survives across turns; cleaned up on successful submit. Distinct from `.runlog-harvest/` so the two skills do not clobber each other's scratch state. |

```text
# add to your project's .gitignore:
.runlog-author/
```

## What this adapter MUST NOT change

Per [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md):

1. The four-point client contract (read-side `claude-code/SKILL.md` is the read counterpart).
2. The four-step author flow (steps may not be skipped or reordered).
3. **The local verifier as the submission gate.** Claude Code MUST NOT call `runlog_submit` without a verifier-signed bundle. If Bash access is blocked or the verifier binary is missing, the skill MUST refuse to submit.
4. The 5-round retry cap on the verification loop.
5. The hard-rejects in Step 2 (no real credentials / hostnames / PII in drafts).
6. The MUST NOT list in [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md).

## Claude-Code-specific pre-flight checks

Run on first invocation. All gaps surface as a single diagnostic; do not partial-draft.

| Check | Failure surface |
|---|---|
| `runlog-verifier` on `$PATH` | "runlog-verifier not found — install via the runlog-installer (`runlog register --email <addr>`) or `curl -fLO https://github.com/runlog-org/runlog-verifier/releases/latest/download/runlog-verifier-<platform>`" |
| `~/.runlog/key` exists | "Ed25519 keypair not registered — run `runlog-verifier register --email <addr>` to generate and upload" |
| `RUNLOG_API_KEY` set | "RUNLOG_API_KEY not set — get a key at https://runlog.org/register, then `export RUNLOG_API_KEY=sk-runlog-<your-key>`" |
| Workspace is a git repo OR has writable cwd | "Cannot write `.runlog-author/<unit_id>.yaml` — workspace cwd is not writable" |

## Setup

The Claude Code plugin (`/plugin install runlog`) places this adapter under `~/.claude/skills/runlog-author/SKILL.md` and registers `/runlog:publish` automatically. Manual install:

```sh
cp claude-code/runlog-author.md ~/.claude/skills/runlog-author/SKILL.md
```

Companion: [`runlog-harvest.md`](./runlog-harvest.md) for end-of-session retrospective capture across multiple findings.

## Further reading

- [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md) — canonical author body (read first).
- [`../runlog-author/DESIGN.md`](../runlog-author/DESIGN.md) — design rationale.
- [`../common/runlog-author-contract.md`](../common/runlog-author-contract.md) — cross-vendor invariants.
- [`../common/four-point-client-contract.md`](../common/four-point-client-contract.md) — read-side base contract.
- [`./runlog-harvest.md`](./runlog-harvest.md) — end-of-session retrospective companion.
