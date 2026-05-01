"""aider.py — Host adapter for Aider (aider-chat).

Installs the Runlog skill body to ~/.aider/runlog.md (Pattern B — separate
file referenced via ``--read``) and merges the runlog MCP server block into
~/.aider.conf.yml under the ``mcp-servers:`` list via the yamlc helper.

Target paths:
  Skill file:   ~/.aider/runlog.md
  MCP config:   ~/.aider.conf.yml

Install pattern:
  Pattern B is chosen over Pattern A (CONVENTIONS.md append) because it does
  not pollute the team-shared CONVENTIONS.md and is cleanly reversible by
  ``uninstall``.

``read:`` auto-wiring is intentionally skipped:
  Aider's ``read:`` block is a YAML list-of-strings, while yamlc operates on
  list-of-dicts.  Extending yamlc for a single list-of-strings case would
  inflate the helper for marginal benefit.  After install the user must add
  the skill path to their ``read:`` list manually:

      read:
        - ~/.aider/runlog.md

  A one-line CLI hint for this is emitted by the CLI (Task 4 / T4).

Fallback mode:
  ``add-mcp@1.8.0`` does not support Aider, so this adapter writes the skill
  file and edits the MCP config directly via the yamlc YAML helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from runlog_install import yamlc


class AiderHost:
    """Host adapter for Aider (fallback mode — direct YAML config edit)."""

    name: str = "Aider"
    target_key: str = "aider"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Aider skill file: ~/.aider/runlog.md (Pattern B install)
    SKILL_DEST: Path = Path.home() / ".aider" / "runlog.md"

    # Aider global config: ~/.aider.conf.yml
    # Source: aider/SKILL.md §Setup step 3
    SETTINGS_PATH: Path = Path.home() / ".aider.conf.yml"

    # Source SKILL.md: <repo-root>/aider/SKILL.md
    # parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
    # [4]=runlog-skills/ (repo root). Matches WindsurfHost._SKILL_SRC pattern.
    _SKILL_SRC: Path = Path(__file__).resolve().parents[4] / "aider" / "SKILL.md"

    def install(self, api_key: str | None = None) -> None:
        """Write ~/.aider/runlog.md and merge the runlog MCP block into ~/.aider.conf.yml.

        api_key is REQUIRED for fallback hosts — it carries the Bearer header
        written directly into the config file.

        Note: The Aider ``read:`` list is NOT auto-wired by this method.
        Aider's ``read:`` block is a YAML list-of-strings, outside the scope of
        the yamlc helper (which handles list-of-dicts).  After install, add the
        following to ``~/.aider.conf.yml`` manually:

            read:
              - ~/.aider/runlog.md

        A one-line hint for this step is printed by the CLI after install.
        """
        if api_key is None:
            raise ValueError(
                "api_key is required for AiderHost (fallback mode): "
                "pass the user's Runlog API key so the Bearer header can be "
                "written into ~/.aider.conf.yml."
            )

        # 1. Validate source SKILL.md exists.
        skill_src = self._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: aider/SKILL.md "
                f"(expected at {skill_src})"
            )

        # 2. Copy SKILL.md to SKILL_DEST (mkdir -p parent).
        self.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
        self.SKILL_DEST.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

        # 3. Read SETTINGS_PATH (seed with empty string if missing).
        if self.SETTINGS_PATH.exists():
            text = self.SETTINGS_PATH.read_text(encoding="utf-8")
        else:
            text = ""

        # 4. Build the MCP block matching aider/SKILL.md §Setup YAML shape.
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

        # 5. Insert / replace the runlog item in the mcp-servers list.
        #    Key is kebab-case "mcp-servers" (Aider), not camelCase "mcpServers" (Continue).
        text = yamlc.add_to_list(text, "mcp-servers", "name", "runlog", mcp_block)

        # 6. Write back, mode 0600 (contains Bearer token).
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def post_install_hint(self) -> str | None:
        return (
            "Aider note: add `~/.aider/runlog.md` to the `read:` list in "
            "`~/.aider.conf.yml` so Aider auto-loads the skill."
        )

    def uninstall(self) -> None:
        """Remove ~/.aider/runlog.md and the runlog MCP block from ~/.aider.conf.yml."""
        # 1. Remove SKILL_DEST; try to rmdir empty ~/.aider parent.
        self.SKILL_DEST.unlink(missing_ok=True)
        try:
            self.SKILL_DEST.parent.rmdir()
        except OSError:
            pass  # directory not empty or doesn't exist — leave it alone

        # 2. Read SETTINGS_PATH (skip if missing).
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog item from the mcp-servers list.
        text = yamlc.remove_from_list(text, "mcp-servers", "name", "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
