"""Tests for ClaudeCodeHost."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from runlog_install.hosts.claude_code import ClaudeCodeHost
from runlog_install import jsonc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_host(monkeypatch, tmp_path: Path) -> ClaudeCodeHost:
    """Return a ClaudeCodeHost with Path.home() and paths redirected to tmp_path."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    # Provide a stub source SKILL.md so tests don't depend on repo layout.
    fake_skill_src = tmp_path / "_src_skill" / "SKILL.md"
    fake_skill_src.parent.mkdir(parents=True, exist_ok=True)
    fake_skill_src.write_text("# Runlog skill (test stub)\n", encoding="utf-8")

    # Re-evaluate the class-level paths so they reflect the patched home.
    monkeypatch.setattr(ClaudeCodeHost, "SKILL_DEST",
                        tmp_path / ".claude" / "skills" / "runlog" / "SKILL.md")
    monkeypatch.setattr(ClaudeCodeHost, "SETTINGS_PATH",
                        tmp_path / ".claude" / "settings.json")
    monkeypatch.setattr(ClaudeCodeHost, "_SKILL_SRC", fake_skill_src)

    host = ClaudeCodeHost()
    return host


def _settings(host: ClaudeCodeHost) -> dict:
    return jsonc.parse(host.SETTINGS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 1: install writes SKILL.md and merges runlog block into a fresh settings.json
# ---------------------------------------------------------------------------

def test_install_fresh(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    host.install("key-abc")

    # SKILL.md written
    assert host.SKILL_DEST.is_file()
    assert host.SKILL_DEST.stat().st_size > 0

    # settings.json has runlog block
    data = _settings(host)
    assert "mcpServers" in data
    assert "runlog" in data["mcpServers"]
    runlog = data["mcpServers"]["runlog"]
    assert runlog["type"] == "http"
    assert runlog["url"] == "https://api.runlog.org/mcp"


# ---------------------------------------------------------------------------
# Test 2: install merges into existing settings with unrelated mcpServers entries
# ---------------------------------------------------------------------------

def test_install_preserves_sibling_mcp(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Pre-populate settings.json with a sibling entry
    existing = {
        "mcpServers": {
            "other-tool": {
                "type": "http",
                "url": "https://other.example.com/mcp",
            }
        }
    }
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    host.install("key-xyz")

    data = _settings(host)
    # Sibling preserved
    assert "other-tool" in data["mcpServers"]
    assert data["mcpServers"]["other-tool"]["url"] == "https://other.example.com/mcp"
    # Runlog added
    assert "runlog" in data["mcpServers"]


# ---------------------------------------------------------------------------
# Test 3: install replaces existing runlog block (idempotent re-run)
# ---------------------------------------------------------------------------

def test_install_replaces_existing_runlog(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # First install with old key
    host.install("old-key")
    # Second install with new key
    host.install("new-key")

    data = _settings(host)
    runlog = data["mcpServers"]["runlog"]
    assert runlog["headers"]["Authorization"] == "Bearer new-key"
    # Only one runlog entry
    assert list(data["mcpServers"].keys()).count("runlog") == 1


# ---------------------------------------------------------------------------
# Test 4: uninstall removes SKILL file and runlog block, leaves siblings
# ---------------------------------------------------------------------------

def test_uninstall_removes_runlog_keeps_sibling(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)

    # Write a settings.json that already contains both runlog and a sibling,
    # as if installed by a prior run and then another tool added its own entry.
    # Using json.dumps here (not jsonc helper) to get clean, comma-correct JSON.
    settings_data = {
        "mcpServers": {
            "runlog": {
                "type": "http",
                "url": "https://api.runlog.org/mcp",
                "headers": {"Authorization": "Bearer key-del"},
            },
            "sibling": {
                "type": "http",
                "url": "https://sibling.example.com/mcp",
            },
        }
    }
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")
    # Also create the SKILL.md so unlink has something to remove
    host.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
    host.SKILL_DEST.write_text("# stub\n", encoding="utf-8")

    host.uninstall()

    # SKILL.md gone
    assert not host.SKILL_DEST.exists()

    # runlog block gone, sibling preserved
    data = _settings(host)
    assert "runlog" not in data.get("mcpServers", {})
    assert "sibling" in data["mcpServers"]


# ---------------------------------------------------------------------------
# Test 5: uninstall is idempotent when nothing is installed
# ---------------------------------------------------------------------------

def test_uninstall_idempotent_when_nothing_installed(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    # Should not raise even though SKILL.md and settings.json don't exist
    host.uninstall()
    assert not host.SKILL_DEST.exists()
    assert not host.SETTINGS_PATH.exists()


# ---------------------------------------------------------------------------
# Test 6: install uses Bearer token header with the literal key
# ---------------------------------------------------------------------------

def test_install_bearer_token(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    api_key = "tok-1234567890abcdef"
    host.install(api_key)

    data = _settings(host)
    auth = data["mcpServers"]["runlog"]["headers"]["Authorization"]
    assert auth == f"Bearer {api_key}"


# ---------------------------------------------------------------------------
# Test 7: settings.json file mode is 0600 after install
# ---------------------------------------------------------------------------

def test_install_settings_file_mode(monkeypatch, tmp_path):
    host = _make_host(monkeypatch, tmp_path)
    host.install("key-mode-test")

    mode = host.SETTINGS_PATH.stat().st_mode
    # Check that only owner read/write bits are set (no group or other)
    assert stat.S_IMODE(mode) == 0o600
