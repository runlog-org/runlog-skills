"""cursor.py — Host adapter for Cursor.

Delegated mode: copies the runlog read / author / harvest rule files to
``~/.cursor/rules/``. MCP server wiring is handled separately by the user
via ``npx add-mcp``.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from runlog_install.hosts._base import BaseHost, DelegatedMixin, SeparateFileMixin


class CursorHost(BaseHost, DelegatedMixin, SeparateFileMixin):
    """Host adapter for Cursor (delegated mode — SKILL placement only)."""

    name: ClassVar[str] = "Cursor"
    target_key: ClassVar[str] = "cursor"
    _VENDOR_KEY: ClassVar[str] = "cursor"
    SKILL_DEST: ClassVar[Path] = Path.home() / ".cursor" / "rules" / "runlog.mdc"
