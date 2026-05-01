"""aider.py — Host adapter for Aider (aider-chat).

Installs the Runlog read / author / harvest skill bodies under
``~/.aider/`` (Pattern B — separate files referenced via ``--read``) and
merges the runlog MCP server block into ``~/.aider.conf.yml`` under the
``mcp-servers:`` list via the yamlc helper.

Target paths:
  Read skill:     ~/.aider/runlog.md
  Author skill:   ~/.aider/runlog-author.md
  Harvest skill:  ~/.aider/runlog-harvest.md
  MCP config:     ~/.aider.conf.yml

Install pattern:
  Pattern B is chosen over Pattern A (CONVENTIONS.md append) because it does
  not pollute the team-shared CONVENTIONS.md and is cleanly reversible by
  ``uninstall``.

``read:`` auto-wiring is intentionally skipped:
  Aider's ``read:`` block is a YAML list-of-strings, while yamlc operates on
  list-of-dicts.  After install the user must add the three skill paths to
  their ``read:`` list manually:

      read:
        - ~/.aider/runlog.md
        - ~/.aider/runlog-author.md
        - ~/.aider/runlog-harvest.md

  A one-line CLI hint for this is emitted by the CLI.

Fallback mode:
  ``add-mcp@1.8.0`` does not support Aider, so this adapter writes the skill
  files and edits the MCP config directly via the yamlc YAML helper.
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


class AiderHost(BaseHost, FallbackMixin, SeparateFileMixin):
    """Host adapter for Aider (fallback mode — direct YAML config edit)."""

    name: ClassVar[str] = "Aider"
    target_key: ClassVar[str] = "aider"
    _VENDOR_KEY: ClassVar[str] = "aider"

    # Read-skill destination (Pattern B install). The author and harvest
    # skill files sit alongside it in ~/.aider/.
    SKILL_DEST: ClassVar[Path] = Path.home() / ".aider" / "runlog.md"

    # Aider global config: ~/.aider.conf.yml
    # Source: aider/SKILL.md §Setup step 3
    SETTINGS_PATH: ClassVar[Path] = Path.home() / ".aider.conf.yml"

    _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "yamlc-list"

    # Aider uses kebab-case "mcp-servers" (not camelCase "mcpServers")
    _TOP_LEVEL_KEY: ClassVar[str] = "mcp-servers"

    def _mcp_block(self, api_key: str) -> dict:
        """Return the MCP block matching aider/SKILL.md §Setup YAML shape.

        Note: Aider uses ``transport:`` (not ``type:``) and a flat ``headers:``
        dict (not Continue's nested requestOptions.headers).
        """
        return {
            "name": "runlog",
            "transport": "streamable-http",
            "url": RUNLOG_MCP_URL,
            "headers": {"Authorization": f"Bearer {api_key}"},
        }

    def post_install_hint(self) -> str | None:
        return (
            "Aider note: add the three Runlog skill files (`~/.aider/runlog.md`, "
            "`~/.aider/runlog-author.md`, `~/.aider/runlog-harvest.md`) to the "
            "`read:` list in `~/.aider.conf.yml` so Aider auto-loads them."
        )
