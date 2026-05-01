"""cursor.py — Host adapter for Cursor.

Delegated mode: copies the runlog.mdc rule file to ~/.cursor/rules/.
MCP server wiring is handled separately by the user via `npx add-mcp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal


class CursorHost:
    """Host adapter for Cursor."""

    name: str = "Cursor"
    target_key: str = "cursor"
    mode: Literal["delegated", "fallback"] = "delegated"

    SKILL_DEST: Path = Path.home() / ".cursor" / "rules" / "runlog.mdc"

    # Source SKILL.md relative to this file: <repo>/cursor/SKILL.md
    # parents[0] = hosts/  parents[1] = runlog_install/  parents[2] = src/
    # parents[3] = python-installer/  parents[4] = runlog-skills/ (repo root)
    _SKILL_SRC: Path = Path(__file__).resolve().parents[4] / "cursor" / "SKILL.md"

    def install(self, api_key: str | None = None) -> None:
        """Write runlog.mdc to its destination (mkdir -p parent)."""
        # 1. Copy SKILL.md to SKILL_DEST (mkdir -p parent)
        skill_src = self._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: cursor/SKILL.md (expected at {skill_src})"
            )
        self.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
        self.SKILL_DEST.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

    def uninstall(self) -> None:
        """Remove runlog.mdc and clean up empty parent directory."""
        # 1. Remove SKILL_DEST; rmdir empty parent dirs
        self.SKILL_DEST.unlink(missing_ok=True)
        try:
            self.SKILL_DEST.parent.rmdir()
        except OSError:
            pass  # directory not empty or doesn't exist — leave it alone
