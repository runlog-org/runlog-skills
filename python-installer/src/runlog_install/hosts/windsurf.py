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
from typing import ClassVar, Literal

from runlog_install.hosts._base import (
    BaseHost,
    FallbackMixin,
    RUNLOG_MCP_URL,
    SharedFileMixin,
)


class WindsurfHost(BaseHost, FallbackMixin, SharedFileMixin):
    """Host adapter for Windsurf (fallback mode — direct JSONC config edit)."""

    name: ClassVar[str] = "Windsurf"
    target_key: ClassVar[str] = "windsurf"
    _VENDOR_KEY: ClassVar[str] = "windsurf"

    # Windsurf global rules file under ~/.codeium/windsurf/ — the three
    # Runlog skills concatenate into this single shared file.
    SKILL_DEST: ClassVar[Path] = Path.home() / ".codeium" / "windsurf" / "globalrules"

    # Windsurf MCP config: ~/.codeium/windsurf/mcp_config.json
    # Source: windsurf/SKILL.md §Setup step 3
    SETTINGS_PATH: ClassVar[Path] = (
        Path.home() / ".codeium" / "windsurf" / "mcp_config.json"
    )

    _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"
    _TOP_LEVEL_KEY: ClassVar[str] = "mcpServers"

    def _mcp_block(self, api_key: str) -> dict:
        """Return the MCP block matching windsurf/SKILL.md §Setup JSONC shape.

        Windsurf accepts the URL-only block — no ``type:`` key required.
        """
        return {
            "url": RUNLOG_MCP_URL,
            "headers": {"Authorization": f"Bearer {api_key}"},
        }
