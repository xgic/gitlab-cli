"""``xgic gitlab info`` — module status stub (B6a bootstrap)."""

from __future__ import annotations

import argparse
import json

from xgic.cli.gitlab import __version__
from xgic.cli.utils.output import print_info, print_success


def run_info(args: argparse.Namespace) -> int:
    """Print GitLab CLI module identity and planned capabilities."""
    payload = {
        "module": "xgic.cli.gitlab",
        "package": "xgic-gitlab-cli",
        "version": __version__,
        "status": "bootstrap",
        "commands": ["info"],
        "planned": [
            "backup",
            "restore",
            "health",
        ],
        "repository": "https://github.com/xgic/gitlab-cli",
        "graph_client": "https://github.com/xgic/gitlab-graphql",
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
        return 0

    print_success(f"XGIC GitLab CLI {__version__} (bootstrap)")
    print_info("Namespace: xgic.cli.gitlab")
    print_info("Repo: https://github.com/xgic/gitlab-cli")
    print_info(
        "Planned: backup/restore/health (GraphQL via xgic-gitlab-graphql)"
    )
    print_info("Public-safe only — no private host defaults in this package")
    return 0
