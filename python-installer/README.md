# runlog-installer

Single-command installer for the [Runlog](https://runlog.org) MCP server.
Complements `npx add-mcp` by handling what `add-mcp` does not: placing the
Runlog SKILL file, writing MCP config for hosts `add-mcp` does not reach, and
orchestrating the `runlog-verifier` registration flow.

## What it does

`runlog install` writes the Runlog skill file into the host's rules path and,
for fallback hosts, merges the MCP server block directly into the host's config
file — no manual JSON editing required.

`runlog uninstall` surgically removes the MCP server block and the skill file,
leaving the rest of your host config untouched.

`runlog register --email <addr>` orchestrates the `runlog-verifier` Ed25519
registration flow without you needing to invoke the verifier binary directly.

## Install

```sh
pipx install runlog-installer
```

Or with pip:

```sh
pip install runlog-installer
```

The installer is stdlib-only — no third-party Python dependencies.

## Supported hosts

| Target | Host | Mode | What gets installed |
|---|---|---|---|
| `claude` | Claude Code | delegated | SKILL only — wire MCP via `npx add-mcp` |
| `cursor` | Cursor | delegated | SKILL only — wire MCP via `npx add-mcp` |
| `zed` | Zed | delegated | SKILL only — wire MCP via `npx add-mcp` |
| `windsurf` | Windsurf | fallback | SKILL + MCP-config edit at `~/.codeium/windsurf/mcp_config.json` |
| `copilot` | GitHub Copilot (VS Code) | fallback | SKILL + MCP-config edit at VS Code's user `mcp.json` |

**Delegated mode** — `add-mcp` covers these hosts natively. The installer
places the SKILL file and then tells you to run `npx add-mcp` for the MCP
wiring. No API key needed at install time.

**Fallback mode** — `add-mcp` does not reach these hosts. The installer writes
the SKILL file and edits the JSON config directly. An API key is required so
the Bearer header can be written into the config file.

## Usage

```sh
# Delegated hosts — no API key needed at install time
runlog install --target claude
runlog install --target cursor
runlog install --target zed

# Fallback hosts — API key is required
runlog install --target windsurf --api-key $RUNLOG_API_KEY
runlog install --target copilot  --api-key $RUNLOG_API_KEY

# Uninstall (removes SKILL + MCP block if any)
runlog uninstall --target <target>

# Register an Ed25519 keypair with the Runlog server
runlog register --email user@example.com
```

After a delegated install, the CLI prints a reminder to run:

```sh
npx add-mcp https://api.runlog.org/mcp
```

Then restart your editor.

## API key resolution (fallback hosts only)

For fallback hosts the API key is resolved in this order:

1. `--api-key <value>` flag
2. `RUNLOG_API_KEY` environment variable
3. Interactive prompt (stdin)

Delegated hosts do not require an API key at install time — the key is supplied
when you run `npx add-mcp` separately.

Get a key at <https://runlog.org/register>.

## `register --email`

```sh
runlog register --email user@example.com
```

Shells out to `runlog-verifier register --email <addr>` to generate an Ed25519
keypair and register it against the Runlog server. A verification email is sent
to the supplied address.

`runlog-verifier` must be on your `PATH`. If it is not found, the installer
prints a platform-specific download and install hint then exits with code 2.
Download from the [runlog-verifier releases page](https://github.com/runlog-org/runlog-verifier/releases/latest).

## Not yet supported

The following hosts are explicitly deferred from this release:

| Host | Reason |
|---|---|
| Continue.dev | Config is YAML in 1.0+; the legacy JSON format uses an array-shape MCP server list — both incompatible with the stdlib JSONC helper |
| Aider | Config is YAML and uses an array-shape MCP server list |
| JetBrains AI Assistant | Config format not confirmed as JSON with a documented path; likely XML |

These hosts' config formats require writers we haven't built. Track via
M01-S02 follow-up items. In the meantime, install Runlog for these hosts
manually — see each host's `SKILL.md` in the [runlog-skills repo](https://github.com/runlog-org/runlog-skills).
