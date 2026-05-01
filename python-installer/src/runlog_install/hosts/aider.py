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
from typing import Literal

from runlog_install import skill_writer, yamlc

# Source SKILL files: <repo-root>/aider/{SKILL,runlog-author,runlog-harvest}.md
# parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
# [4]=runlog-skills/ (repo root).
_VENDOR_DIR = Path(__file__).resolve().parents[4] / "aider"


class AiderHost:
    """Host adapter for Aider (fallback mode — direct YAML config edit)."""

    name: str = "Aider"
    target_key: str = "aider"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Read-skill destination (Pattern B install). The author and harvest
    # skill files sit alongside it in ~/.aider/.
    SKILL_DEST: Path = Path.home() / ".aider" / "runlog.md"

    # Aider global config: ~/.aider.conf.yml
    # Source: aider/SKILL.md §Setup step 3
    SETTINGS_PATH: Path = Path.home() / ".aider.conf.yml"

    _SKILL_SRC: Path = _VENDOR_DIR / "SKILL.md"

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three specs — read / author / harvest — under ~/.aider/."""
        aider_dir = self.SKILL_DEST.parent  # ~/.aider/
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", aider_dir / "runlog-author.md", "author"),
            (src_root / "runlog-harvest.md", aider_dir / "runlog-harvest.md", "harvest"),
        ]

    def install(self, api_key: str | None = None) -> None:
        """Write the three ~/.aider/runlog*.md skill files and merge the
        runlog MCP block into ~/.aider.conf.yml.

        api_key is REQUIRED for fallback hosts — it carries the Bearer header
        written directly into the config file.

        Note: The Aider ``read:`` list is NOT auto-wired by this method.
        Aider's ``read:`` block is a YAML list-of-strings, outside the scope of
        the yamlc helper (which handles list-of-dicts).  After install, add the
        following to ``~/.aider.conf.yml`` manually:

            read:
              - ~/.aider/runlog.md
              - ~/.aider/runlog-author.md
              - ~/.aider/runlog-harvest.md

        A one-line hint for this step is printed by the CLI after install.
        """
        if api_key is None:
            raise ValueError(
                "api_key is required for AiderHost (fallback mode): "
                "pass the user's Runlog API key so the Bearer header can be "
                "written into ~/.aider.conf.yml."
            )

        # 1. Write the three skill files into ~/.aider/.
        skill_writer.write_skills(self.skill_sources, self.name)

        # 2. Read SETTINGS_PATH (seed with empty string if missing).
        if self.SETTINGS_PATH.exists():
            text = self.SETTINGS_PATH.read_text(encoding="utf-8")
        else:
            text = ""

        # 3. Build the MCP block matching aider/SKILL.md §Setup YAML shape.
        #    Note: Aider uses `transport:` (not `type:`) and a flat `headers:`
        #    dict (not Continue's nested requestOptions.headers).
        mcp_block = {
            "name": "runlog",
            "transport": "streamable-http",
            "url": "https://api.runlog.org/mcp",
            "headers": {
                "Authorization": f"Bearer {api_key}",
            },
        }

        # 4. Insert / replace the runlog item in the mcp-servers list.
        #    Key is kebab-case "mcp-servers" (Aider), not camelCase "mcpServers" (Continue).
        text = yamlc.add_to_list(text, "mcp-servers", "name", "runlog", mcp_block)

        # 5. Write back, mode 0600 (contains Bearer token).
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def post_install_hint(self) -> str | None:
        return (
            "Aider note: add the three Runlog skill files (`~/.aider/runlog.md`, "
            "`~/.aider/runlog-author.md`, `~/.aider/runlog-harvest.md`) to the "
            "`read:` list in `~/.aider.conf.yml` so Aider auto-loads them."
        )

    def uninstall(self) -> None:
        """Remove the three ~/.aider/runlog*.md files and the runlog MCP block
        from ~/.aider.conf.yml."""
        # 1. Remove all three skill files; rmdir empty ~/.aider parent.
        skill_writer.remove_skills(self.skill_sources)

        # 2. Read SETTINGS_PATH (skip if missing).
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog item from the mcp-servers list.
        text = yamlc.remove_from_list(text, "mcp-servers", "name", "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
