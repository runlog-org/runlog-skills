"""Tests for _base.py — BaseHost, SeparateFileMixin, SharedFileMixin,
DelegatedMixin, FallbackMixin.

All test classes are defined inline; we do not import real host adapters.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar, Literal
from unittest.mock import call, patch

import pytest

from runlog_install.hosts._base import (
    RUNLOG_MCP_URL,
    BaseHost,
    DelegatedMixin,
    FallbackMixin,
    SeparateFileMixin,
    SharedFileMixin,
)
from runlog_install import jsonc as _jsonc


# ---------------------------------------------------------------------------
# Helpers: minimal inline host classes for isolated mixin testing
# ---------------------------------------------------------------------------

def _make_src_dir(tmp_path: Path) -> Path:
    """Seed the three skill source files under tmp_path/_src/ and return the dir."""
    src = tmp_path / "_src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "SKILL.md").write_text("# read skill\n", encoding="utf-8")
    (src / "runlog-author.md").write_text("# author skill\n", encoding="utf-8")
    (src / "runlog-harvest.md").write_text("# harvest skill\n", encoding="utf-8")
    return src


# ---------------------------------------------------------------------------
# 1. BaseHost.__init_subclass__ derives _SKILL_SRC when _VENDOR_KEY is present
# ---------------------------------------------------------------------------

def test_init_subclass_sets_skill_src():
    class MyHost(BaseHost):
        _VENDOR_KEY = "aider"

    # _SKILL_SRC should be resolved relative to _base.py's parents[4] / "aider" / "SKILL.md"
    assert MyHost._SKILL_SRC.name == "SKILL.md"
    assert MyHost._SKILL_SRC.parent.name == "aider"
    # parents[4] is the repo root (runlog-skills/)
    assert MyHost._SKILL_SRC.parent.parent.name == "runlog-skills"


# ---------------------------------------------------------------------------
# 2. BaseHost.__init_subclass__ does NOT set _SKILL_SRC for intermediate classes
# ---------------------------------------------------------------------------

def test_init_subclass_skips_intermediate_without_vendor_key():
    # Defining a subclass without _VENDOR_KEY should not raise and should not
    # set _SKILL_SRC on the intermediate class itself.
    class IntermediateMixin(BaseHost):
        pass  # no _VENDOR_KEY

    assert "_SKILL_SRC" not in IntermediateMixin.__dict__


# ---------------------------------------------------------------------------
# 3. SeparateFileMixin.skill_sources — .md extension
# ---------------------------------------------------------------------------

def test_separate_file_mixin_md_extension(tmp_path):
    src = _make_src_dir(tmp_path)

    class MdHost(BaseHost, SeparateFileMixin):
        name = "TestMd"
        target_key = "testmd"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"

    host = MdHost()
    sources = host.skill_sources
    assert len(sources) == 3

    src_paths, dest_paths, labels = zip(*sources)

    # All dests under the same parent
    dest_dir = tmp_path / "rules"
    assert dest_paths[0] == dest_dir / "runlog.md"
    assert dest_paths[1] == dest_dir / "runlog-author.md"
    assert dest_paths[2] == dest_dir / "runlog-harvest.md"

    # Suffixes all .md
    for dp in dest_paths:
        assert dp.suffix == ".md"

    assert labels == ("read", "author", "harvest")


# ---------------------------------------------------------------------------
# 4. SeparateFileMixin.skill_sources — .mdc extension
# ---------------------------------------------------------------------------

def test_separate_file_mixin_mdc_extension(tmp_path):
    src = _make_src_dir(tmp_path)

    class MdcHost(BaseHost, SeparateFileMixin):
        name = "TestMdc"
        target_key = "testmdc"
        SKILL_DEST = tmp_path / "rules" / "runlog.mdc"
        _SKILL_SRC = src / "SKILL.md"

    host = MdcHost()
    sources = host.skill_sources
    dest_paths = [dp for _, dp, _ in sources]

    assert dest_paths[0].suffix == ".mdc"
    assert dest_paths[1].suffix == ".mdc"
    assert dest_paths[2].suffix == ".mdc"
    assert dest_paths[0].parent == dest_paths[1].parent == dest_paths[2].parent


# ---------------------------------------------------------------------------
# 5. SharedFileMixin.skill_sources — all three dests point at SKILL_DEST
# ---------------------------------------------------------------------------

def test_shared_file_mixin_all_point_to_skill_dest(tmp_path):
    src = _make_src_dir(tmp_path)

    class SharedHost(BaseHost, SharedFileMixin):
        name = "TestShared"
        target_key = "testshared"
        SKILL_DEST = tmp_path / "globalrules"
        _SKILL_SRC = src / "SKILL.md"

    host = SharedHost()
    sources = host.skill_sources
    assert len(sources) == 3

    for _, dest, _ in sources:
        assert dest == tmp_path / "globalrules"


# ---------------------------------------------------------------------------
# 6. DelegatedMixin.install calls skill_writer.write_skills
# ---------------------------------------------------------------------------

def test_delegated_install_calls_write_skills(tmp_path):
    src = _make_src_dir(tmp_path)

    class DelHost(BaseHost, DelegatedMixin, SeparateFileMixin):
        name = "TestDel"
        target_key = "testdel"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"

    host = DelHost()

    calls_received = []

    def fake_write_skills(skill_sources, host_name):
        calls_received.append((skill_sources, host_name))

    with patch("runlog_install.skill_writer.write_skills", side_effect=fake_write_skills):
        host.install(api_key=None)

    assert len(calls_received) == 1
    skill_sources_arg, host_name_arg = calls_received[0]
    assert skill_sources_arg == host.skill_sources
    assert host_name_arg == "TestDel"


# ---------------------------------------------------------------------------
# 7. DelegatedMixin.uninstall calls skill_writer.remove_skills with rmdir_stop
# ---------------------------------------------------------------------------

def test_delegated_uninstall_calls_remove_skills(tmp_path):
    src = _make_src_dir(tmp_path)
    stop = tmp_path / "stop"

    class DelStopHost(BaseHost, DelegatedMixin, SeparateFileMixin):
        name = "TestDelStop"
        target_key = "testdelstop"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        _RMDIR_STOP = stop

    host = DelStopHost()

    calls_received = []

    def fake_remove_skills(skill_sources, *, rmdir_stop=None):
        calls_received.append({"skill_sources": skill_sources, "rmdir_stop": rmdir_stop})

    with patch("runlog_install.skill_writer.remove_skills", side_effect=fake_remove_skills):
        host.uninstall()

    assert len(calls_received) == 1
    assert calls_received[0]["rmdir_stop"] == stop


# ---------------------------------------------------------------------------
# 8. FallbackMixin.install raises ValueError when api_key=None
# ---------------------------------------------------------------------------

def test_fallback_install_raises_without_api_key(tmp_path):
    src = _make_src_dir(tmp_path)

    class FallHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestFall"
        target_key = "testfall"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = tmp_path / "config.json"
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"
        _TOP_LEVEL_KEY = "mcpServers"

        def _mcp_block(self, api_key: str) -> dict:
            return {"url": RUNLOG_MCP_URL, "headers": {"Authorization": f"Bearer {api_key}"}}

    host = FallHost()
    with pytest.raises(ValueError) as exc_info:
        host.install(api_key=None)
    msg = str(exc_info.value)
    assert "FallHost" in msg
    assert str(tmp_path / "config.json") in msg


# ---------------------------------------------------------------------------
# 9. FallbackMixin.install writes file with mode 0600 (jsonc-object)
# ---------------------------------------------------------------------------

def test_fallback_install_chmod_0600_jsonc(tmp_path):
    src = _make_src_dir(tmp_path)

    class ChmodHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestChmod"
        target_key = "testchmod"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = tmp_path / "config.json"
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"
        _TOP_LEVEL_KEY = "mcpServers"

        def _mcp_block(self, api_key: str) -> dict:
            return {"url": RUNLOG_MCP_URL, "headers": {"Authorization": f"Bearer {api_key}"}}

    host = ChmodHost()
    host.install(api_key="sk-test-key")

    mode = os.stat(host.SETTINGS_PATH).st_mode & 0o777
    assert mode == 0o600, f"Expected 0600, got {oct(mode)}"


# ---------------------------------------------------------------------------
# 10. FallbackMixin.install uses jsonc.add_to_object for jsonc-object style
# ---------------------------------------------------------------------------

def test_fallback_install_jsonc_object_style(tmp_path):
    src = _make_src_dir(tmp_path)

    class JsoncHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestJsonc"
        target_key = "testjsonc"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = tmp_path / "mcp.json"
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"
        _TOP_LEVEL_KEY = "servers"

        def _mcp_block(self, api_key: str) -> dict:
            return {"url": RUNLOG_MCP_URL, "headers": {"Authorization": f"Bearer {api_key}"}}

    host = JsoncHost()
    host.install(api_key="sk-test-abc")

    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "servers" in data
    assert "runlog" in data["servers"]
    assert data["servers"]["runlog"]["url"] == RUNLOG_MCP_URL
    assert data["servers"]["runlog"]["headers"]["Authorization"] == "Bearer sk-test-abc"


# ---------------------------------------------------------------------------
# 11. FallbackMixin.install uses yamlc.add_to_list for yamlc-list style
# ---------------------------------------------------------------------------

def test_fallback_install_yamlc_list_style(tmp_path):
    src = _make_src_dir(tmp_path)

    class YamlcHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestYamlc"
        target_key = "testyamlc"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = tmp_path / "config.yaml"
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "yamlc-list"
        _TOP_LEVEL_KEY = "mcpServers"

        def _mcp_block(self, api_key: str) -> dict:
            return {
                "name": "runlog",
                "url": RUNLOG_MCP_URL,
                "headers": {"Authorization": f"Bearer {api_key}"},
            }

    host = YamlcHost()
    host.install(api_key="sk-yaml-key")

    raw = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "mcpServers" in raw
    # yamlc quotes string values, so the identifier appears as name: "runlog"
    assert "runlog" in raw


# ---------------------------------------------------------------------------
# 12. FallbackMixin.install seeds missing jsonc-object config correctly
# ---------------------------------------------------------------------------

def test_fallback_install_seeds_missing_jsonc_config(tmp_path):
    src = _make_src_dir(tmp_path)
    settings = tmp_path / "subdir" / "mcp.json"  # non-existent path

    class SeedHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestSeed"
        target_key = "testseed"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = settings
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"
        _TOP_LEVEL_KEY = "mcpServers"

        def _mcp_block(self, api_key: str) -> dict:
            return {"url": RUNLOG_MCP_URL, "headers": {"Authorization": f"Bearer {api_key}"}}

    host = SeedHost()
    assert not settings.exists()

    host.install(api_key="sk-seed-key")

    assert settings.exists()
    data = json.loads(settings.read_text())
    assert "mcpServers" in data
    assert "runlog" in data["mcpServers"]


# ---------------------------------------------------------------------------
# 13. FallbackMixin.uninstall is a no-op when SETTINGS_PATH doesn't exist
# ---------------------------------------------------------------------------

def test_fallback_uninstall_noop_when_settings_missing(tmp_path):
    src = _make_src_dir(tmp_path)

    class NoopHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestNoop"
        target_key = "testnoop"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = tmp_path / "nonexistent.json"
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"
        _TOP_LEVEL_KEY = "mcpServers"

        def _mcp_block(self, api_key: str) -> dict:
            return {"url": RUNLOG_MCP_URL}

    host = NoopHost()
    assert not host.SETTINGS_PATH.exists()
    # Should not raise
    host.uninstall()


# ---------------------------------------------------------------------------
# 14. FallbackMixin.uninstall removes runlog key for jsonc-object style
# ---------------------------------------------------------------------------

def test_fallback_uninstall_removes_jsonc_key(tmp_path):
    src = _make_src_dir(tmp_path)

    class UninstJsoncHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestUninstJsonc"
        target_key = "testuninstjsonc"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = tmp_path / "mcp.json"
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "jsonc-object"
        _TOP_LEVEL_KEY = "mcpServers"

        def _mcp_block(self, api_key: str) -> dict:
            return {"url": RUNLOG_MCP_URL, "headers": {"Authorization": f"Bearer {api_key}"}}

    host = UninstJsoncHost()
    host.install(api_key="sk-uninstall-key")
    assert "runlog" in json.loads(host.SETTINGS_PATH.read_text())["mcpServers"]

    host.uninstall()
    data = json.loads(host.SETTINGS_PATH.read_text())
    assert "runlog" not in data.get("mcpServers", {})


# ---------------------------------------------------------------------------
# 15. FallbackMixin.uninstall removes runlog entry for yamlc-list style
# ---------------------------------------------------------------------------

def test_fallback_uninstall_removes_yamlc_entry(tmp_path):
    src = _make_src_dir(tmp_path)

    class UninstYamlcHost(BaseHost, FallbackMixin, SeparateFileMixin):
        name = "TestUninstYamlc"
        target_key = "testuninstyamlc"
        SKILL_DEST = tmp_path / "rules" / "runlog.md"
        _SKILL_SRC = src / "SKILL.md"
        SETTINGS_PATH = tmp_path / "config.yaml"
        _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]] = "yamlc-list"
        _TOP_LEVEL_KEY = "mcp-servers"

        def _mcp_block(self, api_key: str) -> dict:
            return {
                "name": "runlog",
                "url": RUNLOG_MCP_URL,
                "headers": {"Authorization": f"Bearer {api_key}"},
            }

    host = UninstYamlcHost()
    host.install(api_key="sk-yaml-uninstall")

    raw_before = host.SETTINGS_PATH.read_text(encoding="utf-8")
    # yamlc quotes string values; "runlog" appears as the value
    assert "runlog" in raw_before

    host.uninstall()

    raw_after = host.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "runlog" not in raw_after
