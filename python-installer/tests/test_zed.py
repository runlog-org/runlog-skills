"""Tests for ZedHost."""

from __future__ import annotations

from pathlib import Path

import pytest

from runlog_install.hosts.zed import ZedHost


# ---------------------------------------------------------------------------
# Test 1: install writes SKILL.md (delegated — does not touch settings.json)
# ---------------------------------------------------------------------------

def test_install_writes_skill(make_host, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )
    host.install()

    assert host.SKILL_DEST.is_file()
    assert host.SKILL_DEST.stat().st_size > 0


# ---------------------------------------------------------------------------
# Test 2: install does NOT write any settings/config JSON (delegated mode)
# ---------------------------------------------------------------------------

def test_install_does_not_write_settings_json(make_host, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )
    host.install()

    settings_json = tmp_path / ".config" / "zed" / "settings.json"
    assert not settings_json.exists(), (
        "Delegated mode must not create settings.json; MCP wiring is left to `npx add-mcp`."
    )


# ---------------------------------------------------------------------------
# Test 3: install is idempotent — calling twice overwrites, no error
# ---------------------------------------------------------------------------

def test_install_idempotent(make_host, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )
    host.install()
    host.install()
    assert host.SKILL_DEST.is_file()


# ---------------------------------------------------------------------------
# Test 4: uninstall removes SKILL file
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill(make_host, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )
    host.install()
    assert host.SKILL_DEST.is_file()

    host.uninstall()
    assert not host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# Test 5: uninstall walks up empty parent dirs (stops at ~/.config/zed)
# ---------------------------------------------------------------------------

def test_uninstall_walks_up_empty_dirs(make_host, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )

    # SKILL_DEST is tmp_path/.config/zed/rules.md — parent is .config/zed/
    # Since rules.md lives directly in ~/.config/zed/, the stop boundary is
    # reached immediately: there are no intermediate dirs to remove.
    # Confirm that ~/.config/zed/ itself is NOT removed.
    host.install()
    zed_dir = tmp_path / ".config" / "zed"
    assert zed_dir.is_dir()

    host.uninstall()

    # rules.md gone
    assert not host.SKILL_DEST.exists()
    # ~/.config/zed/ is the stop boundary — must survive
    assert zed_dir.is_dir()


# ---------------------------------------------------------------------------
# Test 6: uninstall when nothing installed is a no-op
# ---------------------------------------------------------------------------

def test_uninstall_missing_is_noop(make_host, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )
    # Should not raise even though rules.md was never created.
    host.uninstall()
    assert not host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# Test 7: install raises FileNotFoundError when source SKILL.md is missing
# ---------------------------------------------------------------------------

def test_install_missing_source_raises(make_host, monkeypatch, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )
    # Point _SKILL_SRC at a nonexistent path.
    monkeypatch.setattr(ZedHost, "_SKILL_SRC", tmp_path / "nonexistent" / "SKILL.md")

    with pytest.raises(FileNotFoundError):
        host.install()


# ---------------------------------------------------------------------------
# Test 8: mode attribute is "delegated"
# ---------------------------------------------------------------------------

def test_mode_attribute(make_host, tmp_path):
    host = make_host(
        ZedHost,
        skill_dest=tmp_path / ".config" / "zed" / "rules.md",
    )
    assert host.mode == "delegated"
