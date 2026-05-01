"""Registry of host adapters keyed by --target value."""

from runlog_install.hosts.claude_code import ClaudeCodeHost
from runlog_install.hosts.copilot import CopilotHost
from runlog_install.hosts.cursor import CursorHost
from runlog_install.hosts.windsurf import WindsurfHost
from runlog_install.hosts.zed import ZedHost

HOSTS: dict[str, type] = {
    "claude": ClaudeCodeHost,
    "copilot": CopilotHost,
    "cursor": CursorHost,
    "windsurf": WindsurfHost,
    "zed": ZedHost,
}
