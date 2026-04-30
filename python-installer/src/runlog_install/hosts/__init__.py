"""Registry of host adapters keyed by --target value."""

from runlog_install.hosts.claude_code import ClaudeCodeHost
from runlog_install.hosts.cursor import CursorHost

HOSTS: dict[str, type] = {
    "claude": ClaudeCodeHost,
    "cursor": CursorHost,
}
