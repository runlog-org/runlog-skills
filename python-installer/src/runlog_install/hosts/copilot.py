"""copilot.py — Host adapter for GitHub Copilot (VS Code).

Installs the Runlog MCP server block into VS Code's user-scope MCP config
file and concatenates the read / author / harvest skill bodies into a
single Copilot instruction file.

VS Code reads MCP server config from two locations:
  - Workspace scope:  .vscode/mcp.json  (per-project)
  - User/global scope: <user-data-dir>/mcp.json

This adapter targets user/global scope, since the installer is invoked once
per user rather than per workspace.  The user-data directory differs by OS:

  Linux:  ~/.config/Code/User/
  macOS:  ~/Library/Application Support/Code/User/

Config format is JSONC (JSON with comments — VS Code's standard).  The MCP
block structure uses a named-key object under the top-level "servers" key:

  {
    "servers": {
      "runlog": {
        "type": "http",
        "url": "https://api.runlog.org/mcp",
        "headers": { "Authorization": "Bearer <key>" }
      }
    }
  }

Source:
  - copilot/SKILL.md §Setup step 3
  - https://code.visualstudio.com/docs/copilot/customization/mcp-servers

The Copilot instructions (the Runlog read / author / harvest bundle) are
copied to .github/copilot-instructions.md in the user's home directory so
they are picked up by Copilot Chat's agent mode. The three skill bodies
are concatenated with ``# === Runlog <label> skill ===`` section headers.

Fallback mode: ``add-mcp`` does not support the VS Code Copilot MCP config
file at user scope, so this adapter edits the JSONC config directly.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar, Literal

from runlog_install.hosts._base import (
    BaseHost,
    FallbackMixin,
    RUNLOG_MCP_URL,
    SharedFileMixin,
)


def _vscode_user_dir() -> Path:
    """Return the VS Code user-data directory for the current platform.

    Supports Linux and macOS only (v0 scope — Windows users are sparse).
    Raises RuntimeError on unsupported platforms.
    """
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User"
    if sys.platform.startswith("linux"):
        return Path.home() / ".config" / "Code" / "User"
    raise RuntimeError(
        f"CopilotHost: unsupported platform {sys.platform!r}. "
        "Only Linux and macOS are supported in v0."
    )


class CopilotHost(BaseHost, FallbackMixin, SharedFileMixin):
    """Host adapter for GitHub Copilot / VS Code (fallback mode — direct JSONC edit)."""

    name: ClassVar[str] = "GitHub Copilot (VS Code)"
    target_key: ClassVar[str] = "copilot"
    _VENDOR_KEY: ClassVar[str] = "copilot"

    # Copilot instruction file: home/.github/copilot-instructions.md.
    # All three Runlog skills concatenate into this single shared file.
    SKILL_DEST: ClassVar[Path] = Path.home() / ".github" / "copilot-instructions.md"

    _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"

    # VS Code uses "servers" (not "mcpServers") in its mcp.json schema.
    # Source: https://code.visualstudio.com/docs/copilot/customization/mcp-servers
    _TOP_LEVEL_KEY: ClassVar[str] = "servers"

    # VS Code user-scope MCP config: <user-data-dir>/mcp.json
    # Resolved lazily on first access so the platform check fires at
    # install/uninstall time rather than at import time.  Tests override by
    # monkeypatching the class attribute directly (which shadows the property).
    def __init__(self) -> None:
        self._settings_path: Path | None = None

    @property
    def SETTINGS_PATH(self) -> Path:
        if self._settings_path is None:
            self._settings_path = _vscode_user_dir() / "mcp.json"
        return self._settings_path

    @SETTINGS_PATH.setter
    def SETTINGS_PATH(self, value: Path) -> None:
        self._settings_path = value

    def _mcp_block(self, api_key: str) -> dict:
        """Return the MCP block matching copilot/SKILL.md §Setup JSONC shape."""
        return {
            "type": "http",
            "url": RUNLOG_MCP_URL,
            "headers": {"Authorization": f"Bearer {api_key}"},
        }
