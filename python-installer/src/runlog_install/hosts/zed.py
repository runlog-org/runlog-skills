"""zed.py — ZedHost adapter (delegated).

Installs the Runlog SKILL to the path Zed expects for agent rules.
Zed loads rules from ~/.config/zed/rules.md (global) — see §Setup in
zed/SKILL.md for the canonical reference. The MCP server config is
wired up by `npx add-mcp` (which Zed supports natively); this adapter
does not touch any Zed config file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal


class ZedHost:
    """Host adapter for Zed (delegated mode — SKILL placement only)."""

    name: str = "Zed"
    target_key: str = "zed"
    mode: Literal["delegated", "fallback"] = "delegated"

    # Zed loads rules from ~/.config/zed/rules.md (global scope).
    # Source: zed/SKILL.md §Setup step 4:
    #   "Or global: mkdir -p ~/.config/zed && cp skills/zed/SKILL.md ~/.config/zed/rules.md"
    SKILL_DEST: Path = Path.home() / ".config" / "zed" / "rules.md"

    # Source SKILL.md: <repo-root>/zed/SKILL.md
    # parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
    # [4]=runlog-skills/ (repo root). Matches ClaudeCodeHost._SKILL_SRC pattern.
    _SKILL_SRC: Path = Path(__file__).resolve().parents[4] / "zed" / "SKILL.md"

    def install(self, api_key: str | None = None) -> None:
        """Write SKILL.md to rules.md destination (api_key ignored — delegated mode)."""
        if not self._SKILL_SRC.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: zed/SKILL.md (expected at {self._SKILL_SRC})"
            )
        self.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
        self.SKILL_DEST.write_text(
            self._SKILL_SRC.read_text(encoding="utf-8"), encoding="utf-8"
        )

    def uninstall(self) -> None:
        """Remove rules.md and walk up empty parent dirs (stop at ~/.config/zed)."""
        self.SKILL_DEST.unlink(missing_ok=True)
        stop = Path.home() / ".config" / "zed"
        parent = self.SKILL_DEST.parent
        while parent != stop and parent != parent.parent:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
