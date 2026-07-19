"""``xgic gitlab info`` — module status."""

from __future__ import annotations

import argparse
import json

from xgic.cli.gitlab import __version__
from xgic.cli.utils.output import print_info, print_success


def run_info(args: argparse.Namespace) -> int:
    """Print GitLab CLI module identity and capabilities."""
    payload = {
        "module": "xgic.cli.gitlab",
        "package": "xgic-gitlab-cli",
        "version": __version__,
        "status": "experimental",
        "commands": ["info", "health", "backup", "restore"],
        "planned": [
            "graphql-backed ops (optional extra)",
        ],
        "repository": "https://github.com/xgic/gitlab-cli",
        "graph_client": "https://github.com/xgic/gitlab-graphql",
        "config": {
            "compose_file": "XGIC_GITLAB_COMPOSE_FILE / --compose-file",
            "gitlab_url": "GITLAB_URL / --url (no default host)",
            "token": "GITLAB_TOKEN / --token (never logged)",
        },
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
        return 0

    print_success(f"XGIC GitLab CLI {__version__} (experimental)")
    print_info("Namespace: xgic.cli.gitlab")
    print_info("Repo: https://github.com/xgic/gitlab-cli")
    print_info("Commands: info, health, backup, restore")
    print_info("Config via env/flags only — no private host defaults")
    return 0
