"""CLI entry point for the Runlog installer."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

_TARGETS = ("claude", "cursor")


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
        # TODO: look up host via registry, call host.install(api_key=args.api_key)
        print(
            f"[TODO] install --target {args.target} --api-key {args.api_key!r} "
            "— not yet implemented in scaffold; a follow-up task will fill this in."
        )
        return 0

    if args.command == "uninstall":
        # TODO: look up host via registry, call host.uninstall()
        print(
            f"[TODO] uninstall --target {args.target} "
            "— not yet implemented in scaffold; a follow-up task will fill this in."
        )
        return 0

    # Should be unreachable (argparse enforces required subcommand).
    parser.print_help(sys.stderr)
    return 2
