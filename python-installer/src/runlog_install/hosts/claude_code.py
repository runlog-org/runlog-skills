"""
claude_code.py — ClaudeCodeHost adapter for the Runlog installer.

Delegated mode: installs the read / author / harvest SKILL.md trio under
``~/.claude/skills/``. MCP server wiring is handled separately by the user
via ``npx add-mcp``.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from runlog_install.hosts._base import BaseHost, DelegatedMixin, SeparateFileMixin


class ClaudeCodeHost(BaseHost, DelegatedMixin, SeparateFileMixin):
    """Host adapter for Claude Code (delegated mode — SKILL placement only)."""

    name: ClassVar[str] = "Claude Code"
    target_key: ClassVar[str] = "claude"
    _VENDOR_KEY: ClassVar[str] = "claude-code"
    SKILL_DEST: ClassVar[Path] = Path.home() / ".claude" / "skills" / "runlog" / "SKILL.md"

    @property
    def _RMDIR_STOP(self) -> Path:  # type: ignore[override]
        """Stop pruning empty parent dirs at ~/.claude."""
        return self.SKILL_DEST.parent.parent.parent

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Per-skill subdirs: each skill at .../skills/<skill-name>/SKILL.md."""
        skills_root = self.SKILL_DEST.parent.parent
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", skills_root / "runlog-author" / "SKILL.md", "author"),
            (src_root / "runlog-harvest.md", skills_root / "runlog-harvest" / "SKILL.md", "harvest"),
        ]
