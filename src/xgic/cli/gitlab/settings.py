"""Pydantic configuration for ``xgic gitlab``.

The model is the schema. A config file is optional. Command flags override
it, and environment variables override the file for the shared Docker
Compose settings. An API token is never a field in this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from xgic.cli.gitlab.config import (
    DEFAULT_BACKUP_DIR,
    DEFAULT_COMPOSE_FILE,
    DEFAULT_GITLAB_SERVICE,
    DEFAULT_PROJECT_NAME,
    DEFAULT_XGIC_SERVICE,
)

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "gitlab-cli.schema.json"
ComponentName = Literal["registry", "lfs", "packages"]
EnvironmentName = Literal["development", "staging", "production"]


class ConfigError(Exception):
    """The GitLab CLI config file is missing or invalid."""


class GitLabCliConfig(BaseModel):
    """Settings an operator or automation can store as JSON."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    environment: EnvironmentName | None = None
    organization: str = ""
    compose_file: str = DEFAULT_COMPOSE_FILE
    project_name: str = DEFAULT_PROJECT_NAME
    gitlab_service: str = DEFAULT_GITLAB_SERVICE
    xgic_service: str = DEFAULT_XGIC_SERVICE
    backup_dir: str = DEFAULT_BACKUP_DIR
    gitlab_url: str | None = None
    secrets_file: str | None = None
    config_file: str | None = None
    secrets_dest: str | None = None
    config_dest: str | None = None
    allow_missing: list[ComponentName] = Field(default_factory=list)
    dry_run: bool = False

    def to_json(self) -> str:
        return self.model_dump_json(indent=2) + "\n"


def default_config_path() -> Path | None:
    """Return the user config when it exists. A missing file uses defaults."""
    path = Path.home() / ".config" / "xgic" / "gitlab.json"
    if path.is_file():
        return path
    return None


def load_cli_config(path: Path | None) -> GitLabCliConfig:
    """Validate one config file. ``None`` means the built-in defaults."""
    if path is None:
        return GitLabCliConfig()
    if not path.is_file():
        raise ConfigError(f"missing config {path}")
    try:
        return GitLabCliConfig.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        message = exc.errors()[0]["msg"]
        raise ConfigError(f"invalid gitlab config: {message}") from exc


def gitlab_cli_schema() -> dict[str, Any]:
    """JSON Schema generated from :class:`GitLabCliConfig`."""
    document: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_PATH.name,
    }
    document.update(GitLabCliConfig.model_json_schema())
    return document


def schema_text() -> str:
    return json.dumps(gitlab_cli_schema(), indent=4) + "\n"
