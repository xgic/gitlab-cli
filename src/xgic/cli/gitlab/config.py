"""Public-safe GitLab ops configuration (env + flags; no private defaults)."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

# Environment keys (operators set these; package never ships private hosts/tokens).
ENV_GITLAB_URL = "GITLAB_URL"
ENV_GITLAB_TOKEN = "GITLAB_TOKEN"
ENV_COMPOSE_FILE = "XGIC_GITLAB_COMPOSE_FILE"
ENV_COMPOSE_PROJECT = "XGIC_GITLAB_COMPOSE_PROJECT"
ENV_GITLAB_SERVICE = "XGIC_GITLAB_EE_SERVICE"
ENV_XGIC_SERVICE = "XGIC_GITLAB_ORCH_SERVICE"
ENV_BACKUP_DIR = "XGIC_GITLAB_BACKUP_DIR"

DEFAULT_COMPOSE_FILE = "docker-compose.yml"
DEFAULT_PROJECT_NAME = "xgic-gitlab"
DEFAULT_GITLAB_SERVICE = "gitlab-ee"
DEFAULT_XGIC_SERVICE = "xgic-gitlab"
DEFAULT_BACKUP_DIR = "./gitlab-backups"


@dataclass(frozen=True)
class GitLabOpsConfig:
    """Resolved ops settings for Compose-based GitLab stacks."""

    compose_file: str
    project_name: str
    gitlab_service: str
    xgic_service: str
    backup_dir: str
    gitlab_url: str | None
    token: str | None
    dry_run: bool

    def public_dict(self) -> dict[str, object]:
        """Serializable view safe for logs/JSON (token redacted)."""
        return {
            "compose_file": self.compose_file,
            "project_name": self.project_name,
            "gitlab_service": self.gitlab_service,
            "xgic_service": self.xgic_service,
            "backup_dir": self.backup_dir,
            "gitlab_url": self.gitlab_url,
            "token_set": bool(self.token),
            "dry_run": self.dry_run,
        }


def _first(*values: str | None) -> str | None:
    for v in values:
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return None


def resolve_config(args: argparse.Namespace) -> GitLabOpsConfig:
    """Build config from argparse namespace and process environment."""
    return GitLabOpsConfig(
        compose_file=_first(
            getattr(args, "compose_file", None),
            os.environ.get(ENV_COMPOSE_FILE),
        )
        or DEFAULT_COMPOSE_FILE,
        project_name=_first(
            getattr(args, "project", None),
            os.environ.get(ENV_COMPOSE_PROJECT),
        )
        or DEFAULT_PROJECT_NAME,
        gitlab_service=_first(
            getattr(args, "gitlab_service", None),
            os.environ.get(ENV_GITLAB_SERVICE),
        )
        or DEFAULT_GITLAB_SERVICE,
        xgic_service=_first(
            getattr(args, "xgic_service", None),
            os.environ.get(ENV_XGIC_SERVICE),
        )
        or DEFAULT_XGIC_SERVICE,
        backup_dir=_first(
            getattr(args, "backup_dir", None),
            os.environ.get(ENV_BACKUP_DIR),
        )
        or DEFAULT_BACKUP_DIR,
        gitlab_url=_first(
            getattr(args, "url", None),
            os.environ.get(ENV_GITLAB_URL),
        ),
        token=_first(
            getattr(args, "token", None),
            os.environ.get(ENV_GITLAB_TOKEN),
        ),
        dry_run=bool(getattr(args, "dry_run", False)),
    )


def add_common_ops_args(parser: argparse.ArgumentParser) -> None:
    """Shared flags for health / backup / restore."""
    parser.add_argument(
        "--compose-file",
        dest="compose_file",
        default=None,
        help=f"Compose file path (env {ENV_COMPOSE_FILE}; default {DEFAULT_COMPOSE_FILE})",
    )
    parser.add_argument(
        "--project",
        dest="project",
        default=None,
        help=f"Compose project name (env {ENV_COMPOSE_PROJECT}; default {DEFAULT_PROJECT_NAME})",
    )
    parser.add_argument(
        "--gitlab-service",
        dest="gitlab_service",
        default=None,
        help=f"GitLab EE service name (env {ENV_GITLAB_SERVICE}; default {DEFAULT_GITLAB_SERVICE})",
    )
    parser.add_argument(
        "--xgic-service",
        dest="xgic_service",
        default=None,
        help=f"Orchestration service name (env {ENV_XGIC_SERVICE}; default {DEFAULT_XGIC_SERVICE})",
    )
    parser.add_argument(
        "--backup-dir",
        dest="backup_dir",
        default=None,
        help=f"Host backup directory hint (env {ENV_BACKUP_DIR}; default {DEFAULT_BACKUP_DIR})",
    )
    parser.add_argument(
        "--url",
        dest="url",
        default=None,
        help=f"GitLab base URL for HTTP checks (env {ENV_GITLAB_URL}; no default host)",
    )
    parser.add_argument(
        "--token",
        dest="token",
        default=None,
        help=f"API token when needed (env {ENV_GITLAB_TOKEN}; never logged)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without executing destructive or mutating steps",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
