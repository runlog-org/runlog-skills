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
from typing import ClassVar

from runlog_install.hosts._base import BaseHost, DelegatedMixin, SharedFileMixin


class ZedHost(BaseHost, DelegatedMixin, SharedFileMixin):
    """Host adapter for Zed (delegated mode — SKILL placement only)."""

    name: ClassVar[str] = "Zed"
    target_key: ClassVar[str] = "zed"
    _VENDOR_KEY: ClassVar[str] = "zed"
    SKILL_DEST: ClassVar[Path] = Path.home() / ".config" / "zed" / "rules.md"

    @property
    def _RMDIR_STOP(self) -> Path:  # type: ignore[override]
        """Stop pruning empty parent dirs at ~/.config/zed (the Zed config dir)."""
        return self.SKILL_DEST.parent
