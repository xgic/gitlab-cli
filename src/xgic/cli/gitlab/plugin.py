"""Register ``xgic.cli.gitlab`` subcommands on the core ``xgic`` CLI.

All product commands live under the ``gitlab`` group for domain ownership::

    xgic gitlab info
    xgic gitlab health
    xgic gitlab backup
    xgic gitlab restore
    xgic gitlab --help
"""

from __future__ import annotations

import argparse

from xgic.cli.gitlab.commands.backup import run_backup
from xgic.cli.gitlab.commands.health import run_health
from xgic.cli.gitlab.commands.info import run_info
from xgic.cli.gitlab.commands.restore import run_restore
from xgic.cli.gitlab.config import add_common_ops_args


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

    health = gitlab_sub.add_parser(
        "health",
        help="Check Compose services and optional GitLab HTTP health",
    )
    add_common_ops_args(health)
    health.set_defaults(func=run_health)

    backup = gitlab_sub.add_parser(
        "backup",
        help="Create a GitLab EE backup (docker compose exec gitlab-backup create)",
    )
    add_common_ops_args(backup)
    backup.set_defaults(func=run_backup)

    restore = gitlab_sub.add_parser(
        "restore",
        help="Restore a GitLab EE backup (destructive; requires --yes)",
    )
    restore.add_argument(
        "backup_id",
        help="Backup id (timestamp prefix; not the full tar filename)",
    )
    restore.add_argument(
        "--yes",
        action="store_true",
        help="Confirm destructive restore",
    )
    add_common_ops_args(restore)
    restore.set_defaults(func=run_restore)
