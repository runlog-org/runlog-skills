"""CLI entry point for the Runlog installer."""

from __future__ import annotations

import argparse
import getpass
import os
import platform
import shutil
import subprocess
import sys

from runlog_install.hosts import HOSTS

_TARGETS = tuple(sorted(HOSTS))
_REGISTER_URL = "https://runlog.org/register"
_VERIFIER_RELEASE_BASE = (
    "https://github.com/runlog-org/runlog-verifier/releases/latest/download"
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runlog",
        description="Install or uninstall the Runlog MCP server for an AI coding host.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # --- install ---
    install_p = subparsers.add_parser(
        "install",
        help="Write the Runlog skill file and register the MCP server with the host.",
        description=(
            "Install Runlog into a coding host.\n\n"
            "Delegated hosts (skill placement only — wire MCP via `npx add-mcp`):\n"
            "  claude, cursor, zed\n\n"
            "Fallback hosts (skill placement + direct MCP-config edit):\n"
            "  aider, continue, copilot, windsurf\n\n"
            "The four hosts add-mcp covers natively (claude, cursor, cline, zed)\n"
            "use delegated mode; hosts add-mcp doesn't reach use fallback.\n"
            "JetBrains AI Assistant is not yet supported (deferred — its config\n"
            "format is not yet pinned down to a JSON path; likely XML, out of\n"
            "scope for the stdlib-only installer)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    install_p.add_argument(
        "--target",
        required=True,
        choices=_TARGETS,
        metavar="{" + ",".join(_TARGETS) + "}",
        help="AI coding host to install into.",
    )
    install_p.add_argument(
        "--api-key",
        metavar="VALUE",
        default=None,
        help="Runlog API key (written into the skill file).",
    )

    # --- uninstall ---
    uninstall_p = subparsers.add_parser(
        "uninstall",
        help="Remove the Runlog skill file and MCP server block from the host.",
        description=(
            "Uninstall Runlog from a coding host.\n\n"
            "Delegated hosts: claude, cursor, zed\n"
            "Fallback hosts:  aider, continue, copilot, windsurf"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    uninstall_p.add_argument(
        "--target",
        required=True,
        choices=_TARGETS,
        metavar="{" + ",".join(_TARGETS) + "}",
        help="AI coding host to uninstall from.",
    )

    # --- register ---
    register_p = subparsers.add_parser(
        "register",
        help="Register an Ed25519 keypair against the Runlog server (delegates to runlog-verifier).",
    )
    register_p.add_argument(
        "--email",
        required=True,
        metavar="ADDR",
        help="Email address to associate with the registered key (verification mail goes here).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "install":
        try:
            host = HOSTS[args.target]()

            if host.mode == "delegated":
                # Delegated hosts don't need an API key — skip resolution.
                api_key = None
            else:
                # Fallback hosts: resolve API key from CLI arg > env var > prompt.
                if args.api_key:
                    api_key = args.api_key
                elif os.environ.get("RUNLOG_API_KEY"):
                    api_key = os.environ["RUNLOG_API_KEY"]
                else:
                    api_key = getpass.getpass(
                        f"Runlog API key ({_REGISTER_URL} if you don't have one): "
                    )
                    if not api_key:
                        print(
                            f"No API key provided. Register at {_REGISTER_URL}",
                            file=sys.stderr,
                        )
                        return 1

            host.install(api_key)

            if host.mode == "delegated":
                print(f"Installed Runlog skill for {host.name}.")
                print(
                    "Run `npx add-mcp https://api.runlog.org/mcp` to wire up the MCP server,"
                    " then restart your editor."
                )
            else:
                print(f"Installed Runlog skill + MCP block for {host.name}.")
                print("Restart your editor for the changes to take effect.")
                hint = host.post_install_hint()
                if hint:
                    print(hint)

            return 0

        except (FileNotFoundError, KeyError, OSError, ValueError, RuntimeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "uninstall":
        try:
            host = HOSTS[args.target]()
            host.uninstall()
            print(f"Uninstalled Runlog from {host.name}.")
            return 0

        except (FileNotFoundError, KeyError, OSError, ValueError, RuntimeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "register":
        return _handle_register(args.email)

    # Should be unreachable (argparse enforces required subcommand).
    parser.print_help(sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Register helpers
# ---------------------------------------------------------------------------


def _detect_platform_slug() -> tuple[str, bool]:
    """Return (slug, is_guess). is_guess is True if we couldn't match cleanly."""
    system = platform.system()
    machine = platform.machine().lower()
    matrix: dict[tuple[str, str], str] = {
        ("Linux", "x86_64"): "linux-amd64",
        ("Linux", "aarch64"): "linux-arm64",
        ("Linux", "arm64"): "linux-arm64",  # some distros report arm64
        ("Darwin", "x86_64"): "darwin-amd64",
        ("Darwin", "arm64"): "darwin-arm64",
    }
    slug = matrix.get((system, machine))
    if slug is None:
        return "linux-amd64", True
    return slug, False


def _handle_register(email: str) -> int:
    """Shell out to runlog-verifier register, or print an install hint and exit 2."""
    verifier = shutil.which("runlog-verifier")
    if verifier is None:
        slug, is_guess = _detect_platform_slug()
        guess_note = (
            "  (detected platform looked unfamiliar — confirm against "
            "https://github.com/runlog-org/runlog-verifier/releases/latest)\n"
            if is_guess
            else ""
        )
        print(
            f"runlog-verifier not found on PATH.\n"
            f"Install:\n"
            f"  curl -fLO {_VERIFIER_RELEASE_BASE}/runlog-verifier-{slug}\n"
            f"  curl -fLO {_VERIFIER_RELEASE_BASE}/SHA256SUMS\n"
            f"  sha256sum --check --ignore-missing SHA256SUMS\n"
            f"  install -m 0755 runlog-verifier-{slug} ~/.local/bin/runlog-verifier\n"
            f"{guess_note}\n"
            f"Then re-run: runlog register --email {email}",
            file=sys.stderr,
        )
        return 2

    try:
        proc = subprocess.run(
            [verifier, "register", "--email", email],
            check=False,
        )
        return proc.returncode
    except OSError as exc:
        print(f"Error invoking runlog-verifier: {exc}", file=sys.stderr)
        return 1
