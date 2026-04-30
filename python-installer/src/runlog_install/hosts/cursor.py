"""cursor.py — Host adapter for Cursor.

Installs the Runlog MCP server block into ~/.cursor/mcp.json and copies
the runlog.mdc rule file to ~/.cursor/rules/.
"""

from __future__ import annotations

from pathlib import Path

from runlog_install import jsonc


class CursorHost:
    """Host adapter for Cursor."""

    name: str = "Cursor"
    target_key: str = "cursor"

    SKILL_DEST: Path = Path.home() / ".cursor" / "rules" / "runlog.mdc"
    SETTINGS_PATH: Path = Path.home() / ".cursor" / "mcp.json"

    # Source SKILL.md relative to this file: <repo>/cursor/SKILL.md
    # parents[0] = hosts/  parents[1] = runlog_install/  parents[2] = src/
    # parents[3] = python-installer/  parents[4] = runlog-skills/ (repo root)
    _SKILL_SRC: Path = Path(__file__).resolve().parents[4] / "cursor" / "SKILL.md"

    def install(self, api_key: str) -> None:
        """Write runlog.mdc and merge the runlog MCP block into mcp.json."""
        # 1. Copy SKILL.md to SKILL_DEST (mkdir -p parent)
        skill_src = self._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: cursor/SKILL.md (expected at {skill_src})"
            )
        self.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
        self.SKILL_DEST.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

        # 2. Read SETTINGS_PATH (or a minimal seed if missing / empty).
        # Seed with an "mcpServers" key to avoid the JSONC bootstrap-path
        # inserting a leading comma into an empty root object.
        _SEED = '{\n  "mcpServers": {}\n}'
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else _SEED
        else:
            text = _SEED

        # 3. Insert / replace the runlog MCP block under "mcpServers"
        mcp_block = {
            "url": "https://api.runlog.org/mcp",
            "headers": {
                "Authorization": f"Bearer {api_key}",
            },
        }
        text = jsonc.add_to_object(text, ("mcpServers",), "runlog", mcp_block)

        # 4. Write back, mode 0600
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def uninstall(self) -> None:
        """Remove runlog.mdc and the runlog MCP block from mcp.json."""
        # 1. Remove SKILL_DEST; rmdir empty parent dirs
        self.SKILL_DEST.unlink(missing_ok=True)
        try:
            self.SKILL_DEST.parent.rmdir()
        except OSError:
            pass  # directory not empty or doesn't exist — leave it alone

        # 2. Read SETTINGS_PATH (skip if missing)
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog key under "mcpServers"
        text = jsonc.remove_from_object(text, ("mcpServers",), "runlog")

        # 4. Write back
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
