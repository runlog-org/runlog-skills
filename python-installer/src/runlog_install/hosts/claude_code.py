"""
claude_code.py — ClaudeCodeHost adapter for the Runlog installer.

Installs the Runlog skill and MCP server config for Claude Code.
"""

from __future__ import annotations

from pathlib import Path

from runlog_install import jsonc


class ClaudeCodeHost:
    name = "Claude Code"
    target_key = "claude"

    SKILL_DEST = Path.home() / ".claude" / "skills" / "runlog" / "SKILL.md"
    SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

    # Source SKILL.md: lives at <repo-root>/claude-code/SKILL.md.
    # When installed via `pip install -e python-installer/` from inside the
    # runlog-skills repo, __file__ resolves to:
    #   <repo-root>/python-installer/src/runlog_install/hosts/claude_code.py
    # parents[0]=hosts/  [1]=runlog_install/  [2]=src/  [3]=python-installer/
    # [4]=runlog-skills/ (repo root). Matches CursorHost._SKILL_SRC.
    _SKILL_SRC = (
        Path(__file__).resolve().parents[4] / "claude-code" / "SKILL.md"
    )

    # ------------------------------------------------------------------
    # install
    # ------------------------------------------------------------------

    def install(self, api_key: str) -> None:
        """Write SKILL.md and merge the runlog MCP block into settings.json."""
        skill_dest = type(self).SKILL_DEST
        settings_path = type(self).SETTINGS_PATH

        # 1. Validate source SKILL.md exists.
        skill_src = type(self)._SKILL_SRC
        if not skill_src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found: claude-code/SKILL.md "
                f"(expected at {skill_src})"
            )

        # 2. Copy SKILL.md to destination (mkdir -p parent).
        skill_dest.parent.mkdir(parents=True, exist_ok=True)
        skill_dest.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")

        # 3. Read existing settings.json, or seed with a minimal structure.
        # We seed with mcpServers already present to avoid a spurious leading
        # comma that jsonc.add_to_object produces when bootstrapping a missing
        # top-level key into a completely empty "{}". Mirrors CursorHost.
        _SEED = '{\n  "mcpServers": {}\n}'
        if settings_path.is_file():
            raw = settings_path.read_text(encoding="utf-8").strip()
            text = raw if raw else _SEED
        else:
            text = _SEED

        # 4. Build the MCP block value.
        mcp_block = {
            "type": "http",
            "url": "https://api.runlog.org/mcp",
            "headers": {
                "Authorization": f"Bearer {api_key}",
            },
        }

        # 5. Merge into settings via JSONC helper.
        text = jsonc.add_to_object(text, ("mcpServers",), "runlog", mcp_block)

        # 6. Write back with mode 0600.
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(text, encoding="utf-8")
        settings_path.chmod(0o600)

    # ------------------------------------------------------------------
    # uninstall
    # ------------------------------------------------------------------

    def uninstall(self) -> None:
        """Remove SKILL.md and the runlog MCP block from settings.json."""
        skill_dest = type(self).SKILL_DEST
        settings_path = type(self).SETTINGS_PATH

        # 1. Remove SKILL.md; clean up empty parent dirs.
        skill_dest.unlink(missing_ok=True)
        # Walk up through parent dirs, removing each if empty (stop at ~/.claude).
        stop = Path.home() / ".claude"
        parent = skill_dest.parent
        while parent != stop and parent != parent.parent:
            try:
                parent.rmdir()  # only succeeds if empty
            except OSError:
                break
            parent = parent.parent

        # 2. Skip if settings.json is missing.
        if not settings_path.is_file():
            return

        # 3. Remove runlog key from mcpServers.
        text = settings_path.read_text(encoding="utf-8")
        text = jsonc.remove_from_object(text, ("mcpServers",), "runlog")

        # 4. Write back.
        settings_path.write_text(text, encoding="utf-8")
