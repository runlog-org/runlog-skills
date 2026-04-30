---
name: runlog-author
description: Author and submit Runlog entries from a real Cursor debugging session. Drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit. Cursor-specific orchestration around the canonical body at skills/runlog-author/SKILL.md.
---

## runlog-author (Cursor adapter)

This is the Cursor wrapper of the canonical `runlog-author` skill. The four-step author flow (Classify+Search → Draft → Local verify loop → Sign+Submit), the typed-reason → fix-strategy table, the 5-round retry cap, and the MUST-NOT list are inherited verbatim from `skills/runlog-author/SKILL.md`. **Read that file first** — this adapter only adds Cursor-specific glue.

Author-side cross-vendor invariants live at `skills/common/runlog-author-contract.md`. Cursor adapters MAY vary orchestration glue but MUST NOT vary the contract.

## What this adapter changes (orchestration glue only)

| Concern | Canonical body | Cursor specifics |
|---|---|---|
| **Invocation** | "User says 'publish'" | Slash-command via Cursor's command palette (`@runlog publish`) or explicit user request in the agent panel. Cursor's agent mode surfaces the proposal inline; the Composer mode does the same in chat. |
| **Local Bash dispatch** | "Run `runlog-verifier verify <draft>.yaml`" | Cursor's terminal-tool grant. The agent must have terminal access; if blocked, surface a single diagnostic asking the user to grant terminal use for this session. |
| **Agent-loop iteration** | "Cap at 5 retry rounds" | Cursor's agent stays in the verification loop across turns; each retry is a new tool turn, the cap applies to the count of `runlog-verifier verify` invocations on the same draft. |
| **`~/.runlog/key` access** | "Read the keypair file" | Cursor reads via the terminal tool (no special secret store integration today). Filesystem access prompt may fire on first run. |
| **Draft persistence** | "Hold the draft in memory" | Write the draft to `.runlog-author/<unit_id>.yaml` in the workspace (a gitignored scratch dir Cursor's agent owns). Survives across turns; cleaned up on successful submit. |

```text
# add to your project's .gitignore:
.runlog-author/
```

## What this adapter MUST NOT change

Per `skills/common/runlog-author-contract.md`:

1. The four-point client contract (read-side `skills/cursor/SKILL.md` is the read counterpart).
2. The four-step author flow (steps may not be skipped or reordered).
3. **The local verifier as the submission gate.** Cursor MUST NOT call `runlog_submit` without a verifier-signed bundle. If terminal access is blocked or the verifier binary is missing, the skill MUST refuse to submit.
4. The 5-round retry cap on the verification loop.
5. The hard-rejects in Step 2 (no real credentials / hostnames / PII in drafts).
6. The MUST NOT list in `skills/runlog-author/SKILL.md`.

## Cursor-specific pre-flight checks

Run on first invocation. All gaps surface as a single diagnostic; do not partial-draft.

```sh
command -v runlog-verifier   # verifier binary on $PATH
test -f ~/.runlog/key        # Ed25519 keypair generated and registered
[ -n "$RUNLOG_API_KEY" ]     # API key in environment
```

If `runlog-verifier` is missing, instruct the user:

```sh
PLATFORM=linux-amd64   # or linux-arm64, darwin-amd64, darwin-arm64
BASE=https://github.com/runlog-org/runlog-verifier/releases/latest/download
curl -fLO "$BASE/runlog-verifier-$PLATFORM"
curl -fLO "$BASE/SHA256SUMS"
grep "runlog-verifier-$PLATFORM" SHA256SUMS | sha256sum --check -
install -m 0755 "runlog-verifier-$PLATFORM" ~/.local/bin/runlog-verifier
```

If `~/.runlog/key` is missing:

```sh
runlog-verifier register --email <your-email>
```

If `$RUNLOG_API_KEY` is unset, instruct the user to set it in the shell that launched Cursor (Cursor inherits the parent shell's env; settings need to be made before launch or via Cursor's own env-var settings).

## Cursor-specific invocation patterns

**Heuristic prompt** (after a successful external-dependency fix):

> *"This looks like a generic third-party-system gotcha that other teams will hit. Want me to publish it to Runlog as a verified entry? I'll draft the YAML, run the local verifier to make sure it actually discriminates, fix anything the verifier rejects, and submit. ~3-5 minutes."*

**Explicit invocation** — the user types one of:

- `@runlog publish` in Cursor's chat
- `/runlog-publish` via command palette
- "publish that to runlog" in plain language

Both heuristic and explicit invocations route into the same four-step flow.

## Setup

This adapter assumes the read-side Cursor skill is already configured (see `skills/cursor/SKILL.md §Setup`). Beyond that:

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
3. **Install this adapter as a Cursor rule**:

```sh
# Project-scoped (recommended for repos with shared author conventions)
mkdir -p .cursor/rules
cp skills/cursor/runlog-author.md .cursor/rules/runlog-author.mdc

# Global
mkdir -p ~/.cursor/rules
cp skills/cursor/runlog-author.md ~/.cursor/rules/runlog-author.mdc
```

The adapter loads alongside the read-side `runlog.mdc`. Both rules together implement the four-point contract end-to-end.

## Status

This adapter is functional end-to-end as of `runlog-verifier v0.1.0` (2026-04-28). Server-side bundle signature verification + the `register --email` UX + the release artifacts shipped under F24. The skill body is unchanged from when the prereqs were tracked.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/cursor/SKILL.md` — read-side Cursor adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
