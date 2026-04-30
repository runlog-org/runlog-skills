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

class _FakeHost:
    """Minimal Host implementation that records calls."""

    name = "Fake Host"
    target_key = "fake"

    def __init__(self):
        self.install_calls: list[str] = []
        self.uninstall_calls: int = 0

    def install(self, api_key: str) -> None:
        self.install_calls.append(api_key)

    def uninstall(self) -> None:
        self.uninstall_calls += 1


def _make_fake_host_class() -> tuple[type, _FakeHost]:
    """Return a fake Host *class* and the shared instance it will produce."""
    instance = _FakeHost()

    class FakeHostClass:
        name = instance.name
        target_key = instance.target_key

        def __new__(cls):
            return instance

    return FakeHostClass, instance


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_install_with_api_key_arg(monkeypatch):
    """install --target claude --api-key sk-test-123 → install called with that key."""
    fake_cls, fake_host = _make_fake_host_class()
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["install", "--target", "claude", "--api-key", "sk-test-123"])

    assert rc == 0
    assert fake_host.install_calls == ["sk-test-123"]


def test_install_uses_env_var(monkeypatch):
    """install --target cursor with RUNLOG_API_KEY set → install called with env value."""
    fake_cls, fake_host = _make_fake_host_class()
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.setenv("RUNLOG_API_KEY", "env-key-abc")
    # Ensure --api-key is absent so env path is exercised.
    monkeypatch.delenv("RUNLOG_API_KEY", raising=False)
    monkeypatch.setenv("RUNLOG_API_KEY", "env-key-abc")

    rc = cli.main(["install", "--target", "cursor"])

    assert rc == 0
    assert fake_host.install_calls == ["env-key-abc"]


def test_install_empty_interactive_input_returns_nonzero(monkeypatch, capsys):
    """install with no key and no env, simulated empty input → non-zero + URL printed."""
    fake_cls, fake_host = _make_fake_host_class()
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)
    monkeypatch.delenv("RUNLOG_API_KEY", raising=False)
    # Simulate the user pressing Enter with no input.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "")

    rc = cli.main(["install", "--target", "claude"])

    assert rc != 0
    captured = capsys.readouterr()
    assert "runlog.org/register" in captured.err
    assert fake_host.install_calls == []


def test_install_unknown_target_returns_nonzero(monkeypatch, capsys):
    """install --target unknown → non-zero, error lists available targets."""
    # Raise KeyError as the real registry does for unknown names.
    def _raise(name):
        raise KeyError(f"Unknown target {name!r}. Available targets: claude, cursor")

    monkeypatch.setattr("runlog_install.registry.get_host", _raise)

    # argparse itself rejects values not in `choices`, so we bypass that by
    # patching the choices list too.
    original_build = cli._build_parser

    def _patched_build():
        import argparse as _ap
        p = original_build()
        # Rewrite choices to allow "unknown" through argparse so the registry
        # path is exercised.
        return p

    # Instead, call main() with a choices-valid but registry-rejected value.
    # Use a direct registry patch approach: pretend "claude" hits KeyError.
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
    fake_cls, fake_host = _make_fake_host_class()
    monkeypatch.setattr("runlog_install.registry.get_host", lambda name: fake_cls)

    rc = cli.main(["uninstall", "--target", "claude"])

    assert rc == 0
    assert fake_host.uninstall_calls == 1
    captured = capsys.readouterr()
    assert "Uninstalled Runlog from" in captured.out


def test_uninstall_cursor(monkeypatch, capsys):
    """uninstall --target cursor → host.uninstall() called, returns 0."""
    fake_cls, fake_host = _make_fake_host_class()
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
