"""CLI entry point for the Runlog installer."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from typing import Sequence

from runlog_install import registry

_TARGETS = ("claude", "cursor")
_REGISTER_URL = "https://runlog.org/register"


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
    )
    uninstall_p.add_argument(
        "--target",
        required=True,
        choices=_TARGETS,
        metavar="{" + ",".join(_TARGETS) + "}",
        help="AI coding host to uninstall from.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "install":
        try:
            host_cls = registry.get_host(args.target)
            host = host_cls()

            # Resolve API key: CLI arg > env var > interactive prompt.
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
            print(f"Installed Runlog skill + MCP block for {host.name}.")
            print("Restart your editor for the changes to take effect.")
            return 0

        except (FileNotFoundError, KeyError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "uninstall":
        try:
            host_cls = registry.get_host(args.target)
            host = host_cls()
            host.uninstall()
            print(f"Uninstalled Runlog from {host.name}.")
            return 0

        except (FileNotFoundError, KeyError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    # Should be unreachable (argparse enforces required subcommand).
    parser.print_help(sys.stderr)
    return 2
