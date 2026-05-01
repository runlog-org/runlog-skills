"""Shared test fixtures for python-installer tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def make_host(monkeypatch, tmp_path):
    """Factory that builds a Host instance with all paths redirected under tmp_path.

    Usage:
        host = make_host(WindsurfHost,
                         skill_dest=tmp_path / ".codeium" / "windsurf" / "mcp_config.json",
                         settings_path=tmp_path / ".codeium" / "windsurf" / "globalrules")

    The factory monkeypatches Path.home → tmp_path, writes a stub SKILL.md
    source under tmp_path/_src_skill/, and patches the host class's
    SKILL_DEST / SETTINGS_PATH / _SKILL_SRC class attributes.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    fake_skill_src = tmp_path / "_src_skill" / "SKILL.md"
    fake_skill_src.parent.mkdir(parents=True, exist_ok=True)
    fake_skill_src.write_text("# Runlog skill (test stub)\n", encoding="utf-8")

    def _factory(host_cls, *, skill_dest, settings_path=None):
        monkeypatch.setattr(host_cls, "SKILL_DEST", skill_dest)
        if settings_path is not None and hasattr(host_cls, "SETTINGS_PATH"):
            monkeypatch.setattr(host_cls, "SETTINGS_PATH", settings_path)
        monkeypatch.setattr(host_cls, "_SKILL_SRC", fake_skill_src)
        return host_cls()

    return _factory
