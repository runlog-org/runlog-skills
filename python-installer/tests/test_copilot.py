"""Tests for CopilotHost."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runlog_install.hosts.copilot import CopilotHost


# ---------------------------------------------------------------------------
# 1. install writes SKILL (copilot-instructions.md)
# ---------------------------------------------------------------------------

def test_install_writes_skill(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )
    host.install(api_key="sk-runlog-testkey")

    assert host.SKILL_DEST.is_file(), "copilot-instructions.md should be created"
    assert host.SKILL_DEST.stat().st_size > 0


# ---------------------------------------------------------------------------
# 2. install writes MCP block with correct type, URL + Bearer header
# ---------------------------------------------------------------------------

def test_install_writes_mcp_block(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )
    api_key = "sk-runlog-abc123xyz"
    host.install(api_key=api_key)

    assert host.SETTINGS_PATH.exists(), "mcp.json should be created"
    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["servers"], "runlog key must exist under servers"
    block = data["servers"]["runlog"]
    assert block["type"] == "http"
    assert block["url"] == "https://api.runlog.org/mcp"
    assert block["headers"]["Authorization"] == f"Bearer {api_key}"


# ---------------------------------------------------------------------------
# 3. install preserves sibling MCP servers
# ---------------------------------------------------------------------------

def test_install_preserves_sibling_mcp_servers(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )

    # Pre-populate mcp.json with a sibling server.
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(
        json.dumps({
            "servers": {
                "other-tool": {"type": "http", "url": "https://other.example.com/mcp"}
            }
        }),
        encoding="utf-8",
    )

    host.install(api_key="sk-runlog-testkey")

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["servers"], "runlog block must be present"
    assert "other-tool" in data["servers"], "sibling entry must be preserved"


# ---------------------------------------------------------------------------
# 4. install is idempotent — installing twice produces no duplicate
# ---------------------------------------------------------------------------

def test_install_idempotent(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )

    host.install(api_key="sk-runlog-first")
    host.install(api_key="sk-runlog-second")

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["servers"]

    # "runlog" key should appear exactly once in the raw file.
    raw = host.SETTINGS_PATH.read_text()
    assert raw.count('"runlog"') == 1, 'duplicate "runlog" key found'

    # Authorization should reflect the latest key.
    auth = data["servers"]["runlog"]["headers"]["Authorization"]
    assert auth == "Bearer sk-runlog-second"


# ---------------------------------------------------------------------------
# 5. install(api_key=None) raises ValueError
# ---------------------------------------------------------------------------

def test_install_requires_api_key(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )
    with pytest.raises(ValueError):
        host.install(api_key=None)


# ---------------------------------------------------------------------------
# 6. install preserves pre-existing JSONC comments
# ---------------------------------------------------------------------------

def test_install_preserves_jsonc_comments(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )

    # Write a mcp.json that contains JSONC comments.
    jsonc_text = (
        '{\n'
        '  // keep this comment\n'
        '  "servers": {\n'
        '    /* block comment */\n'
        '    "existing": { "type": "http", "url": "https://existing.example.com/mcp" }\n'
        '  }\n'
        '}\n'
    )
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(jsonc_text, encoding="utf-8")

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text()
    assert "// keep this comment" in raw, "JSONC line comment must be preserved"
    assert "/* block comment */" in raw, "JSONC block comment must be preserved"

    # File must still be parseable as plain JSON after stripping comments.
    from runlog_install import jsonc as _jsonc
    data = _jsonc.parse(raw)
    assert "runlog" in data["servers"]
    assert "existing" in data["servers"]


# ---------------------------------------------------------------------------
# 7. uninstall removes SKILL file and MCP block
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill_and_mcp_block(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )
    host.install(api_key="sk-runlog-testkey")

    # Add a sibling so the file is not left empty.
    data = json.loads(host.SETTINGS_PATH.read_text())
    data["servers"]["sibling"] = {"type": "http", "url": "https://sibling.example.com/mcp"}
    host.SETTINGS_PATH.write_text(json.dumps(data), encoding="utf-8")

    host.uninstall()

    assert not host.SKILL_DEST.exists(), "copilot-instructions.md should be removed"
    remaining = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" not in remaining.get("servers", {}), "runlog block must be gone"
    assert "sibling" in remaining.get("servers", {}), "sibling must remain"


# ---------------------------------------------------------------------------
# 8. uninstall when nothing installed is a no-op
# ---------------------------------------------------------------------------

def test_uninstall_missing_is_noop(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )
    # Should not raise even when no files exist.
    host.uninstall()
    host.uninstall()
    assert not host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# 9. mode attribute is "fallback"
# ---------------------------------------------------------------------------

def test_mode_attribute(make_host, tmp_path):
    host = make_host(
        CopilotHost,
        skill_dest=tmp_path / ".github" / "copilot-instructions.md",
        settings_path=tmp_path / ".config" / "Code" / "User" / "mcp.json",
    )
    assert host.mode == "fallback"


# ---------------------------------------------------------------------------
# 10. platform path branching — Linux vs macOS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("platform,expected_fragment", [
    ("linux", ".config/Code/User/mcp.json"),
    ("darwin", "Library/Application Support/Code/User/mcp.json"),
])
def test_platform_path_branch(monkeypatch, tmp_path, platform, expected_fragment):
    """_vscode_user_dir() returns the correct path for each supported platform."""
    from runlog_install.hosts import copilot as copilot_module

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(copilot_module.sys, "platform", platform)

    resolved = copilot_module._vscode_user_dir() / "mcp.json"
    assert expected_fragment in str(resolved), (
        f"Expected path fragment {expected_fragment!r} in {resolved!s}"
    )
