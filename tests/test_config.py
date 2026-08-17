"""Tests for public-safe GitLab ops config resolution."""

from __future__ import annotations

import argparse

from xgic.cli.gitlab.config import (
    DEFAULT_COMPOSE_FILE,
    DEFAULT_GITLAB_SERVICE,
    resolve_config,
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
    assert cfg.public_dict()["token_set"] is False


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
