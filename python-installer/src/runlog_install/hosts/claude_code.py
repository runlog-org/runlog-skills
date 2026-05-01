"""
claude_code.py — ClaudeCodeHost adapter for the Runlog installer.

Delegated mode: installs only the SKILL.md file. MCP server wiring is
handled separately by the user via `npx add-mcp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal


class ClaudeCodeHost:
    name = "Claude Code"
    target_key = "claude"
    mode: Literal["delegated", "fallback"] = "delegated"

    SKILL_DEST = Path.home() / ".claude" / "skills" / "runlog" / "SKILL.md"

    # Source SKILL.md: lives at <repo-root>/claude-code/SKILL.md.
    # When installed via `pip install -e python-installer/` from inside the
    # runlog-skills repo, __file__ resolves to:
    #   <repo-root>/python-installer/src/runlog_install/hosts/claude_code.py
    # parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
    # [4]=runlog-skills/ (repo root). Matches CursorHost._SKILL_SRC.
    _SKILL_SRC = (
        Path(__file__).resolve().parents[4] / "claude-code" / "SKILL.md"
    )

    # ------------------------------------------------------------------
    # install
    # ------------------------------------------------------------------

    def install(self, api_key: str | None = None) -> None:
        """Write SKILL.md to its destination (mkdir -p parent)."""
        skill_dest = self.SKILL_DEST

        # 1. Validate source SKILL.md exists.
        skill_src = self._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: claude-code/SKILL.md "
                f"(expected at {skill_src})"
            )

        # 2. Copy SKILL.md to destination (mkdir -p parent).
        skill_dest.parent.mkdir(parents=True, exist_ok=True)
        skill_dest.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

    # ------------------------------------------------------------------
    # uninstall
    # ------------------------------------------------------------------

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove SKILL.md and clean up empty parent directories."""
        skill_dest = self.SKILL_DEST

        # 1. Remove SKILL.md; clean up empty parent dirs.
        skill_dest.unlink(missing_ok=True)
        # Walk up through parent dirs, removing each if empty (stop at ~/.claude).
        stop = Path.home() / ".claude"
        parent = skill_dest.parent
        while parent != stop and parent != parent.parent:
            try:
                parent.rmdir()  # only succeeds if empty
            except OSError:
                break
            parent = parent.parent
