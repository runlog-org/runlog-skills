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
from typing import Literal

from runlog_install import jsonc, skill_writer


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


# Source SKILL files: <repo-root>/copilot/{SKILL,runlog-author,runlog-harvest}.md
# parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
# [4]=runlog-skills/ (repo root).
_VENDOR_DIR = Path(__file__).resolve().parents[4] / "copilot"


class CopilotHost:
    """Host adapter for GitHub Copilot / VS Code (fallback mode — direct JSONC edit)."""

    name: str = "GitHub Copilot (VS Code)"
    target_key: str = "copilot"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Copilot instruction file: home/.github/copilot-instructions.md.
    # All three Runlog skills concatenate into this single shared file.
    SKILL_DEST: Path = Path.home() / ".github" / "copilot-instructions.md"

    # VS Code user-scope MCP config: <user-data-dir>/mcp.json
    # Platform-resolved at class body time; tests override via monkeypatch.
    # Wrap in try/except so the module is importable on unsupported platforms
    # (e.g. Windows CI) without raising at import time.
    try:
        SETTINGS_PATH: Path = _vscode_user_dir() / "mcp.json"
    except RuntimeError:
        SETTINGS_PATH: Path = Path.home() / ".config" / "Code" / "User" / "mcp.json"

    _SKILL_SRC: Path = _VENDOR_DIR / "SKILL.md"

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three specs sharing the same dest (copilot-instructions.md) — concatenated on write."""
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", self.SKILL_DEST, "author"),
            (src_root / "runlog-harvest.md", self.SKILL_DEST, "harvest"),
        ]

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

        # 1. Write the concatenated read / author / harvest bundle to copilot-instructions.md.
        skill_writer.write_skills(self.skill_sources, self.name)

        # 2. Read SETTINGS_PATH (or a minimal seed if missing / empty).
        # Seed with a "servers" key to avoid the JSONC bootstrap-path
        # inserting a leading comma into an empty root object.
        _SEED = '{\n  "servers": {}\n}'
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else _SEED
        else:
            text = _SEED

        # 3. Insert / replace the runlog MCP block under "servers".
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

        # 4. Write back, mode 0600.
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove Copilot instructions and the runlog MCP block from mcp.json."""
        # 1. Remove SKILL_DEST (single shared file); rmdir empty parent dir.
        skill_writer.remove_skills(self.skill_sources)

        # 2. Read SETTINGS_PATH (skip if missing).
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog key under "servers".
        text = jsonc.remove_from_object(text, ("servers",), "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
