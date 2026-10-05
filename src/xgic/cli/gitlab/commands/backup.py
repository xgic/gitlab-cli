"""``xgic gitlab backup`` — publish one landing-host backup pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from xgic.cli.gitlab.archive import (
    ArchiveError,
    BackupSources,
    LandingPair,
    sha256_file,
)
from xgic.cli.gitlab.compose import ComposeRunner
from xgic.cli.gitlab.config import resolve_config
from xgic.cli.gitlab.manifest import (
    BackupManifest,
    ManifestError,
    parse_allow_missing,
    split_members,
)
from xgic.cli.utils.output import print_error, print_info, print_success, print_warning


def run_backup(args: argparse.Namespace) -> int:
    """Create a GitLab backup, then publish the ``.tar.zst`` pair.

    The live secrets and config files are copied into the archive and are not
    written back.
    """
    cfg = resolve_config(args)
    report: dict[str, Any] = {
        "ok": False,
        "action": "backup",
        "config": cfg.public_dict(),
        "command": ["gitlab-backup", "create"],
        "detail": "",
    }
    secrets_file = getattr(args, "secrets_file", None)
    config_file = getattr(args, "config_file", None)
    try:
        allow_missing = set(parse_allow_missing(getattr(args, "allow_missing", None)))
    except ManifestError as exc:
        report["detail"] = str(exc)
        return _emit(args, report, 2)
    if not secrets_file or not config_file:
        report["detail"] = "backup requires --secrets-file and --config-file"
        return _emit(args, report, 2)

    runner = ComposeRunner(cfg)
    if not runner.available():
        report["detail"] = "docker CLI not found on PATH"
        return _emit(args, report, 1)

    running = runner.running_services()
    if cfg.gitlab_service not in running:
        report["detail"] = (
            f"service {cfg.gitlab_service!r} is not running "
            f"(running: {running or 'none'})"
        )
        return _emit(args, report, 1)

    if cfg.dry_run:
        report["ok"] = True
        report["detail"] = (
            f"dry-run: would exec in {cfg.gitlab_service}: gitlab-backup create; "
            f"would publish a .tar.zst pair in {cfg.backup_dir} "
            "without modifying the secrets or config files"
        )
        return _emit(args, report, 0)

    secrets_path = Path(secrets_file)
    config_path = Path(config_file)
    if not secrets_path.is_file() or not config_path.is_file():
        report["detail"] = "backup requires --secrets-file and --config-file to be files"
        return _emit(args, report, 2)

    print_info(f"Creating backup in service {cfg.gitlab_service}…")
    proc = runner.exec_service(cfg.gitlab_service, ["gitlab-backup", "create"], dry_run=False)
    if proc is None:
        report["detail"] = "exec did not run"
        return _emit(args, report, 1)

    report["returncode"] = proc.returncode
    report["stdout_tail"] = (proc.stdout or "")[-2000:]
    report["stderr_tail"] = (proc.stderr or "")[-2000:]
    if proc.returncode != 0:
        report["detail"] = f"gitlab-backup create failed (exit {proc.returncode})"
        return _emit(args, report, proc.returncode or 1)

    landing = Path(cfg.backup_dir)
    try:
        pair = LandingPair(landing)
        gitlab_tar = pair.newest_application_tar()
        present = {Path(name).name for name in pair.component_names(gitlab_tar)}
        members, omitted = split_members(present, allow_missing)
        manifest = BackupManifest.create(
            application_tar=gitlab_tar.name,
            sha256=sha256_file(gitlab_tar),
            compose_project=cfg.project_name,
            external_url=cfg.gitlab_url or "",
            backup_bind=str(landing),
            members=members,
            omitted=omitted,
        )
        archive = pair.publish(
            BackupSources(
                gitlab_tar=gitlab_tar,
                secrets_file=secrets_path,
                config_file=config_path,
            ),
            manifest,
        )
    except (ArchiveError, ManifestError, ValidationError) as exc:
        report["detail"] = str(exc)
        return _emit(args, report, 1)

    report["ok"] = True
    report["archive"] = str(archive)
    report["detail"] = f"published {archive.name}"
    return _emit(args, report, 0)


def _emit(args: argparse.Namespace, report: dict[str, Any], exit_code: int) -> int:
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
        return exit_code

    if report["ok"]:
        print_success(report["detail"] or "Backup OK")
    else:
        print_error(report["detail"] or "Backup failed")

    print_info(f"Service: {report['config']['gitlab_service']}")
    print_info(f"Compose: {report['config']['compose_file']}")
    if report.get("stderr_tail"):
        print_warning(report["stderr_tail"][:500])
    return exit_code
