"""Tests for ContinueHost."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from runlog_install.hosts.continue_host import ContinueHost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ContinueHost:
    """Return a ContinueHost with all paths redirected under tmp_path."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    # Provide a stub source SKILL.md so tests don't depend on repo layout.
    fake_skill_src = tmp_path / "_src_skill" / "SKILL.md"
    fake_skill_src.parent.mkdir(parents=True, exist_ok=True)
    fake_skill_src.write_text("# Runlog skill (Continue test stub)\n", encoding="utf-8")

    monkeypatch.setattr(
        ContinueHost,
        "SKILL_DEST",
        tmp_path / ".continue" / "rules" / "runlog.md",
    )
    monkeypatch.setattr(
        ContinueHost,
        "SETTINGS_PATH",
        tmp_path / ".continue" / "config.yaml",
    )
    monkeypatch.setattr(ContinueHost, "_SKILL_SRC", fake_skill_src)

    return ContinueHost()


# ---------------------------------------------------------------------------
# 1. install writes SKILL (rules/runlog.md)
# ---------------------------------------------------------------------------

def test_install_writes_skill(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    host.install(api_key="sk-runlog-testkey")

    assert host.SKILL_DEST.is_file(), "rules/runlog.md should be created"
    assert host.SKILL_DEST.stat().st_size > 0


# ---------------------------------------------------------------------------
# 2. install writes MCP block with correct URL + Bearer header
# ---------------------------------------------------------------------------

def test_install_writes_mcp_block(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    api_key = "sk-runlog-abc123xyz"
    host.install(api_key=api_key)

    assert host.SETTINGS_PATH.exists(), "config.yaml should be created"
    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")

    # String-search assertions (stdlib-only: no PyYAML).
    # yamlc renders string values double-quoted, so "runlog" not runlog.
    assert 'name: "runlog"' in raw, 'name: "runlog" line must be in config.yaml'
    assert "https://api.runlog.org/mcp" in raw, "MCP URL must be present"
    assert f"Bearer {api_key}" in raw, "Bearer token must be written into config.yaml"


# ---------------------------------------------------------------------------
# 3. install preserves sibling MCP servers
# ---------------------------------------------------------------------------

def test_install_preserves_sibling_mcp_servers(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Pre-populate config.yaml with a sibling MCP server.
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(
        "mcpServers:\n"
        "  - name: other-tool\n"
        "    type: streamable-http\n"
        "    url: \"https://other.example.com/mcp\"\n",
        encoding="utf-8",
    )

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert 'name: "runlog"' in raw, "runlog block must be present"
    assert "name: other-tool" in raw, "sibling entry must be preserved"


# ---------------------------------------------------------------------------
# 4. install is idempotent — installing twice produces exactly one runlog entry
# ---------------------------------------------------------------------------

def test_install_idempotent(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    host.install(api_key="sk-runlog-first")
    host.install(api_key="sk-runlog-second")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    # yamlc renders string values double-quoted.
    assert raw.count('name: "runlog"') == 1, 'duplicate name: "runlog" entry found'
    assert "Bearer sk-runlog-second" in raw, "Authorization must reflect the latest key"


# ---------------------------------------------------------------------------
# 5. install(api_key=None) raises ValueError
# ---------------------------------------------------------------------------

def test_install_requires_api_key(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        host.install(api_key=None)


# ---------------------------------------------------------------------------
# 6. install preserves pre-existing YAML comments
# ---------------------------------------------------------------------------

def test_install_preserves_yaml_comments(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Write a config.yaml that contains comments — before and within mcpServers.
    yaml_text = (
        "# user comment at top\n"
        "mcpServers:\n"
        "  # comment inside mcpServers\n"
        "  - name: existing\n"
        "    type: streamable-http\n"
        "    url: \"https://existing.example.com/mcp\"\n"
    )
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(yaml_text, encoding="utf-8")

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "# user comment at top" in raw, "top-level comment must be preserved"
    assert "# comment inside mcpServers" in raw, "inline comment must be preserved"
    assert 'name: "runlog"' in raw, "runlog block must be present"
    assert "name: existing" in raw, "sibling entry must be preserved"


# ---------------------------------------------------------------------------
# 7. uninstall removes SKILL file and MCP block; preserves sibling
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill_and_mcp_block(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    host.install(api_key="sk-runlog-testkey")

    # Add a sibling MCP server so the file is not left empty.
    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    raw += (
        "  - name: sibling\n"
        "    type: streamable-http\n"
        "    url: \"https://sibling.example.com/mcp\"\n"
    )
    host.SETTINGS_PATH.write_text(raw, encoding="utf-8")

    host.uninstall()

    assert not host.SKILL_DEST.exists(), "rules/runlog.md should be removed"
    remaining = host.SETTINGS_PATH.read_text(encoding="utf-8")
    # yamlc renders string values double-quoted; check for the quoted form.
    assert 'name: "runlog"' not in remaining, "runlog block must be gone"
    assert "name: sibling" in remaining, "sibling must remain"


# ---------------------------------------------------------------------------
# 8. uninstall when nothing installed is a no-op
# ---------------------------------------------------------------------------

def test_uninstall_missing_is_noop(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    # Should not raise even when no files exist.
    host.uninstall()
    host.uninstall()
    assert not host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# 9. mode attribute is "fallback"
# ---------------------------------------------------------------------------

def test_mode_attribute(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    assert host.mode == "fallback"


# ---------------------------------------------------------------------------
# 10. install preserves other top-level sections (e.g. rules:)
# ---------------------------------------------------------------------------

def test_install_preserves_top_level_rules_section(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Pre-populate config.yaml with both mcpServers and a rules section.
    yaml_text = (
        "mcpServers:\n"
        "  - name: other-tool\n"
        "    type: streamable-http\n"
        "    url: \"https://other.example.com/mcp\"\n"
        "\n"
        "rules:\n"
        "  - name: my-team-rules\n"
        "    rule: |\n"
        "      Always check team docs first.\n"
    )
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(yaml_text, encoding="utf-8")

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    # Both the new runlog block and the sibling must be present.
    # yamlc renders string values double-quoted.
    assert 'name: "runlog"' in raw, "runlog block must be present"
    assert "name: other-tool" in raw, "sibling MCP server must be preserved"
    # The rules section must survive intact.
    assert "rules:" in raw, "rules: section must be preserved"
    assert "name: my-team-rules" in raw, "rules content must be preserved"
    assert "Always check team docs first." in raw, "rules rule text must be preserved"
