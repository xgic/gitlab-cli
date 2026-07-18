"""Register ``xgic.cli.gitlab`` subcommands on the core ``xgic`` CLI.

All product commands live under the ``gitlab`` group for domain ownership::

    xgic gitlab info
    xgic gitlab --help
"""

from __future__ import annotations

import argparse

from xgic.cli.gitlab.commands.info import run_info


def register(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Entry point: ``xgic.cli.commands`` → GitLab product commands."""
    gitlab = subparsers.add_parser(
        "gitlab",
        help="GitLab product commands",
    )
    gitlab_sub = gitlab.add_subparsers(
        dest="gitlab_command",
        help="GitLab action",
        metavar="ACTION",
        required=True,
    )

    info = gitlab_sub.add_parser(
        "info",
        help="Show GitLab CLI module version and status",
    )
    info.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    info.set_defaults(func=run_info)
