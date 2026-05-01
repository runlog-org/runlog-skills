from typing import Literal, Protocol


class Host(Protocol):
    """A vendor-specific install target (Claude Code, Cursor, etc.)."""

    name: str        # human-readable, e.g. "Claude Code"
    target_key: str  # CLI --target value, e.g. "claude", "cursor"
    mode: Literal["delegated", "fallback"]
    """delegated → SKILL placement only; user runs `npx add-mcp` for the MCP config edit.
    fallback → SKILL placement + JSONC merge of the MCP block into the host's config file."""

    def install(self, api_key: str | None = None) -> None:
        """Write SKILL file and (for fallback mode) merge MCP server block into host settings.

        api_key is only used by fallback hosts; delegated hosts ignore it.
        """
        ...

    def uninstall(self) -> None:
        """Remove SKILL file and (for fallback mode) MCP server block from host settings."""
        ...

    def post_install_hint(self) -> str | None:
        """Optional one-line hint printed after a successful install.
        Used for host-specific manual steps the installer can't auto-wire
        (e.g. Aider's read: list — YAML list-of-strings, outside yamlc scope).
        Default: None (no hint)."""
        ...
