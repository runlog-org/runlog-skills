"""cursor.py — Host adapter for Cursor.

Delegated mode: copies the runlog read / author / harvest rule files to
``~/.cursor/rules/``. MCP server wiring is handled separately by the user
via ``npx add-mcp``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from runlog_install import skill_writer

# Source SKILL files: <repo>/cursor/{SKILL,runlog-author,runlog-harvest}.md
# parents[0] = hosts/  parents[1] = runlog_install/  parents[2] = src/
# parents[3] = python-installer/  parents[4] = runlog-skills/ (repo root)
_VENDOR_DIR = Path(__file__).resolve().parents[4] / "cursor"


class CursorHost:
    """Host adapter for Cursor."""

    name: str = "Cursor"
    target_key: str = "cursor"
    mode: Literal["delegated", "fallback"] = "delegated"

    # Read-skill destination + source — kept as named class attrs for
    # back-compat with the make_host fixture monkeypatching.
    SKILL_DEST: Path = Path.home() / ".cursor" / "rules" / "runlog.mdc"
    _SKILL_SRC: Path = _VENDOR_DIR / "SKILL.md"

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three (source, dest, label) specs — read / author / harvest .mdc files."""
        rules_dir = self.SKILL_DEST.parent  # .../rules/
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", rules_dir / "runlog-author.mdc", "author"),
            (src_root / "runlog-harvest.md", rules_dir / "runlog-harvest.mdc", "harvest"),
        ]

    def install(self, api_key: str | None = None) -> None:
        """Write the read / author / harvest .mdc files (mkdir -p parent)."""
        skill_writer.write_skills(self.skill_sources, self.name)

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove the three .mdc rule files and the (now-empty) parent directory."""
        skill_writer.remove_skills(self.skill_sources)
