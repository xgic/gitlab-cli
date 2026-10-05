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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xgic")
    sub = parser.add_subparsers(dest="command")
    register(sub)
    return parser


def test_register_adds_gitlab_group() -> None:
    args = _parser().parse_args(["gitlab", "info"])
    assert args.command == "gitlab"
    assert args.gitlab_command == "info"
    assert callable(args.func)


def test_missing_action_prints_full_usage(capsys) -> None:
    parser = _parser()
    args = parser.parse_args(["gitlab"])
    assert args.gitlab_command is None
    code = args.func(args)
    assert code == 2
    out = capsys.readouterr().out
    assert "usage:" in out.lower()
    assert "info" in out
    assert "health" in out
    assert "backup" in out
    assert "restore" in out
    assert "the following arguments are required" not in out.lower()


def test_register_ops_commands() -> None:
    parser = _parser()
    for action in ("health", "backup"):
        args = parser.parse_args(["gitlab", action, "--dry-run"])
        assert args.gitlab_command == action
        assert args.dry_run is True
    args = parser.parse_args(
        ["gitlab", "restore", "--archive", "gitlab.tar.zst", "--yes", "--dry-run"]
    )
    assert args.archive == "gitlab.tar.zst"
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
        "secrets_file": None,
        "config_file": None,
        "archive": None,
        "secrets_dest": None,
        "config_dest": None,
        "allow_missing": None,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_backup_rejects_unknown_allow_missing(capsys) -> None:
    code = run_backup(_ops_ns(dry_run=True, json=True, allow_missing="wiki"))
    assert code == 2
    assert "allow-missing" in json.loads(capsys.readouterr().out)["detail"]


def test_backup_requires_live_files(capsys) -> None:
    code = run_backup(_ops_ns(dry_run=True, json=True))
    assert code == 2
    assert "secrets-file" in json.loads(capsys.readouterr().out)["detail"]


def test_backup_dry_run_when_service_running(capsys) -> None:
    with (
        patch("xgic.cli.gitlab.commands.backup.ComposeRunner") as mock_cls,
    ):
        runner = MagicMock()
        runner.available.return_value = True
        runner.running_services.return_value = ["gitlab-ee", "xgic-gitlab"]
        mock_cls.return_value = runner
        code = run_backup(
            _ops_ns(
                dry_run=True,
                json=True,
                secrets_file="secrets.json",
                config_file="gitlab.rb",
            )
        )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert "dry-run" in data["detail"]


def test_restore_requires_yes(capsys) -> None:
    code = run_restore(_ops_ns(dry_run=False, yes=False, json=True, archive="gitlab.tar.zst"))
    assert code == 2
    assert "--yes" in json.loads(capsys.readouterr().out)["detail"]


def test_restore_requires_a_pair_when_archive_is_omitted(tmp_path, capsys) -> None:
    with patch("xgic.cli.gitlab.commands.restore.ComposeRunner") as mock_cls:
        runner = MagicMock()
        runner.available.return_value = True
        runner.running_services.return_value = ["gitlab-ee"]
        mock_cls.return_value = runner
        code = run_restore(
            _ops_ns(dry_run=False, yes=True, json=True, backup_dir=str(tmp_path))
        )
    assert code == 1
    assert "pair" in json.loads(capsys.readouterr().out)["detail"]
    runner.exec_service.assert_not_called()


def test_restore_rejects_bad_archive(capsys) -> None:
    code = run_restore(
        _ops_ns(archive="../evil.tar.zst", dry_run=True, yes=True, json=True)
    )
    assert code == 2
    assert "tar.zst" in json.loads(capsys.readouterr().out)["detail"]


def test_restore_dry_run_does_not_extract_or_write_destinations(tmp_path, capsys) -> None:
    from datetime import UTC, datetime

    from xgic.cli.gitlab.archive import BackupSources, LandingPair, sha256_file
    from xgic.cli.gitlab.manifest import BackupManifest

    gitlab_tar = tmp_path / "1_gitlab_backup.tar"
    import tarfile

    with tarfile.open(gitlab_tar, "w") as archive:
        for name in ("registry.tar.gz", "lfs.tar.gz", "packages.tar.gz"):
            info = tarfile.TarInfo(name)
            archive.addfile(info)
    secrets = tmp_path / "live-secrets.json"
    config = tmp_path / "live.rb"
    secrets.write_text("{}\n", encoding="utf-8")
    config.write_text("external_url 'https://gitlab.example'\n", encoding="utf-8")
    sources = BackupSources(gitlab_tar, secrets, config)
    landing = tmp_path / "landing"
    manifest = BackupManifest.create(
        application_tar=gitlab_tar.name,
        sha256=sha256_file(gitlab_tar),
        compose_project="xgic-gitlab",
        now=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
    )
    LandingPair(landing).publish(sources, manifest)
    secrets_dest = tmp_path / "out-secrets.json"
    with patch("xgic.cli.gitlab.commands.restore.ComposeRunner") as mock_cls:
        runner = MagicMock()
        runner.available.return_value = True
        runner.running_services.return_value = ["gitlab-ee"]
        mock_cls.return_value = runner
        code = run_restore(
            _ops_ns(
                dry_run=True,
                yes=False,
                json=True,
                backup_dir=str(landing),
                secrets_dest=str(secrets_dest),
                config_dest=str(tmp_path / "out.rb"),
            )
        )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["backup_id"] == "1"
    assert not secrets_dest.exists()
    assert not (landing / ".restore").exists()
    assert secrets.read_text(encoding="utf-8") == "{}\n"
    runner.exec_service.assert_not_called()


def test_health_no_docker(capsys) -> None:
    with patch("xgic.cli.gitlab.commands.health.ComposeRunner") as mock_cls:
        runner = MagicMock()
        runner.available.return_value = False
        mock_cls.return_value = runner
        code = run_health(_ops_ns(json=True, dry_run=False))
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
