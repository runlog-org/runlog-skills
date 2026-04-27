# skills/ — MCP Client Skills

**Future repo:** `runlog-skills` — public, MIT (planned)
**Content:** Agent skill files and MCP client configs
**Implements:** [`../docs/07-mcp-interface.md`](../docs/07-mcp-interface.md), plus the manifest conventions from [`../docs/03-verification-and-provenance.md`](../docs/03-verification-and-provenance.md) §6

Drop-in skill files so agents running Claude Code, Cursor, Cline, and other MCP clients can use Runlog without writing their own MCP plumbing. Each skill wraps `runlog_search`, `runlog_submit`, and `runlog_report` with the right framework-specific glue.

Also standardises how each agent framework tracks `kb:<id>` entries in its working session so the server's failure-attribution engine gets clean dependency manifests.

## What's real today

| Skill | Vendor | Side | File |
|---|---|---|---|
| `runlog` | Claude Code | read | [`claude-code/SKILL.md`](./claude-code/SKILL.md) |
| `runlog-author` | (vendor-agnostic body) | write | [`runlog-author/SKILL.md`](./runlog-author/SKILL.md) |

The read-side skill is shipped and operational against the live MCP server. The write-side skill (canonical body) is shipped; the structural prerequisites it relies on (verifier release artifact, server-side public-key registration, `runlog-verifier register --email` UX) are tracked separately — see [`runlog-author/DESIGN.md`](./runlog-author/DESIGN.md) §Status.

## Cross-vendor expansion — `[F25]`

The defensive moat for Runlog is being the cross-vendor knowledge layer that no single agent platform owns. As LLM vendors ship their own "skills" / "memory" / "knowledge" features, multi-vendor reach is what keeps Runlog relevant rather than getting absorbed into a single ecosystem.

Target vendors in priority order:

1. **Cursor** — largest agent-tool user base after Claude Code
2. **Cline** — open-source, MCP-native
3. **Continue.dev** — open-source, MCP-native
4. **Windsurf / Codeium**
5. **Aider** — CLI-native, MCP-capable
6. **Copilot via VS Code MCP extension**
7. **JetBrains AI Assistant via MCP plugin**
8. **Zed**

Each vendor gets two adapters:

- **Read-side** — port [`claude-code/SKILL.md`](./claude-code/SKILL.md) with vendor-specific MCP config, the team-memory surface to check first (`.cursorrules`, `.clinerules`, etc.), and how the dependency manifest is persisted across the agent's tool-use turns.
- **Write-side** — wrap [`runlog-author/SKILL.md`](./runlog-author/SKILL.md). The canonical author body is inherited byte-for-byte; the adapter swaps orchestration glue (vendor's tool-use API, agent-loop iteration, command palette / slash-command invocation, how local Bash is dispatched).

[`cursor/`](./cursor/README.md) and [`cline/`](./cline/README.md) are placeholder directories with READMEs describing what each adapter will contain.

## Layout

```
skills/
├── claude-code/                            # ✅ shipped — read side
│   └── SKILL.md
├── runlog-author/                          # ✅ shipped — write-side canonical body (vendor-agnostic)
│   ├── SKILL.md
│   └── DESIGN.md                           #     design rationale + open questions
├── common/                                 # 🚧 cross-vendor invariants (referenced by every adapter)
│   ├── README.md
│   ├── four-point-client-contract.md       # ✅ shipped
│   ├── runlog-author-contract.md           # ✅ shipped
│   ├── dependency-manifest.md              # ⏳ planned — F25
│   └── reporting-conventions.md            # ⏳ planned — F25
├── cursor/                                 # ⏳ placeholder — F25
│   └── README.md
├── cline/                                  # ⏳ placeholder — F25
│   └── README.md
└── README.md                               # this file
```

The `common/` extraction means each vendor adapter references invariants instead of re-authoring them — when the contract changes, one file moves, not eight.

## Invariants every adapter MUST honour

- The four rules in [`common/four-point-client-contract.md`](./common/four-point-client-contract.md) — both read and write skills inherit.
- The author-side rules in [`common/runlog-author-contract.md`](./common/runlog-author-contract.md) — adds the submission-flow constraints.

The contract is framework-agnostic; per-vendor adapters swap orchestration glue, not the rules.

## Depends on

- [`../schema/`](../schema/) — referenced in documentation only (not as a code dep)
- [`../verifier/`](../verifier/) — the `runlog-author` skill drives the local verifier binary; without it the write side cannot submit. Build with `cd verifier && make build`.
