# `@runlog/install`

One-command install of the Runlog client skills for any of the nine supported agent frameworks. Each vendor gets all three skills: the read-side `runlog` skill, the `runlog-author` write skill, and the `runlog-harvest` skill.

```sh
npx @runlog/install <vendor>
```

Supported vendors: `claude-code`, `cursor`, `cline`, `continue`, `windsurf`, `aider`, `copilot`, `jetbrains`, `zed`.

## How it works

The installer fetches all three per-vendor skill bodies (`SKILL.md`, `runlog-author.md`, `runlog-harvest.md`) from `runlog-org/runlog-skills` on GitHub (always the latest `main`) and either prints them (default, safe) or writes them to the vendor's rules paths (`--write`). For shared-file vendors the three bodies are concatenated with section headers so you can merge them into your existing rules file.

It **does not** auto-edit your vendor's MCP config — `~/.cursor/mcp.json`, `~/.codeium/windsurf/mcp_config.json`, etc. likely already contain other servers, and clobbering them would be a footgun. Instead the installer prints the Runlog MCP server snippet and you paste it in.

## Common usage

```sh
# Cursor — print the rule and MCP config
npx @runlog/install cursor

# Cursor — write to .cursor/rules/runlog.mdc
npx @runlog/install cursor --write

# Cursor — write to ~/.cursor/rules/runlog.mdc (user-global)
npx @runlog/install cursor --write --global

# Cline — write to .clinerules/runlog.md
npx @runlog/install cline --write
```

## Vendor-by-vendor

| Vendor | `--write` targets (read / author / harvest) | `--global` target prefix | Mode |
|---|---|---|---|
| `claude-code` | `.claude/skills/runlog/SKILL.md`, `.claude/skills/runlog-author/SKILL.md`, `.claude/skills/runlog-harvest/SKILL.md` | `~/.claude/skills/...` | write supported (but the plugin marketplace is preferred — see below) |
| `cursor` | `.cursor/rules/runlog.mdc`, `.cursor/rules/runlog-author.mdc`, `.cursor/rules/runlog-harvest.mdc` | `~/.cursor/rules/...` | write supported |
| `cline` | `.clinerules/runlog.md`, `.clinerules/runlog-author.md`, `.clinerules/runlog-harvest.md` | — | write supported |
| `continue` | `.continue/rules/runlog.md`, `.continue/rules/runlog-author.md`, `.continue/rules/runlog-harvest.md` | — | write supported |
| `windsurf` | `.windsurfrules` | — | print only (shared file, 3 sections) |
| `aider` | `CONVENTIONS.md` | — | print only (shared file, 3 sections) |
| `copilot` | `.github/copilot-instructions.md` | — | print only (shared file, 3 sections) |
| `jetbrains` | IDE Settings → AI Assistant | — | print only (settings UI, 3 sections) |
| `zed` | `.rules` | — | print only (shared file, 3 sections) |

Vendors marked "print only" already share a single file with your other rules — auto-overwriting it would clobber your existing content, so the installer prints all three skill bodies (read, author, harvest) with section dividers for you to merge.

## Claude Code: prefer the plugin marketplace

The smoothest install for Claude Code is the official plugin, which also auto-registers the Runlog MCP server (no manual config edit):

```text
/plugin marketplace add runlog-org/runlog-skills
/plugin install runlog
```

`npx @runlog/install claude-code --write` is the manual fallback if you'd rather not use the plugin system.

## After install: register the MCP server

The installer prints the snippet. You'll need to:

1. Set `RUNLOG_API_KEY` to your key from <https://runlog.org/register>.
2. Add the printed `mcpServers.runlog` block to your vendor's MCP config.
3. Restart your agent so the new MCP server is picked up.

## License

MIT — see `LICENSE` in the parent repo.
