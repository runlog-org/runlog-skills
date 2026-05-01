"""Integration tests for the CLI dispatch layer.

All tests monkeypatch ``runlog_install.registry.get_host`` so no real filesystem
operations are performed — adapter-level tests live in test_claude_code.py and
test_cursor.py.
"""

from __future__ import annotations

import pytest

from runlog_install import cli
from runlog_install.hosts import HOSTS


# ---------------------------------------------------------------------------
# Fake Host helpers
# ---------------------------------------------------------------------------

class _FakeDelegatedHost:
    """Minimal delegated Host implementation that records calls."""

    name = "Fake Delegated Host"
    target_key = "fake-delegated"
    mode = "delegated"

    def __init__(self):
        self.install_calls: list = []
        self.uninstall_calls: int = 0

    def install(self, api_key=None) -> None:
        self.install_calls.append(api_key)

    def uninstall(self) -> None:
        self.uninstall_calls += 1


class _FakeFallbackHost:
    """Minimal fallback Host implementation that records calls."""

    name = "Fake Fallback Host"
    target_key = "fake-fallback"
    mode = "fallback"

    def __init__(self):
        self.install_calls: list = []
        self.uninstall_calls: int = 0

    def install(self, api_key=None) -> None:
        self.install_calls.append(api_key)

    def uninstall(self) -> None:
        self.uninstall_calls += 1

    def post_install_hint(self) -> str | None:
        return None


def _make_fake_host_class(host_mode: str = "delegated") -> tuple[type, object]:
    """Return a fake Host *class* and the shared instance it will produce."""
    base_cls = _FakeDelegatedHost if host_mode == "delegated" else _FakeFallbackHost
    instance = base_cls()

    class FakeHostClass:
        name = instance.name
        target_key = instance.target_key
        mode = instance.mode

        def __new__(cls):
            return instance

    return FakeHostClass, instance


# ---------------------------------------------------------------------------
# Tests — delegated mode (claude, cursor, zed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target", ["claude", "cursor", "zed"])
def test_install_delegated_no_api_key_needed(monkeypatch, capsys, target):
    """install --target <delegated> succeeds without any API key."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.delenv("RUNLOG_API_KEY", raising=False)

    rc = cli.main(["install", "--target", target])

    assert rc == 0
    assert fake_host.install_calls == [None]
    captured = capsys.readouterr()
    assert "npx add-mcp" in captured.out


@pytest.mark.parametrize("target", ["claude", "cursor", "zed"])
def test_install_delegated_ignores_api_key_arg(monkeypatch, capsys, target):
    """install --target <delegated> --api-key ... still passes None to install."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["install", "--target", target, "--api-key", "sk-ignored"])

    assert rc == 0
    # Delegated hosts receive None regardless of --api-key
    assert fake_host.install_calls == [None]
    captured = capsys.readouterr()
    assert "npx add-mcp" in captured.out


@pytest.mark.parametrize("target", ["claude", "cursor", "zed"])
def test_install_delegated_message_contains_npx_add_mcp(monkeypatch, capsys, target):
    """Delegated post-install message mentions `npx add-mcp`."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    cli.main(["install", "--target", target])

    captured = capsys.readouterr()
    assert "npx add-mcp" in captured.out
    assert "https://api.runlog.org/mcp" in captured.out


# ---------------------------------------------------------------------------
# Tests — fallback mode (windsurf, copilot)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target", ["windsurf", "copilot"])
def test_install_with_api_key_arg(monkeypatch, target):
    """install --target <fallback> --api-key sk-test-123 → install called with that key."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["install", "--target", target, "--api-key", "sk-test-123"])

    assert rc == 0
    assert fake_host.install_calls == ["sk-test-123"]


@pytest.mark.parametrize("target", ["windsurf", "copilot"])
def test_install_uses_env_var(monkeypatch, target):
    """install --target <fallback> with RUNLOG_API_KEY set → install called with env value."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.setenv("RUNLOG_API_KEY", "env-key-abc")

    rc = cli.main(["install", "--target", target])

    assert rc == 0
    assert fake_host.install_calls == ["env-key-abc"]


@pytest.mark.parametrize("target", ["windsurf", "copilot"])
def test_install_empty_interactive_input_returns_nonzero(monkeypatch, capsys, target):
    """install with no key and no env (fallback), simulated empty input → non-zero + URL printed."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.delenv("RUNLOG_API_KEY", raising=False)
    # Simulate the user pressing Enter with no input.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "")

    rc = cli.main(["install", "--target", target])

    assert rc != 0
    captured = capsys.readouterr()
    assert "runlog.org/register" in captured.err
    assert fake_host.install_calls == []


