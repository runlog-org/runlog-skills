# Runlog Skills — MCP Client Skills

**Repo:** [`runlog-org/runlog-skills`](https://github.com/runlog-org/runlog-skills) — public, MIT
**Content:** Agent skill files and MCP client configs
**Implements:** [`runlog-docs/07-mcp-interface.md`](https://github.com/runlog-org/runlog-docs/blob/main/07-mcp-interface.md), plus the manifest conventions from [`runlog-docs/03-verification-and-provenance.md`](https://github.com/runlog-org/runlog-docs/blob/main/03-verification-and-provenance.md) §6

Drop-in skill files so agents running Claude Code, Cursor, Cline, Continue, Windsurf, Aider, VS Code Copilot, JetBrains AI Assistant, and Zed can use Runlog without writing their own MCP plumbing. Each skill wraps `runlog_search`, `runlog_submit`, and `runlog_report` with the right framework-specific glue.

Also standardises how each agent framework tracks `kb:<id>` entries in its working session so the server's failure-attribution engine gets clean dependency manifests.

## What's shipped today

All 9 vendor adapters (Claude Code + 8 cross-vendor expansion) are operational on the read side against the live MCP server. The write side ships per-vendor too; end-to-end functionality is gated on three F24 prerequisites — see [`runlog-author/DESIGN.md`](./runlog-author/DESIGN.md) §Status.

| Vendor | Read | Write | Read-side install | Notes |
|---|---|---|---|---|
| **Claude Code** | ✅ | ✅ | [`claude-code/SKILL.md`](./claude-code/SKILL.md) | Reference adapter |
| **Cursor** | ✅ | ✅ | [`cursor/SKILL.md`](./cursor/SKILL.md) → `.cursor/rules/runlog.mdc` | Highest priority after Claude Code |
| **Cline** | ✅ | ✅ | [`cline/SKILL.md`](./cline/SKILL.md) → `.clinerules/runlog.md` | Open-source, MCP-native |
| **Continue.dev** | ✅ | ✅ | [`continue/SKILL.md`](./continue/SKILL.md) → `.continue/config.yaml` rules block | Open-source, MCP-native |
| **Windsurf** | ✅ | ✅ | [`windsurf/SKILL.md`](./windsurf/SKILL.md) → `.windsurfrules` | Codeium-based |
| **Aider** | ✅ * | ✅ * | [`aider/SKILL.md`](./aider/SKILL.md) → `CONVENTIONS.md` or `--read` | * MCP support is version-dependent |
| **VS Code + GitHub Copilot** | ✅ | ✅ | [`copilot/SKILL.md`](./copilot/SKILL.md) → `.github/copilot-instructions.md` | Requires Copilot agent mode |
| **JetBrains AI Assistant** | ✅ * | ✅ * | [`jetbrains/SKILL.md`](./jetbrains/SKILL.md) → AI guidelines | * Tool-use varies by IDE / plugin version |
| **Zed** | ✅ * | ✅ * | [`zed/SKILL.md`](./zed/SKILL.md) → `.rules` | * HTTP `context_servers` schema is evolving |

Asterisks (`*`) flag adapters whose MCP integration is evolving in the upstream vendor — the adapter is shipped and works against today's vendor capabilities, but check the per-vendor README's "VERIFY" notes against current vendor docs before publishing your config.

## Cross-vendor expansion strategy — `[F25]`

The defensive moat for Runlog is being the cross-vendor knowledge layer that no single agent platform owns. As LLM vendors ship their own "skills" / "memory" / "knowledge" features, multi-vendor reach is what keeps Runlog relevant rather than getting absorbed into a single ecosystem.

Each vendor gets two adapters:

- **Read-side** — port [`claude-code/SKILL.md`](./claude-code/SKILL.md) with vendor-specific MCP config, the team-memory surface to check first (`.cursorrules`, `.clinerules`, `.windsurfrules`, `.github/copilot-instructions.md`, etc.), and how the dependency manifest is persisted across the agent's tool-use turns.
- **Write-side** — wrap [`runlog-author/SKILL.md`](./runlog-author/SKILL.md). The canonical author body is inherited byte-for-byte; the adapter swaps orchestration glue (vendor's tool-use API, agent-loop iteration, command palette / slash-command invocation, how local Bash is dispatched).

The `common/` extraction means each vendor adapter references cross-vendor invariants instead of re-authoring them — when the contract changes, one file moves, not nine.

## Layout

```
skills/
├── claude-code/                            # ✅ Reference adapter (read side)
│   └── SKILL.md
├── runlog-author/                          # ✅ Canonical author body (vendor-agnostic)
│   ├── SKILL.md
│   └── DESIGN.md                           #     design rationale + open questions
├── common/                                 # ✅ Cross-vendor invariants
│   ├── README.md
│   ├── four-point-client-contract.md       # ✅ shipped
│   ├── runlog-author-contract.md           # ✅ shipped
│   ├── dependency-manifest.md              # ⏳ planned — extracted when 2nd consumer ships
│   └── reporting-conventions.md            # ⏳ planned — extracted when 2nd consumer ships
├── cursor/                                 # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
├── cline/                                  # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
├── continue/                               # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
├── windsurf/                               # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
├── aider/                                  # ✅ shipped (caveats)
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
├── copilot/                                # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
├── jetbrains/                              # ✅ shipped (caveats)
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
├── zed/                                    # ✅ shipped (caveats)
│   ├── README.md
│   ├── SKILL.md
│   └── runlog-author.md
└── README.md                               # this file
```

## Invariants every adapter MUST honour

- The four rules in [`common/four-point-client-contract.md`](./common/four-point-client-contract.md) — both read and write skills inherit.
- The author-side rules in [`common/runlog-author-contract.md`](./common/runlog-author-contract.md) — adds the submission-flow constraints.

The contract is framework-agnostic; per-vendor adapters swap orchestration glue, not the rules.

## Maintenance pattern

When the cross-vendor contract changes (e.g. a new MUST-NOT rule or a tool-call shape update), the change pattern is:

1. Update `common/four-point-client-contract.md` and/or `common/runlog-author-contract.md` (single source of truth).
2. Re-sync each per-vendor SKILL.md / runlog-author.md by re-reading the canonical body and bringing the vendor wrapper in line.
3. The bodies are deliberately ~80% similar across vendors — the vendor-specific glue is concentrated in the **Setup** sections and a few notes paragraphs.

Future tooling (a generator script that produces vendor adapters from the canonical body + a vendor-glue spec) is a maintenance-pain follow-up; not yet needed at 9 vendors.

## Depends on

- [`runlog-org/runlog-schema`](https://github.com/runlog-org/runlog-schema) — referenced in documentation only (not as a code dep)
- [`runlog-org/runlog-verifier`](https://github.com/runlog-org/runlog-verifier) — the `runlog-author` skill drives the local verifier binary; without it the write side cannot submit. Build with `git clone … && make build` in the verifier repo.
