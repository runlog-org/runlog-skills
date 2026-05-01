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
from typing import Literal

from runlog_install import skill_writer, yamlc

# Source SKILL files: <repo-root>/continue/{SKILL,runlog-author,runlog-harvest}.md
# parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
# [4]=runlog-skills/ (repo root).
_VENDOR_DIR = Path(__file__).resolve().parents[4] / "continue"


class ContinueHost:
    """Host adapter for Continue.dev (fallback mode — direct YAML config edit)."""

    name: str = "Continue.dev"
    target_key: str = "continue"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Continue 1.0+ global rules directory: ~/.continue/rules/runlog.md
    # Source: continue/SKILL.md §Setup step 4. Author and harvest skill
    # files sit alongside as runlog-author.md / runlog-harvest.md.
    SKILL_DEST: Path = Path.home() / ".continue" / "rules" / "runlog.md"

    # Continue 1.0+ modern YAML config: ~/.continue/config.yaml
    # Source: continue/SKILL.md §Setup step 3
    SETTINGS_PATH: Path = Path.home() / ".continue" / "config.yaml"

    _SKILL_SRC: Path = _VENDOR_DIR / "SKILL.md"

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three specs — read / author / harvest — under ~/.continue/rules/."""
        rules_dir = self.SKILL_DEST.parent  # ~/.continue/rules/
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", rules_dir / "runlog-author.md", "author"),
            (src_root / "runlog-harvest.md", rules_dir / "runlog-harvest.md", "harvest"),
        ]

    def install(self, api_key: str | None = None) -> None:
        """Write rules/runlog{,-author,-harvest}.md and merge the runlog MCP
        block into config.yaml.

        api_key is REQUIRED for fallback hosts — it carries the Bearer header
        written directly into config.yaml.
        """
        if api_key is None:
            raise ValueError(
                "api_key is required for ContinueHost (fallback mode): "
                "pass the user's Runlog API key so the Bearer header can be "
                "written into ~/.continue/config.yaml."
            )

        # 1. Write the three rule files into ~/.continue/rules/.
        skill_writer.write_skills(self.skill_sources, self.name)

        # 2. Read SETTINGS_PATH (or empty string seed if missing / empty).
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else ""
        else:
            text = ""

        # 3. Build the MCP block dict matching continue/SKILL.md §Setup YAML shape.
        mcp_block = {
            "name": "runlog",
            "type": "streamable-http",
            "url": "https://api.runlog.org/mcp",
            "requestOptions": {
                "headers": {
                    "Authorization": f"Bearer {api_key}",
                },
            },
        }

        # 4. Insert / replace the runlog MCP block under "mcpServers".
        text = yamlc.add_to_list(text, "mcpServers", "name", "runlog", mcp_block)

        # 5. Write back, mode 0600.
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove the three rule files and the runlog MCP block from config.yaml."""
        # 1. Remove all three skill files; rmdir empty ~/.continue/rules parent.
        skill_writer.remove_skills(self.skill_sources)

        # 2. Read SETTINGS_PATH (skip if missing).
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog item from "mcpServers".
        text = yamlc.remove_from_list(text, "mcpServers", "name", "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
