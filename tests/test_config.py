"""Tests for public-safe GitLab ops config resolution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from xgic.cli.gitlab.config import (
    DEFAULT_COMPOSE_FILE,
    DEFAULT_GITLAB_SERVICE,
    resolve_config,
)
from xgic.cli.gitlab.settings import (
    SCHEMA_PATH,
    ConfigError,
    GitLabCliConfig,
    gitlab_cli_schema,
    load_cli_config,
)


def test_resolve_defaults(monkeypatch) -> None:
    for key in (
        "GITLAB_URL",
        "GITLAB_TOKEN",
        "XGIC_GITLAB_COMPOSE_FILE",
        "XGIC_GITLAB_COMPOSE_PROJECT",
        "XGIC_GITLAB_EE_SERVICE",
        "XGIC_GITLAB_ORCH_SERVICE",
        "XGIC_GITLAB_BACKUP_DIR",
    ):
        monkeypatch.delenv(key, raising=False)

    ns = argparse.Namespace(
        compose_file=None,
        project=None,
        gitlab_service=None,
        xgic_service=None,
        backup_dir=None,
        url=None,
        token=None,
        dry_run=False,
    )
    cfg = resolve_config(ns)
    assert cfg.compose_file == DEFAULT_COMPOSE_FILE
    assert cfg.gitlab_service == DEFAULT_GITLAB_SERVICE
    assert cfg.gitlab_url is None
    assert cfg.token is None
    assert cfg.allow_missing == ()
    assert cfg.dry_run is False


def test_config_file_fills_missing_flags(tmp_path: Path) -> None:
    path = tmp_path / "gitlab.json"
    path.write_text(
        json.dumps(
            {
                "environment": "production",
                "organization": "example",
                "backup_dir": "/var/backups/gitlab",
                "secrets_file": "/etc/gitlab/gitlab-secrets.json",
                "config_file": "/etc/gitlab/gitlab.rb",
                "allow_missing": ["registry"],
                "dry_run": True,
                "gitlab_url": "https://gitlab.example",
            }
        ),
        encoding="utf-8",
    )
    cfg = resolve_config(
        argparse.Namespace(
            config=str(path),
            compose_file=None,
            project=None,
            gitlab_service=None,
            xgic_service=None,
            backup_dir=None,
            url=None,
            token=None,
            dry_run=False,
            apply=False,
            secrets_file=None,
            config_file=None,
            allow_missing=None,
            environment=None,
        )
    )
    assert cfg.backup_dir == "/var/backups/gitlab"
    assert cfg.environment == "production"
    assert cfg.organization == "example"
    assert cfg.secrets_file == "/etc/gitlab/gitlab-secrets.json"
    assert cfg.allow_missing == ("registry.tar.gz",)
    assert cfg.dry_run is True
    assert cfg.gitlab_url == "https://gitlab.example"
    assert cfg.token is None


def test_flag_overrides_config_file(tmp_path: Path) -> None:
    path = tmp_path / "gitlab.json"
    path.write_text(
        GitLabCliConfig(backup_dir="/from/file", dry_run=True).to_json(),
        encoding="utf-8",
    )
    cfg = resolve_config(
        argparse.Namespace(
            config=str(path),
            compose_file=None,
            project=None,
            gitlab_service=None,
            xgic_service=None,
            backup_dir="/from/flag",
            url=None,
            token="secret-token",
            dry_run=False,
            apply=True,
            secrets_file=None,
            config_file=None,
            allow_missing=None,
            environment=None,
        )
    )
    assert cfg.backup_dir == "/from/flag"
    assert cfg.dry_run is False
    assert cfg.token == "secret-token"
    assert cfg.public_dict()["token_set"] is True
    assert "secret-token" not in json.dumps(cfg.public_dict())


def test_config_rejects_a_token_field(tmp_path: Path) -> None:
    path = tmp_path / "gitlab.json"
    path.write_text('{"token":"secret"}\n', encoding="utf-8")
    try:
        load_cli_config(path)
    except ConfigError as exc:
        assert "token" in str(exc).lower() or "extra" in str(exc).lower()
    else:
        raise AssertionError("token field was accepted")


def test_committed_cli_schema_matches_the_model() -> None:
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert committed == gitlab_cli_schema()
    assert committed["$id"] == "gitlab-cli.schema.json"
    assert "token" not in committed["properties"]


def test_resolve_env_and_flags(monkeypatch) -> None:
    monkeypatch.setenv("GITLAB_URL", "http://localhost:8929")
    monkeypatch.setenv("GITLAB_TOKEN", "secret-token")
    monkeypatch.setenv("XGIC_GITLAB_COMPOSE_FILE", "stack.yml")

    ns = argparse.Namespace(
        compose_file=None,
        project="lab",
        gitlab_service="gitlab-ee",
        xgic_service=None,
        backup_dir="/backups",
        url=None,
        token=None,
        dry_run=True,
    )
    cfg = resolve_config(ns)
    assert cfg.compose_file == "stack.yml"
    assert cfg.project_name == "lab"
    assert cfg.gitlab_url == "http://localhost:8929"
    assert cfg.token == "secret-token"
    assert cfg.backup_dir == "/backups"
    assert cfg.dry_run is True
    assert cfg.public_dict()["token_set"] is True
    assert "secret-token" not in str(cfg.public_dict())


def test_flags_override_env(monkeypatch) -> None:
    monkeypatch.setenv("GITLAB_URL", "http://from-env")
    ns = argparse.Namespace(
        compose_file="override.yml",
        project=None,
        gitlab_service=None,
        xgic_service=None,
        backup_dir=None,
        url="http://from-flag",
        token=None,
        dry_run=False,
    )
    cfg = resolve_config(ns)
    assert cfg.compose_file == "override.yml"
    assert cfg.gitlab_url == "http://from-flag"
