"""zed.py — ZedHost adapter (delegated).

Installs the Runlog read / author / harvest skill bundle to the path Zed
expects for agent rules. Zed loads rules from ~/.config/zed/rules.md
(global) — see §Setup in zed/SKILL.md for the canonical reference. The
three skill bodies are concatenated into the shared rules.md with section
headers (``# === Runlog <label> skill ===``) between them. The MCP server
config is wired up by ``npx add-mcp`` (which Zed supports natively); this
adapter does not touch any Zed config file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from runlog_install import skill_writer

# Source SKILL files: <repo-root>/zed/{SKILL,runlog-author,runlog-harvest}.md
# parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
# [4]=runlog-skills/ (repo root). Matches the other host adapters.
_VENDOR_DIR = Path(__file__).resolve().parents[4] / "zed"


class ZedHost:
    """Host adapter for Zed (delegated mode — SKILL placement only)."""

    name: str = "Zed"
    target_key: str = "zed"
    mode: Literal["delegated", "fallback"] = "delegated"

    # Zed loads rules from ~/.config/zed/rules.md (global scope).
    # All three Runlog skills concatenate into this single shared file.
    SKILL_DEST: Path = Path.home() / ".config" / "zed" / "rules.md"
    _SKILL_SRC: Path = _VENDOR_DIR / "SKILL.md"

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three specs that all share the same dest_path (rules.md).

        skill_writer detects the shared destination and concatenates the
        three bodies with section headers.
        """
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", self.SKILL_DEST, "author"),
            (src_root / "runlog-harvest.md", self.SKILL_DEST, "harvest"),
        ]

    def install(self, api_key: str | None = None) -> None:
        """Write rules.md with the concatenated read / author / harvest bodies.

        api_key is ignored (delegated mode).
        """
        skill_writer.write_skills(self.skill_sources, self.name)

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove rules.md and walk up empty parent dirs (stop at ~/.config/zed)."""
        stop = Path.home() / ".config" / "zed"
        skill_writer.remove_skills(self.skill_sources, rmdir_stop=stop)
