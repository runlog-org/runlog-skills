from typing import Protocol


class Host(Protocol):
    """A vendor-specific install target (Claude Code, Cursor, etc.)."""

    name: str        # human-readable, e.g. "Claude Code"
    target_key: str  # CLI --target value, e.g. "claude", "cursor"

    def install(self, api_key: str) -> None:
        """Write SKILL file, merge MCP server block into host settings."""
        ...

    def uninstall(self) -> None:
        """Remove SKILL file, surgically remove MCP server block from host settings."""
        ...
