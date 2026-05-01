"""Integration tests for the CLI dispatch layer.

All tests monkeypatch ``runlog_install.registry.get_host`` so no real filesystem
operations are performed — adapter-level tests live in test_claude_code.py and
test_cursor.py.
"""

from __future__ import annotations

import pytest

from runlog_install import cli


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
# Tests — delegated mode (claude, cursor)
# ---------------------------------------------------------------------------

def test_install_delegated_no_api_key_needed(monkeypatch, capsys):
    """install --target claude (delegated) succeeds without any API key."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.delenv("RUNLOG_API_KEY", raising=False)

    rc = cli.main(["install", "--target", "claude"])

    assert rc == 0
    assert fake_host.install_calls == [None]
    captured = capsys.readouterr()
    assert "npx add-mcp" in captured.out


def test_install_delegated_ignores_api_key_arg(monkeypatch, capsys):
    """install --target claude --api-key ... (delegated) still passes None to install."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["install", "--target", "claude", "--api-key", "sk-ignored"])

    assert rc == 0
    # Delegated hosts receive None regardless of --api-key
    assert fake_host.install_calls == [None]
    captured = capsys.readouterr()
    assert "npx add-mcp" in captured.out


def test_install_delegated_message_contains_npx_add_mcp(monkeypatch, capsys):
    """Delegated post-install message mentions `npx add-mcp`."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    cli.main(["install", "--target", "cursor"])

    captured = capsys.readouterr()
    assert "npx add-mcp" in captured.out
    assert "https://api.runlog.org/mcp" in captured.out


# ---------------------------------------------------------------------------
# Tests — fallback mode (future hosts)
# ---------------------------------------------------------------------------

def test_install_with_api_key_arg(monkeypatch):
    """install --target X --api-key sk-test-123 (fallback) → install called with that key."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["install", "--target", "claude", "--api-key", "sk-test-123"])

    assert rc == 0
    assert fake_host.install_calls == ["sk-test-123"]


def test_install_uses_env_var(monkeypatch):
    """install --target X with RUNLOG_API_KEY set (fallback) → install called with env value."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.setenv("RUNLOG_API_KEY", "env-key-abc")

    rc = cli.main(["install", "--target", "cursor"])

    assert rc == 0
    assert fake_host.install_calls == ["env-key-abc"]


def test_install_empty_interactive_input_returns_nonzero(monkeypatch, capsys):
    """install with no key and no env (fallback), simulated empty input → non-zero + URL printed."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.delenv("RUNLOG_API_KEY", raising=False)
    # Simulate the user pressing Enter with no input.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "")

    rc = cli.main(["install", "--target", "claude"])

    assert rc != 0
    captured = capsys.readouterr()
    assert "runlog.org/register" in captured.err
    assert fake_host.install_calls == []


def test_install_fallback_message_no_npx(monkeypatch, capsys):
    """Fallback post-install message does NOT mention npx add-mcp."""
    fake_cls, fake_host = _make_fake_host_class("fallback")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    cli.main(["install", "--target", "claude", "--api-key", "sk-abc"])

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


def test_uninstall_claude(monkeypatch, capsys):
    """uninstall --target claude → host.uninstall() called, returns 0."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["uninstall", "--target", "claude"])

    assert rc == 0
    assert fake_host.uninstall_calls == 1
    captured = capsys.readouterr()
    assert "Uninstalled Runlog from" in captured.out


def test_uninstall_cursor(monkeypatch, capsys):
    """uninstall --target cursor → host.uninstall() called, returns 0."""
    fake_cls, fake_host = _make_fake_host_class("delegated")
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["uninstall", "--target", "cursor"])

    assert rc == 0
    assert fake_host.uninstall_calls == 1
    captured = capsys.readouterr()
    assert "Uninstalled Runlog from" in captured.out


def test_no_subcommand_exits_nonzero():
    """CLI without subcommand → SystemExit (argparse) with non-zero code."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code != 0
