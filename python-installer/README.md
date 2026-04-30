# runlog-installer

Single-command installer for the [Runlog](https://runlog.org) MCP server.

## What it does

`runlog install` writes the Runlog skill file and merges the MCP server block
into your AI coding host's settings — no manual JSON editing required.

`runlog uninstall` surgically removes the MCP server block and the skill file,
leaving the rest of your host config untouched.

## Install

```sh
pipx install runlog-installer
```

Or with pip:

```sh
pip install runlog-installer
```

## Usage

```sh
# Install for Claude Code
runlog install --target claude --api-key <YOUR_API_KEY>

# Install for Cursor
runlog install --target cursor --api-key <YOUR_API_KEY>

# Uninstall from Claude Code
runlog uninstall --target claude

# Uninstall from Cursor
runlog uninstall --target cursor
```

## Supported targets

| Flag value | Host |
|---|---|
| `claude` | Claude Code |
| `cursor` | Cursor |

More hosts coming soon (Cline, Continue, Copilot, JetBrains, Windsurf, Zed, and Aider).
