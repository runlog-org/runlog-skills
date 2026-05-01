"""_base.py — shared base + mixins for runlog host adapters.

`Host` (in runlog_install.host) is the structural Protocol the rest of the
installer (cli.py, skill_writer.py) depends on. This module provides
concrete bases that satisfy that Protocol and eliminate duplication
across the seven host adapter classes.

Two orthogonal axes:
  - File layout: SeparateFileMixin (each skill at a sibling file) vs
    SharedFileMixin (all skills concatenated into one file).
  - Install mode: DelegatedMixin (SKILL placement only) vs FallbackMixin
    (SKILL placement + direct edit of the host's MCP config file).

Concrete hosts pick one mixin from each axis (plus BaseHost):

    class CursorHost(BaseHost, DelegatedMixin, SeparateFileMixin): ...
    class AiderHost(BaseHost, FallbackMixin, SeparateFileMixin): ...

The `_SKILL_SRC` derivation lives on BaseHost as `__init_subclass__`
logic so concrete hosts only need to declare `_VENDOR_KEY`.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from runlog_install import jsonc, skill_writer, yamlc

# Module-level constant replacing the duplicated literal.
RUNLOG_MCP_URL = "https://api.runlog.org/mcp"


class BaseHost:
    """Shared base for all runlog host adapters."""

    name: ClassVar[str]
    target_key: ClassVar[str]
    mode: ClassVar[Literal["delegated", "fallback"]]

    # Concrete subclass declares; e.g. _VENDOR_KEY = "aider" or "claude-code".
    _VENDOR_KEY: ClassVar[str]

    # Set by __init_subclass__ when _VENDOR_KEY is present on the concrete class.
    _SKILL_SRC: ClassVar[Path]

    # Concrete subclass declares.
    SKILL_DEST: ClassVar[Path]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "_VENDOR_KEY" in cls.__dict__:
            cls._SKILL_SRC = (
                Path(__file__).resolve().parents[4] / cls._VENDOR_KEY / "SKILL.md"
            )

    def post_install_hint(self) -> str | None:
        """Return None; concrete hosts that need a hint override this."""
        return None


class SeparateFileMixin:
    """Each skill is placed at a sibling file under SKILL_DEST.parent."""

    _SKILL_SRC: ClassVar[Path]
    SKILL_DEST: ClassVar[Path]

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three (source, dest, label) specs — one file per skill."""
        ext = self.SKILL_DEST.suffix
        dest_dir = self.SKILL_DEST.parent
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", dest_dir / f"runlog-author{ext}", "author"),
            (src_root / "runlog-harvest.md", dest_dir / f"runlog-harvest{ext}", "harvest"),
        ]


class SharedFileMixin:
    """All three skills are concatenated into the single SKILL_DEST file."""

    _SKILL_SRC: ClassVar[Path]
    SKILL_DEST: ClassVar[Path]

    @property
    def skill_sources(self) -> list[tuple[Path, Path, str]]:
        """Three (source, dest, label) specs all pointing at the same dest."""
        src_root = self._SKILL_SRC.parent
        return [
            (self._SKILL_SRC, self.SKILL_DEST, "read"),
            (src_root / "runlog-author.md", self.SKILL_DEST, "author"),
            (src_root / "runlog-harvest.md", self.SKILL_DEST, "harvest"),
        ]


class DelegatedMixin:
    """SKILL placement only; MCP config is handled by `npx add-mcp`."""

    mode: ClassVar[Literal["delegated", "fallback"]] = "delegated"

    # Subclasses that need rmdir-stop behaviour (claude_code, zed) override this.
    _RMDIR_STOP: ClassVar[Path | None] = None

    def install(self, api_key: str | None = None) -> None:
        """Write the three skill files (api_key ignored in delegated mode)."""
        skill_writer.write_skills(self.skill_sources, self.name)  # type: ignore[attr-defined]

    def uninstall(self) -> None:
        """Remove the three skill files; optionally prune empty parent dirs."""
        skill_writer.remove_skills(self.skill_sources, rmdir_stop=self._RMDIR_STOP)  # type: ignore[attr-defined]


class FallbackMixin:
    """SKILL placement + direct edit of the host's MCP config file."""

    mode: ClassVar[Literal["delegated", "fallback"]] = "fallback"

    # Concrete subclass declares (or overrides as a property, like CopilotHost).
    SETTINGS_PATH: ClassVar[Path]

    # "jsonc-object" → named-key object under _TOP_LEVEL_KEY (copilot, windsurf).
    # "yamlc-list"   → list-of-dicts under _TOP_LEVEL_KEY (aider, continue).
    _CONFIG_STYLE: ClassVar[Literal["jsonc-object", "yamlc-list"]]

    # Top-level config key, e.g. "mcpServers", "mcp-servers", "servers".
    _TOP_LEVEL_KEY: ClassVar[str]

    # Identifying key for list-of-dicts YAML hosts (both existing ones use "name").
    _LIST_IDENTIFIER: ClassVar[str] = "name"

    def _mcp_block(self, api_key: str) -> dict:
        """Return the MCP server block dict for this host. Concrete subclass implements."""
        raise NotImplementedError(f"{type(self).__name__} must implement _mcp_block()")

    def _settings_seed(self) -> str:
        """Return a seed string for a missing/empty config file."""
        if self._CONFIG_STYLE == "jsonc-object":
            return f'{{\n  "{self._TOP_LEVEL_KEY}": {{}}\n}}'
        return ""

    def install(self, api_key: str | None = None) -> None:
        """Write skill files and merge the runlog MCP block into the host config."""
        if api_key is None:
            raise ValueError(
                f"api_key is required for {type(self).__name__} (fallback mode): "
                f"pass the user's Runlog API key so the Bearer header can be "
                f"written into {self.SETTINGS_PATH}."
            )

        # 1. Write the three skill files.
        skill_writer.write_skills(self.skill_sources, self.name)  # type: ignore[attr-defined]

        # 2. Read SETTINGS_PATH or seed.
        if self.SETTINGS_PATH.exists():
            raw = self.SETTINGS_PATH.read_text(encoding="utf-8").strip()
            text = raw if raw else self._settings_seed()
        else:
            text = self._settings_seed()

        # 3. Build the MCP block.
        block = self._mcp_block(api_key)

        # 4. Merge the block into the config.
        if self._CONFIG_STYLE == "jsonc-object":
            text = jsonc.add_to_object(text, (self._TOP_LEVEL_KEY,), "runlog", block)
        else:
            text = yamlc.add_to_list(
                text, self._TOP_LEVEL_KEY, self._LIST_IDENTIFIER, "runlog", block
            )

        # 5. mkdir + write + chmod 0600.
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
        self.SETTINGS_PATH.chmod(0o600)

    def uninstall(self) -> None:
        """Remove skill files and the runlog block from the host config."""
        skill_writer.remove_skills(self.skill_sources)  # type: ignore[attr-defined]

        if not self.SETTINGS_PATH.exists():
            return

        text = self.SETTINGS_PATH.read_text(encoding="utf-8")

        if self._CONFIG_STYLE == "jsonc-object":
            text = jsonc.remove_from_object(text, (self._TOP_LEVEL_KEY,), "runlog")
        else:
            text = yamlc.remove_from_list(
                text, self._TOP_LEVEL_KEY, self._LIST_IDENTIFIER, "runlog"
            )

        self.SETTINGS_PATH.write_text(text, encoding="utf-8")
