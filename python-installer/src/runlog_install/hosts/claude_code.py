"""
claude_code.py — ClaudeCodeHost adapter for the Runlog installer.

Delegated mode: installs the read / author / harvest SKILL.md trio under
``~/.claude/skills/``. MCP server wiring is handled separately by the user
via ``npx add-mcp``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from runlog_install import skill_writer

# Source SKILL files: <repo-root>/claude-code/{SKILL,runlog-author,runlog-harvest}.md.
# When installed via `pip install -e python-installer/` from inside the
# runlog-skills repo, __file__ resolves to:
#   <repo-root>/python-installer/src/runlog_install/hosts/claude_code.py
# parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
# [4]=runlog-skills/ (repo root). Matches the other host adapters.
_VENDOR_DIR = Path(__file__).resolve().parents[4] / "claude-code"


class ClaudeCodeHost:
    name = "Claude Code"
    target_key = "claude"
    mode: Literal["delegated", "fallback"] = "delegated"

    # Read-skill destination + source. Kept as named attributes for
    # back-compat with the make_host fixture (which monkeypatches them) and
    # for clarity in the per-vendor target table.
    SKILL_DEST: Path = Path.home() / ".claude" / "skills" / "runlog" / "SKILL.md"
    _SKILL_SRC: Path = _VENDOR_DIR / "SKILL.md"

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three (source, dest, label) specs covering read / author / harvest.

        Derived dynamically from SKILL_DEST and _SKILL_SRC so the make_host
        fixture's monkeypatches transparently redirect every dest under
        tmp_path. The author and harvest sources live alongside the read
        source in the same vendor directory.
        """
        skills_root = self.SKILL_DEST.parent.parent  # .../skills/
        src_root = self._SKILL_SRC.parent             # .../claude-code/ (or fixture dir)
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", skills_root / "runlog-author" / "SKILL.md", "author"),
            (src_root / "runlog-harvest.md", skills_root / "runlog-harvest" / "SKILL.md", "harvest"),
        ]

    # ------------------------------------------------------------------
    # install
    # ------------------------------------------------------------------

    def install(self, api_key: str | None = None) -> None:
        """Write the read, author, and harvest SKILL files."""
        skill_writer.write_skills(self.skill_sources, self.name)

    # ------------------------------------------------------------------
    # uninstall
    # ------------------------------------------------------------------

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove all three SKILL files and clean up empty parent directories
        (stopping at ``~/.claude``)."""
        stop = Path.home() / ".claude"
        skill_writer.remove_skills(self.skill_sources, rmdir_stop=stop)
