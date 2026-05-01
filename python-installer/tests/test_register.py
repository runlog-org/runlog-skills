"""Tests for the `runlog register` subcommand and its helpers."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from runlog_install import cli


# ---------------------------------------------------------------------------
# _detect_platform_slug — parametrized unit tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "system, machine, expected_slug, expected_is_guess",
    [
        ("Linux", "x86_64", "linux-amd64", False),
        ("Linux", "aarch64", "linux-arm64", False),
        ("Darwin", "arm64", "darwin-arm64", False),
        ("Linux", "riscv64", "linux-amd64", True),
        ("Windows", "x86_64", "linux-amd64", True),
    ],
)
def test_detect_platform_slug(
    monkeypatch,
    system: str,
    machine: str,
    expected_slug: str,
    expected_is_guess: bool,
) -> None:
    monkeypatch.setattr("platform.system", lambda: system)
    monkeypatch.setattr("platform.machine", lambda: machine)

    slug, is_guess = cli._detect_platform_slug()

    assert slug == expected_slug
    assert is_guess == expected_is_guess


# ---------------------------------------------------------------------------
# Missing verifier — hint printed, exit 2
# ---------------------------------------------------------------------------

def test_register_missing_verifier_prints_hint_and_exits_2(monkeypatch, capsys) -> None:
    """When runlog-verifier is not on PATH, print an install hint and return 2."""
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    # Force a known platform so the slug is deterministic.
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "x86_64")

    rc = cli.main(["register", "--email", "user@example.com"])

    assert rc == 2
    captured = capsys.readouterr()
    assert "runlog-verifier not found" in captured.err
    assert "curl -fLO" in captured.err
    assert "linux-amd64" in captured.err
    assert "user@example.com" in captured.err


# ---------------------------------------------------------------------------
# Verifier present — shells out successfully
# ---------------------------------------------------------------------------

def test_register_present_verifier_shells_out(monkeypatch) -> None:
    """When runlog-verifier is on PATH and exits 0, main returns 0."""
    monkeypatch.setattr("shutil.which", lambda _cmd: "/fake/path/runlog-verifier")

    fake_completed = MagicMock()
    fake_completed.returncode = 0

    captured_calls: list = []

    def fake_run(cmd, **kwargs):
        captured_calls.append((cmd, kwargs))
        return fake_completed

    monkeypatch.setattr("subprocess.run", fake_run)

    rc = cli.main(["register", "--email", "user@example.com"])

    assert rc == 0
    assert len(captured_calls) == 1
    cmd, kwargs = captured_calls[0]
    assert cmd == ["/fake/path/runlog-verifier", "register", "--email", "user@example.com"]
    assert kwargs.get("check") is False


def test_register_verifier_failure_passes_through_exit_code(monkeypatch) -> None:
    """When runlog-verifier exits non-zero, main returns that same code."""
    monkeypatch.setattr("shutil.which", lambda _cmd: "/fake/path/runlog-verifier")

    fake_completed = MagicMock()
    fake_completed.returncode = 7
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_completed)

    rc = cli.main(["register", "--email", "user@example.com"])

    assert rc == 7


# ---------------------------------------------------------------------------
# OSError from subprocess.run
# ---------------------------------------------------------------------------

def test_register_subprocess_oserror_returns_1(monkeypatch, capsys) -> None:
    """An OSError from subprocess.run returns 1 and prints an error to stderr."""
    monkeypatch.setattr("shutil.which", lambda _cmd: "/fake/path/runlog-verifier")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("permission denied")),
    )

    rc = cli.main(["register", "--email", "user@example.com"])

    assert rc == 1
    captured = capsys.readouterr()
    assert "Error invoking runlog-verifier" in captured.err
    assert "permission denied" in captured.err


# ---------------------------------------------------------------------------
# --email is required
# ---------------------------------------------------------------------------

def test_register_email_required() -> None:
    """Invoking `runlog register` without --email exits with code 2 (argparse)."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["register"])
    assert exc_info.value.code == 2
