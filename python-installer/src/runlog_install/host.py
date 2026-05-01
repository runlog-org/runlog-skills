from pathlib import Path
from typing import Literal, Protocol


class Host(Protocol):
    """A vendor-specific install target (Claude Code, Cursor, etc.)."""

    name: str        # human-readable, e.g. "Claude Code"
    target_key: str  # CLI --target value, e.g. "claude", "cursor"
    mode: Literal["delegated", "fallback"]
    """delegated → SKILL placement only; user runs `npx add-mcp` for the MCP config edit.
    fallback → SKILL placement + JSONC merge of the MCP block into the host's config file."""

    skill_sources: list[tuple[Path, Path, str]]
    """The three Runlog skill specs as (source_path, dest_path, section_label) tuples.

    Covers the read, author, and harvest skills.  Hosts with a per-skill
    directory (e.g. claude-code, cursor) give each spec a unique dest_path;
    hosts with a single shared rules file (e.g. zed, windsurf, copilot)
    point all three specs at the same dest_path and rely on
    skill_writer.write_skills to concatenate the bodies with section
    headers derived from section_label."""

    def install(self, api_key: str | None = None) -> None:
        """Write all three SKILL files (read, author, harvest) and (for fallback
        mode) merge the MCP server block into host settings.

        api_key is only used by fallback hosts; delegated hosts ignore it.
        """
        ...

    def uninstall(self) -> None:
        """Remove the three SKILL files and (for fallback mode) the MCP server
        block from host settings."""
        ...

    def post_install_hint(self) -> str | None:
        """Optional one-line hint printed after a successful install.
        Used for host-specific manual steps the installer can't auto-wire
        (e.g. Aider's read: list — YAML list-of-strings, outside yamlc scope).
        Default: None (no hint)."""
        ...
