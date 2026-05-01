"""copilot.py — Host adapter for GitHub Copilot (VS Code).

Installs the Runlog MCP server block into VS Code's user-scope MCP config
file and copies the SKILL.md as a Copilot instruction file.

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

The Copilot instruction (SKILL.md) is copied to .github/copilot-instructions.md
in the user's home directory so it is picked up by Copilot Chat's agent mode.

Fallback mode: `add-mcp` does not support the VS Code Copilot MCP config
file at user scope, so this adapter edits the JSONC config directly.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from runlog_install import jsonc


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


class CopilotHost:
    """Host adapter for GitHub Copilot / VS Code (fallback mode — direct JSONC edit)."""

    name: str = "GitHub Copilot (VS Code)"
    target_key: str = "copilot"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Copilot instruction file: home/.github/copilot-instructions.md
    # VS Code Copilot loads this automatically when
    # github.copilot.chat.codeGeneration.useInstructionFiles is true (default).
    SKILL_DEST: Path = Path.home() / ".github" / "copilot-instructions.md"

    # VS Code user-scope MCP config: <user-data-dir>/mcp.json
    # Platform-resolved at class body time; tests override via monkeypatch.
    # Wrap in try/except so the module is importable on unsupported platforms
    # (e.g. Windows CI) without raising at import time.
    try:
        SETTINGS_PATH: Path = _vscode_user_dir() / "mcp.json"
    except RuntimeError:
        SETTINGS_PATH: Path = Path.home() / ".config" / "Code" / "User" / "mcp.json"

    # Source SKILL.md: <repo-root>/copilot/SKILL.md
    # parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
    # [4]=runlog-skills/ (repo root).
    _SKILL_SRC: Path = Path(__file__).resolve().parents[4] / "copilot" / "SKILL.md"

    def install(self, api_key: str | None = None) -> None:
        """Write Copilot instructions and merge the runlog MCP block into mcp.json.

        api_key is REQUIRED for fallback hosts — it carries the Bearer header
        written directly into the config file.
        """
        if api_key is None:
            raise ValueError(
                "api_key is required for CopilotHost (fallback mode): "
                "pass the user's Runlog API key so the Bearer header can be "
                "written into mcp.json."
            )

        # 1. Validate source SKILL.md exists.
        skill_src = self._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: copilot/SKILL.md "
                f"(expected at {skill_src})"
            )

        # 2. Copy SKILL.md to SKILL_DEST (mkdir -p parent).
        self.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
        self.SKILL_DEST.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

        # 3. Read SETTINGS_PATH (or a minimal seed if missing / empty).
        # Seed with a "servers" key to avoid the JSONC bootstrap-path
        # inserting a leading comma into an empty root object.
        _SEED = '{\n  "servers": {}\n}'
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else _SEED
        else:
            text = _SEED

        # 4. Insert / replace the runlog MCP block under "servers".
        # VS Code uses "servers" (not "mcpServers") in its mcp.json schema.
        # Source: https://code.visualstudio.com/docs/copilot/customization/mcp-servers
        mcp_block = {
            "type": "http",
            "url": "https://api.runlog.org/mcp",
            "headers": {
                "Authorization": f"Bearer {api_key}",
            },
        }
        text = jsonc.add_to_object(text, ("servers",), "runlog", mcp_block)

        # 5. Write back, mode 0600.
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove Copilot instructions and the runlog MCP block from mcp.json."""
        # 1. Remove SKILL_DEST; rmdir empty parent dirs.
        self.SKILL_DEST.unlink(missing_ok=True)
        try:
            self.SKILL_DEST.parent.rmdir()
        except OSError:
            pass  # directory not empty or doesn't exist — leave it alone

        # 2. Read SETTINGS_PATH (skip if missing).
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog key under "servers".
        text = jsonc.remove_from_object(text, ("servers",), "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