@pytest.mark.parametrize("target", ["windsurf", "copilot"])
def test_install_fallback_message_no_npx(monkeypatch, capsys, target):
    """Fallback post-install message does NOT mention npx add-mcp."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    cli.main(["install", "--target", target, "--api-key", "sk-abc"])

    captured = capsys.readouterr()
    assert "npx add-mcp" not in captured.out
    assert "Restart your editor" in captured.out


# ---------------------------------------------------------------------------
# Tests — shared / registry
# ---------------------------------------------------------------------------

def test_install_unknown_target_returns_nonzero(monkeypatch, capsys):
    """install --target X where registry rejects X → non-zero + 'Available targets' on stderr."""
    # argparse already rejects values outside `choices`, so simulate the
    # registry-rejection path by making get_host raise for a choices-valid name.
    monkeypatch.setattr(
        "runlog_install.registry.get_host",
        lambda name: (_ for _ in ()).throw(
            KeyError(f"Unknown target {name!r}. Available targets: claude, cursor")
        ),
    )

    rc = cli.main(["install", "--target", "claude", "--api-key", "x"])

    assert rc != 0
    captured = capsys.readouterr()
    assert "Available targets" in captured.err


@pytest.mark.parametrize("target", ["aider", "claude", "continue", "copilot", "cursor", "windsurf", "zed"])
def test_uninstall_all_targets(monkeypatch, capsys, target):
    """uninstall --target <any> → host.uninstall() called, returns 0."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["uninstall", "--target", target])

    assert rc == 0
    assert fake_host.uninstall_calls == 1
    captured = capsys.readouterr()
    assert "Uninstalled Runlog from" in captured.out


def test_no_subcommand_exits_nonzero():
    """CLI without subcommand → SystemExit (argparse) with non-zero code."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# Tests — help text grouping + registry/CLI sync
# ---------------------------------------------------------------------------

def test_help_groups_hosts_by_mode():
    """install --help output groups hosts by mode (Delegated / Fallback)."""
    parser = cli._build_parser()
    # Format help for the install subcommand by finding it through subparsers.
    # We can do this by calling parse_args with --help captured via SystemExit,
    # but it's simpler to re-invoke _build_parser and pull the subparser directly.
    import io, contextlib

    buf = io.StringIO()
    # parse_args(["install", "--help"]) raises SystemExit; capture print_help instead.
    # Walk the _subparsers to find the install parser.
    install_parser = None
    for action in parser._actions:
        if hasattr(action, "_name_parser_map"):
            install_parser = action._name_parser_map.get("install")
            break

    assert install_parser is not None, "install subparser not found"
    help_text = install_parser.format_help()

    assert "Delegated hosts" in help_text
    assert "Fallback hosts" in help_text
    # Delegated group lists the three delegated hosts
    assert "claude" in help_text
    assert "cursor" in help_text
    assert "zed" in help_text
    # Fallback group lists the four fallback hosts
    assert "windsurf" in help_text
    assert "copilot" in help_text
    assert "aider" in help_text
    assert "continue" in help_text
    # Delegated section appears before Fallback section
    assert help_text.index("Delegated hosts") < help_text.index("Fallback hosts")


def test_targets_complete():
    """_TARGETS and HOSTS keys must be identical — catches future drift."""
    assert set(cli._TARGETS) == set(HOSTS.keys())


def test_install_aider_prints_read_hint(monkeypatch, capsys):
    """install --target aider prints the manual `read:` wiring hint."""
    fake_cls, fake_host = _make_fake_host_class("fallback")

    # Override post_install_hint on the instance to return the Aider-specific hint.
    # The real AiderHost.post_install_hint() returns this string; we replicate it
    # here so the CLI test doesn't depend on importing AiderHost directly.
    _AIDER_HINT = (
        "Aider note: add `~/.aider/runlog.md` to the `read:` list in "
        "`~/.aider.conf.yml` so Aider auto-loads the skill."
    )
    fake_host.post_install_hint = lambda: _AIDER_HINT

    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["install", "--target", "aider", "--api-key", "sk-runlog-test"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "Aider note" in captured.out
    assert "~/.aider/runlog.md" in captured.out


@pytest.mark.parametrize("target", ["windsurf", "copilot", "continue"])
def test_install_non_aider_omits_read_hint(monkeypatch, capsys, target):
    """The Aider-specific `read:` hint must not leak into other fallback hosts."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["install", "--target", target, "--api-key", "sk-runlog-test"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "Aider note" not in captured.out
    assert "~/.aider/runlog.md" not in captured.out
