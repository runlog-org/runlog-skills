"""continue_host.py — Host adapter for Continue.dev.

Installs the Runlog MCP server block into ~/.continue/config.yaml and copies
the SKILL.md to ~/.continue/rules/runlog.md.

Continue 1.0+ uses YAML configuration at ~/.continue/config.yaml (global) or
.continue/config.yaml (workspace). The mcpServers key in this modern format is
a list of mappings — each with name, type, url, and requestOptions. This
adapter targets only the modern YAML config; the legacy ~/.continue/config.json
(which uses a completely different shape: an array under
experimental.modelContextProtocolServers) is deferred — it serves a different
schema and there is no current consumer demand for it.

Fallback mode: Neon's add-mcp@1.8.0 does not support Continue.dev as a target,
so this adapter writes the SKILL file and edits config.yaml directly via the
yamlc helper (surgical string-splice, comment-preserving).

(Note: the module file is named continue_host.py because "continue" is a
Python reserved word — it cannot be used as a module name.)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from runlog_install import yamlc


class ContinueHost:
    """Host adapter for Continue.dev (fallback mode — direct YAML config edit)."""

    name: str = "Continue.dev"
    target_key: str = "continue"
    mode: Literal["delegated", "fallback"] = "fallback"

    # Continue 1.0+ global rules directory: ~/.continue/rules/runlog.md
    # Source: continue/SKILL.md §Setup step 4
    SKILL_DEST: Path = Path.home() / ".continue" / "rules" / "runlog.md"

    # Continue 1.0+ modern YAML config: ~/.continue/config.yaml
    # Source: continue/SKILL.md §Setup step 3
    SETTINGS_PATH: Path = Path.home() / ".continue" / "config.yaml"

    # Source SKILL.md: <repo-root>/continue/SKILL.md
    # parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
    # [4]=runlog-skills/ (repo root). Matches WindsurfHost._SKILL_SRC pattern.
    _SKILL_SRC: Path = Path(__file__).resolve().parents[4] / "continue" / "SKILL.md"

    def install(self, api_key: str | None = None) -> None:
        """Write rules/runlog.md and merge the runlog MCP block into config.yaml.

        api_key is REQUIRED for fallback hosts — it carries the Bearer header
        written directly into config.yaml.
        """
        if api_key is None:
            raise ValueError(
                "api_key is required for ContinueHost (fallback mode): "
                "pass the user's Runlog API key so the Bearer header can be "
                "written into ~/.continue/config.yaml."
            )

        # 1. Validate source SKILL.md exists.
        skill_src = self._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: continue/SKILL.md "
                f"(expected at {skill_src})"
            )

        # 2. Copy SKILL.md to SKILL_DEST (mkdir -p parent).
        self.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
        self.SKILL_DEST.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

        # 3. Read SETTINGS_PATH (or empty string seed if missing / empty).
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else ""
        else:
            text = ""

        # 4. Build the MCP block dict matching continue/SKILL.md §Setup YAML shape.
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

        # 5. Insert / replace the runlog MCP block under "mcpServers".
        text = yamlc.add_to_list(text, "mcpServers", "name", "runlog", mcp_block)

        # 6. Write back, mode 0600.
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def post_install_hint(self) -> str | None:
        return None

    def uninstall(self) -> None:
        """Remove rules/runlog.md and the runlog MCP block from config.yaml."""
        # 1. Remove SKILL_DEST; rmdir empty parent (~/.continue/rules).
        self.SKILL_DEST.unlink(missing_ok=True)
        try:
            self.SKILL_DEST.parent.rmdir()
        except OSError:
            pass  # directory not empty or doesn't exist — leave it alone

        # 2. Read SETTINGS_PATH (skip if missing).
        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        # 3. Remove the runlog item from "mcpServers".
        text = yamlc.remove_from_list(text, "mcpServers", "name", "runlog")

        # 4. Write back.
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
