"""Tests for ClaudeCodeHost."""

from __future__ import annotations

from pathlib import Path

import pytest

from runlog_install.hosts.claude_code import ClaudeCodeHost


# ---------------------------------------------------------------------------
# Test 1: install writes SKILL.md (delegated — does not touch settings.json)
# ---------------------------------------------------------------------------

def test_install_fresh(make_host, tmp_path):
    host = make_host(
        ClaudeCodeHost,
        skill_dest=tmp_path / ".claude" / "skills" / "runlog" / "SKILL.md",
    )
    host.install()

    # SKILL.md written
    assert host.SKILL_DEST.is_file()
    assert host.SKILL_DEST.stat().st_size > 0


# ---------------------------------------------------------------------------
# Test 2: install is idempotent — calling twice overwrites SKILL, no error
# ---------------------------------------------------------------------------

def test_install_idempotent(make_host, tmp_path):
    host = make_host(
        ClaudeCodeHost,
        skill_dest=tmp_path / ".claude" / "skills" / "runlog" / "SKILL.md",
    )
    host.install()
    host.install()
    assert host.SKILL_DEST.is_file()


# ---------------------------------------------------------------------------
# Test 3: install does NOT write settings.json (delegated mode)
# ---------------------------------------------------------------------------

def test_install_does_not_write_settings_json(make_host, tmp_path):
    host = make_host(
        ClaudeCodeHost,
        skill_dest=tmp_path / ".claude" / "skills" / "runlog" / "SKILL.md",
    )
    host.install()

    settings_json = tmp_path / ".claude" / "settings.json"
    assert not settings_json.exists(), (
        "Delegated mode must not create settings.json; MCP wiring is left to `npx add-mcp`."
    )


# ---------------------------------------------------------------------------
# Test 4: uninstall removes SKILL file and cleans up empty parent dirs
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill_and_parents(make_host, tmp_path):
    host = make_host(
        ClaudeCodeHost,
        skill_dest=tmp_path / ".claude" / "skills" / "runlog" / "SKILL.md",
    )

    # Create the SKILL.md so unlink has something to remove.
    host.SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
    host.SKILL_DEST.write_text("# stub\n", encoding="utf-8")

    host.uninstall()

    assert not host.SKILL_DEST.exists()
    # The runlog/ subdirectory should have been removed (it was the only entry).
    assert not host.SKILL_DEST.parent.exists()


# ---------------------------------------------------------------------------
# Test 5: uninstall is idempotent when nothing is installed
# ---------------------------------------------------------------------------

def test_uninstall_idempotent_when_nothing_installed(make_host, tmp_path):
    host = make_host(
        ClaudeCodeHost,
        skill_dest=tmp_path / ".claude" / "skills" / "runlog" / "SKILL.md",
    )
    # Should not raise even though SKILL.md doesn't exist.
    host.uninstall()
    assert not host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# Test 6: mode attribute is "delegated"
# ---------------------------------------------------------------------------

def test_mode_is_delegated(make_host, tmp_path):
    host = make_host(
        ClaudeCodeHost,
        skill_dest=tmp_path / ".claude" / "skills" / "runlog" / "SKILL.md",
    )
    assert host.mode == "delegated"
