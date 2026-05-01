"""Tests for the CursorHost adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from runlog_install.hosts.cursor import CursorHost


# ---------------------------------------------------------------------------
# 1. install writes runlog.mdc (delegated — does not touch mcp.json)
# ---------------------------------------------------------------------------

def test_install_fresh(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )
    host.install()

    assert host.SKILL_DEST.exists(), "runlog.mdc should be created"


# ---------------------------------------------------------------------------
# 2. install is idempotent — calling twice overwrites SKILL, no error
# ---------------------------------------------------------------------------

def test_install_idempotent(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )
    host.install()
    host.install()
    assert host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# 3. install does NOT write mcp.json (delegated mode)
# ---------------------------------------------------------------------------

def test_install_does_not_write_mcp_json(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )
    host.install()

    mcp_json = tmp_path / ".cursor" / "mcp.json"
    assert not mcp_json.exists(), (
        "Delegated mode must not create mcp.json; MCP wiring is left to `npx add-mcp`."
    )


# ---------------------------------------------------------------------------
# 4. uninstall removes the rule file and cleans up the parent directory
# ---------------------------------------------------------------------------

def test_uninstall_removes_skill(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )

    host.install()
    assert host.SKILL_DEST.exists()

    host.uninstall()
    assert not host.SKILL_DEST.exists()


# ---------------------------------------------------------------------------
# 5. uninstall is idempotent when nothing is installed
# ---------------------------------------------------------------------------

def test_uninstall_idempotent_nothing_installed(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )
    # Should not raise even when no files exist
    host.uninstall()
    host.uninstall()


# ---------------------------------------------------------------------------
# 6. mode attribute is "delegated"
# ---------------------------------------------------------------------------

def test_mode_is_delegated(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )
    assert host.mode == "delegated"


# ---------------------------------------------------------------------------
# 7. install writes all three .mdc files (read, author, harvest)
# ---------------------------------------------------------------------------

def test_install_writes_all_three_skills(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )
    host.install()

    rules_dir = tmp_path / ".cursor" / "rules"
    assert (rules_dir / "runlog.mdc").is_file()
    assert (rules_dir / "runlog-author.mdc").is_file()
    assert (rules_dir / "runlog-harvest.mdc").is_file()


# ---------------------------------------------------------------------------
# 8. uninstall removes all three .mdc files
# ---------------------------------------------------------------------------

def test_uninstall_removes_all_three_skills(make_host, tmp_path):
    host = make_host(
        CursorHost,
        skill_dest=tmp_path / ".cursor" / "rules" / "runlog.mdc",
    )
    host.install()

    rules_dir = tmp_path / ".cursor" / "rules"
    assert (rules_dir / "runlog-author.mdc").is_file()
    assert (rules_dir / "runlog-harvest.mdc").is_file()

    host.uninstall()

    assert not (rules_dir / "runlog.mdc").exists()
    assert not (rules_dir / "runlog-author.mdc").exists()
    assert not (rules_dir / "runlog-harvest.mdc").exists()
