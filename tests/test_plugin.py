"""Tests for GitLab CLI plugin registration and commands."""

from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

from xgic.cli.gitlab.commands.backup import run_backup
from xgic.cli.gitlab.commands.health import run_health
from xgic.cli.gitlab.commands.info import run_info
from xgic.cli.gitlab.commands.restore import run_restore
from xgic.cli.gitlab.plugin import register


def test_register_adds_gitlab_group() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)
    args = parser.parse_args(["gitlab", "info"])
    assert args.command == "gitlab"
    assert args.gitlab_command == "info"
    assert callable(args.func)


def test_register_ops_commands() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)
    for action in ("health", "backup"):
        args = parser.parse_args(["gitlab", action, "--dry-run"])
        assert args.gitlab_command == action
        assert args.dry_run is True
    args = parser.parse_args(["gitlab", "restore", "20240101_120000", "--yes", "--dry-run"])
    assert args.backup_id == "20240101_120000"
    assert args.yes is True


def test_run_info_json(capsys) -> None:
    ns = argparse.Namespace(json=True)
    assert run_info(ns) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["module"] == "xgic.cli.gitlab"
    assert data["package"] == "xgic-gitlab-cli"
    assert data["status"] == "experimental"
    assert "health" in data["commands"]
    assert "backup" in data["commands"]
    assert "restore" in data["commands"]


def test_run_info_human(capsys) -> None:
    ns = argparse.Namespace(json=False)
    assert run_info(ns) == 0
    out = capsys.readouterr().out
    assert "GitLab CLI" in out
    assert "experimental" in out.lower() or "0.1.1" in out


def _ops_ns(**kwargs):
    base = {
        "compose_file": "docker-compose.yml",
        "project": "xgic-gitlab",
        "gitlab_service": "gitlab-ee",
        "xgic_service": "xgic-gitlab",
        "backup_dir": "./gitlab-backups",
        "url": None,
        "token": None,
        "dry_run": True,
        "json": True,
        "yes": False,
        "backup_id": "20240101_120000",
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_backup_dry_run_when_service_running(capsys) -> None:
    with (
        patch("xgic.cli.gitlab.commands.backup.ComposeRunner") as mock_cls,
    ):
        runner = MagicMock()
        runner.available.return_value = True
        runner.running_services.return_value = ["gitlab-ee", "xgic-gitlab"]
        mock_cls.return_value = runner
        code = run_backup(_ops_ns(dry_run=True, json=True))
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert "dry-run" in data["detail"]


def test_restore_requires_yes(capsys) -> None:
    code = run_restore(_ops_ns(dry_run=False, yes=False, json=True))
    assert code == 2
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
    assert "--yes" in data["detail"]


def test_restore_rejects_bad_id(capsys) -> None:
    code = run_restore(_ops_ns(backup_id="../evil", dry_run=True, yes=True, json=True))
    assert code == 2
    data = json.loads(capsys.readouterr().out)
    assert "invalid" in data["detail"]


def test_health_no_docker(capsys) -> None:
    with patch("xgic.cli.gitlab.commands.health.ComposeRunner") as mock_cls:
        runner = MagicMock()
        runner.available.return_value = False
        mock_cls.return_value = runner
        code = run_health(_ops_ns(json=True, dry_run=False))
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
