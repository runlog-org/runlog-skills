"""windsurf.py — Host adapter for Windsurf (Codeium).

Installs the Runlog MCP server block into
~/.codeium/windsurf/mcp_config.json and concatenates the read / author /
harvest skill bodies into ~/.codeium/windsurf/globalrules.

Windsurf reads MCP server config from ~/.codeium/windsurf/mcp_config.json
(documented in windsurf/SKILL.md §Setup step 3). Global rules are stored
at ~/.codeium/windsurf/globalrules — a single shared file; the three
Runlog skills are placed there with ``# === Runlog <label> skill ===``
section headers between them.

Fallback mode: ``add-mcp@1.8.0`` does not support Windsurf, so this
adapter writes the skill file and edits the MCP config directly via the
JSONC helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from runlog_install import jsonc, skill_writer

# Source SKILL files: <repo-root>/windsurf/{SKILL,runlog-author,runlog-harvest}.md
# parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
# [4]=runlog-skills/ (repo root).
_VENDOR_DIR = Path(__file__).resolve().parents[4] / "windsurf"


class WindsurfHost:
    """Host adapter for Windsurf (fallback mode — direct JSONC config edit)."""

    name: str = "Windsurf"
    target_key: str = "windsurf"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Windsurf global rules file under ~/.codeium/windsurf/ — the three
    # Runlog skills concatenate into this single shared file.
    SKILL_DEST: Path = Path.home() / ".codeium" / "windsurf" / "globalrules"

    # Windsurf MCP config: ~/.codeium/windsurf/mcp_config.json
    # Source: windsurf/SKILL.md §Setup step 3
    SETTINGS_PATH: Path = Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    _SKILL_SRC: Path = _VENDOR_DIR / "SKILL.md"

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three specs sharing the same dest (globalrules) — concatenated on write."""
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", self.SKILL_DEST, "author"),
            (src_root / "runlog-harvest.md", self.SKILL_DEST, "harvest"),
        ]

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

        # 1. Write the read / author / harvest skill bodies into globalrules.
        skill_writer.write_skills(self.skill_sources, self.name)

        # 2. Read SETTINGS_PATH (or a minimal seed if missing / empty).
        # Seed with an "mcpServers" key to avoid the JSONC bootstrap-path
        # inserting a leading comma into an empty root object.
        _SEED = '{\n  "mcpServers": {}\n}'
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else _SEED
        else:
            text = _SEED

        # 3. Insert / replace the runlog MCP block under "mcpServers".
        mcp_block = {
            "url": "https://api.runlog.org/mcp",
            "headers": {
                "Authorization": f"Bearer {api_key}",
            },
        }
        text = jsonc.add_to_object(text, ("mcpServers",), "runlog", mcp_block)

        # 4. Write back, mode 0600.
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove globalrules and the runlog MCP block from mcp_config.json."""
        # 1. Remove SKILL_DEST (single shared file); rmdir empty parent dir.
        skill_writer.remove_skills(self.skill_sources)

        # 2. Read SETTINGS_PATH (skip if missing).
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog key under "mcpServers".
        text = jsonc.remove_from_object(text, ("mcpServers",), "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
