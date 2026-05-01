"""Tests for the CursorHost adapter."""

from __future__ import annotations

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
    host._SKILL_SRC = fake_skill_src  # type: ignore[assignment]
    return host


# ---------------------------------------------------------------------------
# 1. install writes runlog.mdc (delegated — does not touch mcp.json)
# ---------------------------------------------------------------------------

def test_install_fresh(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    host.install()

    assert host.SKILL_DEST.exists(), "runlog.mdc should be created"


# ---------------------------------------------------------------------------
# 2. install is idempotent — calling twice overwrites SKILL, no error
# ---------------------------------------------------------------------------

def test_install_idempotent(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    host.install()
    host.install()
    assert host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# 3. install does NOT write mcp.json (delegated mode)
# ---------------------------------------------------------------------------

def test_install_does_not_write_mcp_json(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    fake_home = tmp_path / "home"
    host.install()

    mcp_json = fake_home / ".cursor" / "mcp.json"
    assert not mcp_json.exists(), (
        "Delegated mode must not create mcp.json; MCP wiring is left to `npx add-mcp`."
    )


# ---------------------------------------------------------------------------
# 4. uninstall removes the rule file and cleans up the parent directory
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)

    host.install()
    assert host.SKILL_DEST.exists()

    host.uninstall()
    assert not host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# 5. uninstall is idempotent when nothing is installed
# ---------------------------------------------------------------------------

def test_uninstall_idempotent_nothing_installed(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    # Should not raise even when no files exist
    host.uninstall()
    host.uninstall()


# ---------------------------------------------------------------------------
# 6. mode attribute is "delegated"
# ---------------------------------------------------------------------------

def test_mode_is_delegated(tmp_path, monkeypatch):
    host = _make_host(tmp_path, monkeypatch)
    assert host.mode == "delegated"
