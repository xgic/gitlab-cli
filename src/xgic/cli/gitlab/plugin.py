"""Register ``xgic.cli.gitlab`` subcommands on the core ``xgic`` CLI.

All product commands live under the ``gitlab`` group for domain ownership::

    xgic gitlab info
    xgic gitlab health
    xgic gitlab backup
    xgic gitlab restore
    xgic gitlab --help

Missing ACTION prints full usage (not a short argparse required-args error).
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
        description="GitLab ops commands for the modular XGIC CLI.",
    )
    gitlab_sub = gitlab.add_subparsers(
        dest="gitlab_command",
        help="GitLab action",
        metavar="ACTION",
        required=False,
    )

    def _missing_action(_args: argparse.Namespace) -> int:
        gitlab.print_help()
        return 2

    gitlab.set_defaults(func=_missing_action)

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
        help="Create a GitLab EE backup pair (.tar.zst and .sha256)",
    )
    backup.add_argument(
        "--secrets-file",
        default=None,
        help="Live gitlab-secrets.json to copy into the archive. The file is not modified.",
    )
    backup.add_argument(
        "--config-file",
        default=None,
        help="Live gitlab.rb to copy into the archive. The file is not modified.",
    )
    backup.add_argument(
        "--allow-missing",
        default=None,
        help=(
            "Comma-separated components that may be absent from the GitLab "
            "tar: registry, lfs, packages. Default: none, so all three are "
            "required. GitLab SKIP can omit them, and object storage does "
            "not put them in the tar."
        ),
    )
    backup.add_argument(
        "--environment",
        choices=("development", "staging", "production"),
        default=None,
        help="Recorded environment. Default comes from the config file, or is unset.",
    )
    backup.add_argument(
        "--apply",
        action="store_true",
        help="Run the backup. Overrides a config file that sets dry_run.",
    )
    add_common_ops_args(backup)
    backup.set_defaults(func=run_backup)

    restore = gitlab_sub.add_parser(
        "restore",
        help="Restore a GitLab EE backup pair (destructive; requires --yes)",
    )
    restore.add_argument(
        "--archive",
        default=None,
        help="Verified .tar.zst (default: latest pair in --backup-dir)",
    )
    restore.add_argument(
        "--secrets-dest",
        default=None,
        help=(
            "Write gitlab-secrets.json here from the verified archive "
            "during a confirmed restore (default: do not write it outside "
            "the extract directory)"
        ),
    )
    restore.add_argument(
        "--config-dest",
        default=None,
        help=(
            "Write gitlab.rb here from the verified archive during a "
            "confirmed restore (default: do not write it outside the "
            "extract directory)"
        ),
    )
    restore.add_argument(
        "--yes",
        action="store_true",
        help="Confirm destructive restore",
    )
    restore.add_argument(
        "--environment",
        choices=("development", "staging", "production"),
        default=None,
        help="Recorded environment. Default comes from the config file, or is unset.",
    )
    restore.add_argument(
        "--apply",
        action="store_true",
        help="Run the restore when --yes is set. Overrides a config file that sets dry_run.",
    )
    add_common_ops_args(restore)
    restore.set_defaults(func=run_restore)
