"""Tests for AiderHost."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from runlog_install.hosts.aider import AiderHost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AiderHost:
    """Return an AiderHost with all paths redirected under tmp_path."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    # Provide a stub source SKILL.md so tests don't depend on repo layout.
    fake_skill_src = tmp_path / "_src_skill" / "SKILL.md"
    fake_skill_src.parent.mkdir(parents=True, exist_ok=True)
    fake_skill_src.write_text("# Runlog skill (Aider test stub)\n", encoding="utf-8")

    monkeypatch.setattr(
        AiderHost,
        "SKILL_DEST",
        tmp_path / ".aider" / "runlog.md",
    )
    monkeypatch.setattr(
        AiderHost,
        "SETTINGS_PATH",
        tmp_path / ".aider.conf.yml",
    )
    monkeypatch.setattr(AiderHost, "_SKILL_SRC", fake_skill_src)

    return AiderHost()


# ---------------------------------------------------------------------------
# 1. install writes SKILL (~/.aider/runlog.md)
# ---------------------------------------------------------------------------

def test_install_writes_skill(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    host.install(api_key="sk-runlog-testkey")

    assert host.SKILL_DEST.is_file(), "~/.aider/runlog.md should be created"
    assert host.SKILL_DEST.stat().st_size > 0


# ---------------------------------------------------------------------------
# 2. install writes MCP block with correct URL + Bearer header
# ---------------------------------------------------------------------------

def test_install_writes_mcp_block(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    api_key = "sk-runlog-abc123xyz"
    host.install(api_key=api_key)

    assert host.SETTINGS_PATH.exists(), "~/.aider.conf.yml should be created"
    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")

    # Aider uses kebab-case "mcp-servers" (not camelCase "mcpServers")
    assert "mcp-servers:" in raw, "mcp-servers block must exist"
    assert "name: runlog" in raw or 'name: "runlog"' in raw, "runlog name entry must exist"
    assert "https://api.runlog.org/mcp" in raw, "MCP URL must be present"
    assert f"Bearer {api_key}" in raw, "Bearer token must be present"


# ---------------------------------------------------------------------------
# 3. install preserves sibling MCP servers
# ---------------------------------------------------------------------------

def test_install_preserves_sibling_mcp_servers(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Pre-populate ~/.aider.conf.yml with a sibling mcp-servers entry.
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(
        "mcp-servers:\n"
        "  - name: other-tool\n"
        "    transport: streamable-http\n"
        "    url: https://other.example.com/mcp\n",
        encoding="utf-8",
    )

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "name: runlog" in raw or 'name: "runlog"' in raw, "runlog entry must be present"
    assert "other-tool" in raw, "sibling entry must be preserved"


# ---------------------------------------------------------------------------
# 4. install is idempotent — installing twice produces no duplicate
# ---------------------------------------------------------------------------

def test_install_idempotent(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    host.install(api_key="sk-runlog-first")
    host.install(api_key="sk-runlog-second")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")

    # "runlog" (as the identifying value) should appear exactly once as a name.
    # Count occurrences of the name line.
    name_runlog_count = raw.count("name: runlog") + raw.count('name: "runlog"')
    assert name_runlog_count == 1, f"duplicate name: runlog found — count={name_runlog_count}"

    # Authorization should reflect the latest key.
    assert "Bearer sk-runlog-second" in raw, "latest api_key must win"
    assert "Bearer sk-runlog-first" not in raw, "stale api_key must be gone"


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

    # Write a ~/.aider.conf.yml that contains YAML comments around mcp-servers.
    yaml_text = (
        "# user comment before\n"
        "mcp-servers:\n"
        "  # inner comment\n"
        "  - name: existing\n"
        "    transport: streamable-http\n"
        "    url: https://existing.example.com/mcp\n"
        "# user comment after\n"
    )
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(yaml_text, encoding="utf-8")

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "# user comment before" in raw, "comment before mcp-servers must be preserved"
    assert "# user comment after" in raw, "comment after mcp-servers must be preserved"
    assert "name: runlog" in raw or 'name: "runlog"' in raw, "runlog entry must be present"
    assert "existing" in raw, "existing entry must be preserved"


# ---------------------------------------------------------------------------
# 7. uninstall removes skill file and MCP block, preserves sibling
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill_and_mcp_block(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    host.install(api_key="sk-runlog-testkey")

    # Add a sibling entry so the file is not left empty.
    sibling_yaml = (
        "  - name: sibling-tool\n"
        "    transport: streamable-http\n"
        "    url: https://sibling.example.com/mcp\n"
    )
    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    host.SETTINGS_PATH.write_text(raw + sibling_yaml, encoding="utf-8")

    host.uninstall()

    assert not host.SKILL_DEST.exists(), "~/.aider/runlog.md should be removed"
    remaining = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "name: runlog" not in remaining and 'name: "runlog"' not in remaining, \
        "runlog block must be gone"
    assert "sibling-tool" in remaining, "sibling entry must remain"


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
# 10. install preserves other top-level sections unchanged
# ---------------------------------------------------------------------------

def test_install_preserves_top_level_other_section(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Pre-populate with both mcp-servers and another top-level key.
    yaml_text = (
        "model: gpt-4o\n"
        "auto-commits: false\n"
        "mcp-servers:\n"
        "  - name: existing\n"
        "    transport: streamable-http\n"
        "    url: https://existing.example.com/mcp\n"
    )
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(yaml_text, encoding="utf-8")

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "model: gpt-4o" in raw, "model section must be preserved"
    assert "auto-commits: false" in raw, "auto-commits section must be preserved"
    assert "name: runlog" in raw or 'name: "runlog"' in raw, "runlog entry must be present"
    assert "existing" in raw, "existing mcp entry must be preserved"


# ---------------------------------------------------------------------------
# 11. install does NOT touch the read: list (deferred — list-of-strings)
# ---------------------------------------------------------------------------

def test_install_does_not_touch_read_list(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Pre-populate config with a read: list (list-of-strings).
    yaml_text = (
        "read:\n"
        "  - CONVENTIONS.md\n"
        "  - .aider/project-notes.md\n"
        "mcp-servers:\n"
        "  - name: existing\n"
        "    transport: streamable-http\n"
        "    url: https://existing.example.com/mcp\n"
    )
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(yaml_text, encoding="utf-8")

    # Capture the exact read: block before install.
    read_block_before = "read:\n  - CONVENTIONS.md\n  - .aider/project-notes.md\n"

    host.install(api_key="sk-runlog-testkey")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")

    # The read: block must be byte-identical post-install.
    assert read_block_before in raw, \
        "read: list must be preserved byte-for-byte (auto-wiring deferred)"

    # The runlog.md path must NOT have been added to the read: list.
    assert "runlog.md" not in raw.split("read:")[1].split("mcp-servers:")[0], \
        "installer must not auto-wire ~/.aider/runlog.md into read: list"

    # SKILL_DEST must be at the documented path so the user can wire it manually.
    expected_skill_dest = tmp_path / ".aider" / "runlog.md"
    assert host.SKILL_DEST == expected_skill_dest, \
        f"SKILL_DEST must be at ~/.aider/runlog.md; got {host.SKILL_DEST}"
    assert host.SKILL_DEST.is_file(), "SKILL_DEST must exist after install"
