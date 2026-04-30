"""Tests for the CursorHost adapter."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from runlog_install.hosts.cursor import CursorHost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CursorHost:
    """Return a CursorHost with all paths redirected under tmp_path."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

    # Create a fake SKILL.md so the source-file check doesn't fail.
    fake_skill_src = tmp_path / "cursor" / "SKILL.md"
    fake_skill_src.parent.mkdir(parents=True, exist_ok=True)
    fake_skill_src.write_text("# Fake Runlog skill for tests\n", encoding="utf-8")

    host = CursorHost()
    # Override instance paths to use the fake home and fake skill source.
    host.SKILL_DEST = fake_home / ".cursor" / "rules" / "runlog.mdc"
    host.SETTINGS_PATH = fake_home / ".cursor" / "mcp.json"
    host._SKILL_SRC = fake_skill_src  # type: ignore[assignment]
    return host


# ---------------------------------------------------------------------------
# 1. install writes runlog.mdc and merges the runlog block into a fresh mcp.json
# ---------------------------------------------------------------------------

def test_install_fresh(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    host.install("sk-runlog-testkey")

    assert host.SKILL_DEST.exists(), "runlog.mdc should be created"
    assert host.SETTINGS_PATH.exists(), "mcp.json should be created"

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["mcpServers"]
    block = data["mcpServers"]["runlog"]
    assert block["url"] == "https://api.runlog.org/mcp"


# ---------------------------------------------------------------------------
# 2. install merges into an existing mcp.json that has other mcpServers entries
# ---------------------------------------------------------------------------

def test_install_merges_siblings(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)

    # Pre-populate mcp.json with a sibling server
    host.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    host.SETTINGS_PATH.write_text(
        json.dumps({
            "mcpServers": {
                "other": {"url": "https://other.example.com/mcp"}
            }
        }),
        encoding="utf-8",
    )

    host.install("sk-runlog-testkey")

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["mcpServers"], "runlog block must be present"
    assert "other" in data["mcpServers"], "sibling entry must be preserved"


# ---------------------------------------------------------------------------
# 3. install replaces an existing runlog block (idempotent re-run)
# ---------------------------------------------------------------------------

def test_install_idempotent_replace(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)

    host.install("sk-runlog-first")
    host.install("sk-runlog-second")

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" in data["mcpServers"]
    # Key should appear only once
    raw = host.SETTINGS_PATH.read_text()
    assert raw.count('"runlog"') == 1

    # Authorization header should reflect the latest key
    auth = data["mcpServers"]["runlog"]["headers"]["Authorization"]
    assert auth == "Bearer sk-runlog-second"


# ---------------------------------------------------------------------------
# 4. uninstall removes the rule file and the runlog block, leaves siblings
# ---------------------------------------------------------------------------

def test_uninstall_removes_and_preserves_siblings(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)

    # Install first, then add a sibling, then uninstall
    host.install("sk-runlog-testkey")
    raw = host.SETTINGS_PATH.read_text()
    # Manually add a sibling by re-writing the file
    data = json.loads(raw)
    data["mcpServers"]["sibling"] = {"url": "https://sibling.example.com/mcp"}
    host.SETTINGS_PATH.write_text(json.dumps(data), encoding="utf-8")

    host.uninstall()

    assert not host.SKILL_DEST.exists(), "runlog.mdc should be removed"
    remaining = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" not in remaining.get("mcpServers", {}), "runlog block must be gone"
    assert "sibling" in remaining.get("mcpServers", {}), "sibling must remain"


# ---------------------------------------------------------------------------
# 5. uninstall is idempotent when nothing is installed
# ---------------------------------------------------------------------------

def test_uninstall_idempotent_nothing_installed(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    # Should not raise even when no files exist
    host.uninstall()
    host.uninstall()


# ---------------------------------------------------------------------------
# 6. The MCP block has Bearer-token header with the literal key
# ---------------------------------------------------------------------------

def test_install_bearer_token(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    api_key = "sk-runlog-abc123xyz"
    host.install(api_key)

    data = json.loads(host.SETTINGS_PATH.read_text())
    block = data["mcpServers"]["runlog"]
    assert "headers" in block
    assert block["headers"]["Authorization"] == f"Bearer {api_key}"


# ---------------------------------------------------------------------------
# 7. mcp.json file mode is 0600 after install
# ---------------------------------------------------------------------------

def test_install_file_mode_0600(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    host.install("sk-runlog-testkey")

    file_stat = os.stat(host.SETTINGS_PATH)
    mode = stat.S_IMODE(file_stat.st_mode)
    assert mode == 0o600, f"Expected 0600, got {oct(mode)}"
