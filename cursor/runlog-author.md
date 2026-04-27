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
cd $(git rev-parse --show-toplevel) && cd verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/
```

If `~/.runlog/key` is missing:

```sh
runlog-verifier keygen --out ~/.runlog/key && chmod 600 ~/.runlog/key
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

1. **Build / install `runlog-verifier`** (one-time): `cd verifier && make build && install -m 0755 bin/runlog-verifier ~/.local/bin/`. Release-artifact UX is a tracked F24 prerequisite.
2. **Generate an Ed25519 keypair**: `runlog-verifier keygen --out ~/.runlog/key`.
3. **Register the public half against your account**: `runlog-verifier register --email <addr>` (UX is a tracked F24 prerequisite; today the public key is registered manually against the API key's account row).
4. **Install this adapter as a Cursor rule**:

```sh
# Project-scoped (recommended for repos with shared author conventions)
mkdir -p .cursor/rules
cp skills/cursor/runlog-author.md .cursor/rules/runlog-author.mdc

# Global
mkdir -p ~/.cursor/rules
cp skills/cursor/runlog-author.md ~/.cursor/rules/runlog-author.mdc
```

The adapter loads alongside the read-side `runlog.mdc`. Both rules together implement the four-point contract end-to-end.

## End-to-end functionality is gated on F24 prerequisites

Three structural prerequisites are NOT yet built. Until they ship:

- **Verifier release artifact** missing → users build from source via `make build`. Manageable for engineers; blocker for casual contributors.
- **Server-side public-key registration** missing → the bundle's signature is currently trusted blindly by the server. Cryptographic handshake is one-sided in prod. The skill works as designed; the server-side trust improves when the registration flow ships.
- **`runlog-verifier register --email` UX** missing → users register the pubkey manually.

The skill body itself is unaffected when prerequisites ship; only the Setup section gets simpler.

## Further Reading

- `skills/runlog-author/SKILL.md` — canonical author body (READ FIRST)
- `skills/runlog-author/DESIGN.md` — design rationale and open questions
- `skills/common/runlog-author-contract.md` — author-side cross-vendor invariants
- `skills/cursor/SKILL.md` — read-side Cursor adapter

---

Adapter version tracks the runlog-skills repo tag. Cross-vendor expansion under `[F25]`.
