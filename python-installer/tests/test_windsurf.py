"""Tests for WindsurfHost."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runlog_install.hosts.windsurf import WindsurfHost


# ---------------------------------------------------------------------------
# 1. install writes SKILL (globalrules)
# ---------------------------------------------------------------------------

def test_install_writes_skill(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )
    host.install(api_key="sk-runlog-testkey")

    assert host.SKILL_DEST.is_file(), "globalrules should be created"
    assert host.SKILL_DEST.stat().st_size > 0


# ---------------------------------------------------------------------------
# 2. install writes MCP block with correct URL + Bearer header
# ---------------------------------------------------------------------------

def test_install_writes_mcp_block(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )
    api_key = "sk-runlog-abc123xyz"
    host.install(api_key=api_key)

    assert host.SETTINGS_PATH.exists(), "mcp_config.json should be created"
    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["mcpServers"], "runlog key must exist under mcpServers"
    block = data["mcpServers"]["runlog"]
    assert block["url"] == "https://api.runlog.org/mcp"
    assert block["headers"]["Authorization"] == f"Bearer {api_key}"


# ---------------------------------------------------------------------------
# 3. install preserves sibling MCP servers
# ---------------------------------------------------------------------------

def test_install_preserves_sibling_mcp_servers(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )

    # Pre-populate mcp_config.json with a sibling server.
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(
        json.dumps({
            "mcpServers": {
                "other-tool": {"url": "https://other.example.com/mcp"}
            }
        }),
        encoding="utf-8",
    )

    host.install(api_key="sk-runlog-testkey")

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["mcpServers"], "runlog block must be present"
    assert "other-tool" in data["mcpServers"], "sibling entry must be preserved"


# ---------------------------------------------------------------------------
# 4. install is idempotent — installing twice produces no duplicate
# ---------------------------------------------------------------------------

def test_install_idempotent(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )

    host.install(api_key="sk-runlog-first")
    host.install(api_key="sk-runlog-second")

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["mcpServers"]

    # "runlog" key should appear exactly once in the raw file.
    raw = host.SETTINGS_PATH.read_text()
    assert raw.count('"runlog"') == 1, 'duplicate "runlog" key found'

    # Authorization should reflect the latest key.
    auth = data["mcpServers"]["runlog"]["headers"]["Authorization"]
    assert auth == "Bearer sk-runlog-second"


# ---------------------------------------------------------------------------
# 5. install(api_key=None) raises ValueError
# ---------------------------------------------------------------------------

def test_install_requires_api_key(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )
    with pytest.raises(ValueError):
        host.install(api_key=None)


# ---------------------------------------------------------------------------
# 6. install preserves pre-existing JSONC comments
# ---------------------------------------------------------------------------

def test_install_preserves_jsonc_comments(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )

    # Write a mcp_config.json that contains JSONC comments.
    jsonc_text = (
        '{\n'
        '  // keep this comment\n'
        '  "mcpServers": {\n'
        '    /* block comment */\n'
        '    "existing": { "url": "https://existing.example.com/mcp" }\n'
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
    assert "runlog" in data["mcpServers"]
    assert "existing" in data["mcpServers"]


# ---------------------------------------------------------------------------
# 7. uninstall removes SKILL file and MCP block
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill_and_mcp_block(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )
    host.install(api_key="sk-runlog-testkey")

    # Add a sibling so the file is not left empty.
    data = json.loads(host.SETTINGS_PATH.read_text())
    data["mcpServers"]["sibling"] = {"url": "https://sibling.example.com/mcp"}
    host.SETTINGS_PATH.write_text(json.dumps(data), encoding="utf-8")

    host.uninstall()

    assert not host.SKILL_DEST.exists(), "globalrules should be removed"
    remaining = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" not in remaining.get("mcpServers", {}), "runlog block must be gone"
    assert "sibling" in remaining.get("mcpServers", {}), "sibling must remain"


# ---------------------------------------------------------------------------
# 8. uninstall when nothing installed is a no-op
# ---------------------------------------------------------------------------

def test_uninstall_missing_is_noop(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
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
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )
    assert host.mode == "fallback"


# ---------------------------------------------------------------------------
# 10. install concatenates all three skill sections into globalrules
# ---------------------------------------------------------------------------

def test_install_concatenates_three_skill_sections(make_host, tmp_path):
    host = make_host(
        WindsurfHost,
        skill_dest=tmp_path / ".codeium" / "windsurf" / "globalrules",
        settings_path=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
    )
    host.install(api_key="sk-runlog-testkey")

    body = host.SKILL_DEST.read_text(encoding="utf-8")
    assert "# === Runlog read skill ===" in body
    assert "# === Runlog author skill ===" in body
    assert "# === Runlog harvest skill ===" in body
    assert "Runlog read skill" in body
    assert "Runlog author skill" in body
    assert "Runlog harvest skill" in body
