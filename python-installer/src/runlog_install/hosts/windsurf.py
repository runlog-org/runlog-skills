"""windsurf.py — Host adapter for Windsurf (Codeium).

Installs the Runlog MCP server block into
~/.codeium/windsurf/mcp_config.json and copies the SKILL.md to
~/.codeium/windsurf/globalrules.

Windsurf reads MCP server config from ~/.codeium/windsurf/mcp_config.json
(documented in windsurf/SKILL.md §Setup step 3). Global rules are stored
at ~/.codeium/windsurf/globalrules.

Fallback mode: `add-mcp@1.8.0` does not support Windsurf, so this adapter
writes the SKILL file and edits the MCP config directly via the JSONC helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from runlog_install import jsonc


class WindsurfHost:
    """Host adapter for Windsurf (fallback mode — direct JSONC config edit)."""

    name: str = "Windsurf"
    target_key: str = "windsurf"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Windsurf global rules file under ~/.codeium/windsurf/
    SKILL_DEST: Path = Path.home() / ".codeium" / "windsurf" / "globalrules"

    # Windsurf MCP config: ~/.codeium/windsurf/mcp_config.json
    # Source: windsurf/SKILL.md §Setup step 3
    SETTINGS_PATH: Path = Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    # Source SKILL.md: <repo-root>/windsurf/SKILL.md
    # parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
    # [4]=runlog-skills/ (repo root). Matches CursorHost._SKILL_SRC pattern.
    _SKILL_SRC: Path = Path(__file__).resolve().parents[4] / "windsurf" / "SKILL.md"

    def install(self, api_key: str | None = None) -> None:
        """Write globalrules and merge the runlog MCP block into mcp_config.json.

        api_key is REQUIRED for fallback hosts — it carries the Bearer header
        written directly into the config file.
        """
        if api_key is None:
            raise ValueError(
                "api_key is required for WindsurfHost (fallback mode): "
                "pass the user's Runlog API key so the Bearer header can be "
                "written into mcp_config.json."
            )

        # 1. Validate source SKILL.md exists.
        skill_src = self._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: windsurf/SKILL.md "
                f"(expected at {skill_src})"
            )

        # 2. Copy SKILL.md to SKILL_DEST (mkdir -p parent).
        self.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
        self.SKILL_DEST.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

        # 3. Read SETTINGS_PATH (or a minimal seed if missing / empty).
        # Seed with an "mcpServers" key to avoid the JSONC bootstrap-path
        # inserting a leading comma into an empty root object.
        _SEED = '{\n  "mcpServers": {}\n}'
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else _SEED
        else:
            text = _SEED

        # 4. Insert / replace the runlog MCP block under "mcpServers".
        mcp_block = {
            "url": "https://api.runlog.org/mcp",
            "headers": {
                "Authorization": f"Bearer {api_key}",
            },
        }
        text = jsonc.add_to_object(text, ("mcpServers",), "runlog", mcp_block)

        # 5. Write back, mode 0600.
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def uninstall(self) -> None:
        """Remove globalrules and the runlog MCP block from mcp_config.json."""
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

        # 3. Remove the runlog key under "mcpServers".
        text = jsonc.remove_from_object(text, ("mcpServers",), "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
