# Runlog Skills — MCP Client Skills

> Part of the **[Runlog](https://github.com/runlog-org)** project — see the [project home](https://github.com/runlog-org) for the overview.

**Repo:** [`runlog-org/runlog-skills`](https://github.com/runlog-org/runlog-skills) — public, MIT
**Content:** Agent skill files and MCP client configs
**Role:** drop-in adapters that wrap the Runlog MCP tools (`runlog_search`, `runlog_submit`, `runlog_report`) for nine vendor agent frameworks. Each adapter honours the four-point client contract in [`common/four-point-client-contract.md`](./common/four-point-client-contract.md) — team-memory-first, external-only classification, route learnings to the right layer, maintain a dependency manifest.

Drop-in skill files so agents running Claude Code, Cursor, Cline, Continue, Windsurf, Aider, VS Code Copilot, JetBrains AI Assistant, and Zed can use Runlog without writing their own MCP plumbing. Each skill wraps `runlog_search`, `runlog_submit`, and `runlog_report` with the right framework-specific glue.

Also standardises how each agent framework tracks `kb:<id>` entries in its working session so the server's failure-attribution engine gets clean dependency manifests.

## What's shipped today

All 9 vendor adapters (Claude Code + 8 cross-vendor expansion) are operational on the read side against the live MCP server. The write side ships per-vendor too; end-to-end functionality is gated on three F24 prerequisites — see [`runlog-author/DESIGN.md`](./runlog-author/DESIGN.md) §Status.

| Vendor | Read | Write | Harvest | Read-side install | Notes |
|---|---|---|---|---|---|
| **Claude Code** | ✅ | ✅ | ✅ | [`claude-code/SKILL.md`](./claude-code/SKILL.md) | Reference adapter |
| **Cursor** | ✅ | ✅ | ✅ | [`cursor/SKILL.md`](./cursor/SKILL.md) → `.cursor/rules/runlog.mdc` | Highest priority after Claude Code |
| **Cline** | ✅ | ✅ | ✅ | [`cline/SKILL.md`](./cline/SKILL.md) → `.clinerules/runlog.md` | Open-source, MCP-native |
| **Continue.dev** | ✅ | ✅ | ✅ | [`continue/SKILL.md`](./continue/SKILL.md) → `.continue/config.yaml` rules block | Open-source, MCP-native |
| **Windsurf** | ✅ | ✅ | ✅ | [`windsurf/SKILL.md`](./windsurf/SKILL.md) → `.windsurfrules` | Codeium-based |
| **Aider** | ✅ * | ✅ * | ✅ * | [`aider/SKILL.md`](./aider/SKILL.md) → `CONVENTIONS.md` or `--read` | * MCP support is version-dependent |
| **VS Code + GitHub Copilot** | ✅ | ✅ | ✅ | [`copilot/SKILL.md`](./copilot/SKILL.md) → `.github/copilot-instructions.md` | Requires Copilot agent mode |
| **JetBrains AI Assistant** | ✅ * | ✅ * | ✅ * | [`jetbrains/SKILL.md`](./jetbrains/SKILL.md) → AI guidelines | * Tool-use varies by IDE / plugin version |
| **Zed** | ✅ * | ✅ * | ✅ * | [`zed/SKILL.md`](./zed/SKILL.md) → `.rules` | * HTTP `context_servers` schema is evolving |

Asterisks (`*`) flag adapters whose MCP integration is evolving in the upstream vendor — the adapter is shipped and works against today's vendor capabilities, but check the per-vendor README's "VERIFY" notes against current vendor docs before publishing your config.

Three skill types ship per vendor: **read** ([`SKILL.md`](./claude-code/SKILL.md)) wraps `runlog_search` so the agent consults the registry when team memory falls short; **author / write** ([`runlog-author.md`](./runlog-author/SKILL.md)) drives the verifier-loop submission flow mid-flow, right after a third-party-system gotcha is solved; **harvest** ([`runlog-harvest.md`](./runlog-harvest/SKILL.md)) is the end-of-session retrospective lever — invoked explicitly via `/runlog:harvest` (or each vendor's literal — see per-vendor READMEs), it scans the just-finished session for external-dependency findings the agent missed in-flight and routes selected ones through the canonical author flow. The canonical bodies under [`runlog-author/`](./runlog-author/SKILL.md) and [`runlog-harvest/`](./runlog-harvest/SKILL.md) are the source of truth; per-vendor folders inherit them and swap orchestration glue.

## Install

Five install paths, in order of preference for a given vendor:

### 1. Claude Code: plugin marketplace (smoothest for Claude Code)

Claude Code users get the smoothest install — the plugin auto-registers the Runlog MCP server **and** drops the skills in place, so no manual MCP config edits and no separate `cp` step for the skill body:

```text
/plugin marketplace add runlog-org/runlog-skills
/plugin install runlog
```

Then `export RUNLOG_API_KEY=sk-runlog-<your-key>` (key from <https://runlog.org/register>) and the `runlog` and `runlog-author` skills are available in any session.

### 2. Cross-vendor MCP install: `npx add-mcp` (Claude Code, Cursor, Cline)

The one-liner that covers the three Runlog vendors `add-mcp` writes a working config for. Neon's [`add-mcp`](https://github.com/neondatabase/add-mcp) reads Runlog's [Official MCP Registry](https://registry.modelcontextprotocol.io/) entry (`org.runlog/runlog`) and auto-detects every supported agent on the machine, writing the correct config for each:

```sh
npx add-mcp https://api.runlog.org/mcp
```

Pass `-a <agent>` to target one host (`claude-code`, `cursor`, `cline`); pass `-g` for a global config rather than project-scoped. Validated for: Claude Code, Cursor, Cline (both VS Code extension and `cline-cli`).

**Continue, Windsurf, Aider, VS Code Copilot, and JetBrains are not in `add-mcp`'s supported set today** — use path 3, 4, or 5 for those vendors. Zed is in `add-mcp`'s supported set; the python-installer (path 4) also covers it as a delegated target.

`add-mcp` only writes the MCP server config; the per-vendor `SKILL.md` body still needs to land in the host's rules path. Either copy it manually (path 5) or use the python-installer (path 4) or run `npx @runlog/install <vendor> --write` (path 3) for the skill side. The Claude Code plugin (path 1) does both in one step.

### 3. Any vendor: `npx @runlog/install <vendor>`

```sh
# Print the rule + MCP config for review
npx @runlog/install cursor

# Or write directly to the vendor's rules path
npx @runlog/install cursor --write
```

Vendors: `claude-code`, `cursor`, `cline`, `continue`, `windsurf`, `aider`, `copilot`, `jetbrains`, `zed`. The installer fetches the canonical `SKILL.md` from this repo's `main` and writes it to the right vendor-specific path (or prints it for vendors that share a single rules file with the user's other content). It does **not** auto-edit your MCP config — it prints the snippet for you to merge in. See [`installer/README.md`](./installer/README.md) for full flag reference.

### 4. Python installer: `runlog install --target <host>` (no npm required)

A stdlib-only Python installer (`pipx install runlog-installer`) covers five hosts across two modes. Use this when npm is not available or you want a single command that handles both SKILL placement and MCP-config editing for hosts `add-mcp` does not reach.

| Target | Host | Mode | What gets installed |
|---|---|---|---|
| `claude` | Claude Code | delegated | SKILL only — wire MCP via `npx add-mcp` |
| `cursor` | Cursor | delegated | SKILL only — wire MCP via `npx add-mcp` |
| `zed` | Zed | delegated | SKILL only — wire MCP via `npx add-mcp` |
| `windsurf` | Windsurf | fallback | SKILL + MCP-config edit (no npm needed) |
| `copilot` | GitHub Copilot (VS Code) | fallback | SKILL + MCP-config edit (no npm needed) |

Delegated hosts use `add-mcp` for the MCP wiring step; the installer places the SKILL and prints the reminder. Fallback hosts get both the SKILL and the MCP block written directly — an API key is required (`--api-key` flag, `RUNLOG_API_KEY` env, or interactive prompt).

The python-installer also provides `runlog register --email <addr>` to orchestrate the verifier registration flow. See [`python-installer/README.md`](./python-installer/README.md) for the full reference.

**Not yet automated (Continue, Aider, JetBrains):** These three hosts' config formats are incompatible with the installer's JSONC helper — Continue uses YAML, Aider uses YAML with an array-shape server list, and JetBrains AI Assistant's config path and format are not confirmed. Use path 5 (manual) for these hosts until a follow-up slice ships support.

### 5. Manual: clone + copy

The original install model still works — each per-vendor folder's README has a `Quickstart` section that walks through `cp <vendor>/SKILL.md <target-path>` plus the MCP config to add. Use this if you want to read the rule before installing it, or your environment has neither npm nor Python.

## Cross-vendor expansion strategy — `[F25]`

The defensive moat for Runlog is being the cross-vendor knowledge layer that no single agent platform owns. As LLM vendors ship their own "skills" / "memory" / "knowledge" features, multi-vendor reach is what keeps Runlog relevant rather than getting absorbed into a single ecosystem.

Each vendor gets two adapters:

- **Read-side** — port [`claude-code/SKILL.md`](./claude-code/SKILL.md) with vendor-specific MCP config, the team-memory surface to check first (`.cursorrules`, `.clinerules`, `.windsurfrules`, `.github/copilot-instructions.md`, etc.), and how the dependency manifest is persisted across the agent's tool-use turns.
- **Write-side** — wrap [`runlog-author/SKILL.md`](./runlog-author/SKILL.md). The canonical author body is inherited byte-for-byte; the adapter swaps orchestration glue (vendor's tool-use API, agent-loop iteration, command palette / slash-command invocation, how local Bash is dispatched).

The `common/` extraction means each vendor adapter references cross-vendor invariants instead of re-authoring them — when the contract changes, one file moves, not nine.

## Layout

```text
skills/
├── .claude-plugin/                         # ✅ Claude Code plugin marketplace + plugin manifest
│   ├── marketplace.json
│   └── plugin.json
├── .mcp.json                               # ✅ MCP server registered when plugin installs
├── skills/                                 # ✅ Plugin-discoverable skills (mirrors of canonical bodies)
│   ├── runlog/SKILL.md
│   └── runlog-author/SKILL.md
├── installer/                              # ✅ npx @runlog/install package source
│   ├── package.json
│   ├── index.js
│   └── README.md
├── claude-code/                            # ✅ Reference adapter (read side; canonical body)
│   ├── SKILL.md
│   └── runlog-harvest.md
├── commands/                               # ✅ Slash-command shims (e.g. `/runlog:harvest`)
│   └── harvest.md
├── runlog-author/                          # ✅ Canonical author body (vendor-agnostic)
│   ├── SKILL.md
│   └── DESIGN.md                           #     design rationale + open questions
├── runlog-harvest/                         # ✅ Canonical harvest body (vendor-agnostic)
│   ├── SKILL.md
│   └── DESIGN.md                           #     design rationale + open questions
├── common/                                 # ✅ Cross-vendor invariants
│   ├── README.md
│   ├── four-point-client-contract.md       # ✅ shipped
│   ├── runlog-author-contract.md           # ✅ shipped
│   ├── runlog-harvest-contract.md          # ✅ shipped
│   ├── dependency-manifest.md              # ⏳ planned — extracted when 2nd consumer ships
│   └── reporting-conventions.md            # ⏳ planned — extracted when 2nd consumer ships
├── cursor/                                 # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
├── cline/                                  # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
├── continue/                               # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
├── windsurf/                               # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
├── aider/                                  # ✅ shipped (caveats)
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
├── copilot/                                # ✅ shipped
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
├── jetbrains/                              # ✅ shipped (caveats)
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
├── zed/                                    # ✅ shipped (caveats)
│   ├── README.md
│   ├── SKILL.md
│   ├── runlog-author.md
│   └── runlog-harvest.md
└── README.md                               # this file
```

## Invariants every adapter MUST honour

- The four rules in [`common/four-point-client-contract.md`](./common/four-point-client-contract.md) — read, write, and harvest skills all inherit.
- The author-side rules in [`common/runlog-author-contract.md`](./common/runlog-author-contract.md) — adds the submission-flow constraints.
- The harvest-side rules in [`common/runlog-harvest-contract.md`](./common/runlog-harvest-contract.md) — adds the retrospective-scan, picker-grammar, and route-to-author constraints.

The contract is framework-agnostic; per-vendor adapters swap orchestration glue, not the rules.

## Maintenance pattern

When the cross-vendor contract changes (e.g. a new MUST-NOT rule or a tool-call shape update), the change pattern is:

1. Update `common/four-point-client-contract.md` and/or `common/runlog-author-contract.md` (single source of truth).
2. Re-sync each per-vendor SKILL.md / runlog-author.md by re-reading the canonical body and bringing the vendor wrapper in line.
3. The bodies are deliberately ~80% similar across vendors — the vendor-specific glue is concentrated in the **Setup** sections and a few notes paragraphs.
4. Re-sync the plugin's discovery copies: `cp claude-code/SKILL.md skills/runlog/SKILL.md` and `cp runlog-author/SKILL.md skills/runlog-author/SKILL.md`. (The `skills/` tree is what Claude Code's plugin loader reads; the canonical bodies stay at their established paths so existing per-vendor wrappers don't need to chase a path move. CIFS doesn't allow symlinks, so they're plain copies.)

The npx installer (`installer/index.js`) fetches `<vendor>/SKILL.md` live from `main` on GitHub at install time, so it always pulls the latest canonical body — no version coupling to maintain.

Future tooling (a generator script that produces vendor adapters from the canonical body + a vendor-glue spec) is a maintenance-pain follow-up; not yet needed at 9 vendors.

### Publishing `@runlog/install` to npm

The npm scope `@runlog` must be claimed before first publish (`npm org create runlog` while logged in as the maintainer, or register a user named `runlog`). Once the scope exists:

```sh
cd installer
npm publish --access public
```

Bump the version in `installer/package.json` for each release. The installer fetches its content from GitHub at runtime, so users always get the latest skill body regardless of which installer version they ran.

## Depends on

- [`runlog-org/runlog-schema`](https://github.com/runlog-org/runlog-schema) — referenced in documentation only (not as a code dep)
- [`runlog-org/runlog-verifier`](https://github.com/runlog-org/runlog-verifier) — the `runlog-author` skill drives the local verifier binary; without it the write side cannot submit. Build with `git clone … && make build` in the verifier repo.
