"""continue_host.py — Host adapter for Continue.dev.

Installs the Runlog MCP server block into ~/.continue/config.yaml and
copies the read / author / harvest skill bodies to
~/.continue/rules/runlog{,-author,-harvest}.md.

Continue 1.0+ uses YAML configuration at ~/.continue/config.yaml (global) or
.continue/config.yaml (workspace). The mcpServers key in this modern format is
a list of mappings — each with name, type, url, and requestOptions. This
adapter targets only the modern YAML config; the legacy ~/.continue/config.json
(which uses a completely different shape: an array under
experimental.modelContextProtocolServers) is deferred — it serves a different
schema and there is no current consumer demand for it.

Fallback mode: Neon's add-mcp@1.8.0 does not support Continue.dev as a target,
so this adapter writes the skill files and edits config.yaml directly via the
yamlc helper (surgical string-splice, comment-preserving).

(Note: the module file is named continue_host.py because "continue" is a
Python reserved word — it cannot be used as a module name.)
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from runlog_install.hosts._base import (
    BaseHost,
    FallbackMixin,
    RUNLOG_MCP_URL,
    SeparateFileMixin,
)


class ContinueHost(BaseHost, FallbackMixin, SeparateFileMixin):
    """Host adapter for Continue.dev (fallback mode — direct YAML config edit)."""

    name: ClassVar[str] = "Continue.dev"
    target_key: ClassVar[str] = "continue"
    _VENDOR_KEY: ClassVar[str] = "continue"

    # Continue 1.0+ global rules directory: ~/.continue/rules/runlog.md
    # Source: continue/SKILL.md §Setup step 4. Author and harvest skill
    # files sit alongside as runlog-author.md / runlog-harvest.md.
    SKILL_DEST: ClassVar[Path] = Path.home() / ".continue" / "rules" / "runlog.md"

    # Continue 1.0+ modern YAML config: ~/.continue/config.yaml
    # Source: continue/SKILL.md §Setup step 3
    SETTINGS_PATH: ClassVar[Path] = Path.home() / ".continue" / "config.yaml"

    _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "yamlc-list"

    # camelCase "mcpServers" (Continue), not kebab-case "mcp-servers" (Aider)
    _TOP_LEVEL_KEY: ClassVar[str] = "mcpServers"

    def _mcp_block(self, api_key: str) -> dict:
        """Return the MCP block matching continue/SKILL.md §Setup YAML shape.

        Note: Continue uses ``type:`` (not ``transport:``), and the auth header
        is nested under ``requestOptions.headers`` (not a flat ``headers:`` dict).
        """
        return {
            "name": "runlog",
            "type": "streamable-http",
            "url": RUNLOG_MCP_URL,
            "requestOptions": {
                "headers": {"Authorization": f"Bearer {api_key}"},
            },
        }
