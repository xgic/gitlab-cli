"""``xgic gitlab restore`` — restore a verified GitLab backup pair."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from xgic.cli.gitlab.archive import ArchiveError, LandingPair, write_snapshot
from xgic.cli.gitlab.compose import ComposeRunner
from xgic.cli.gitlab.config import resolve_config
from xgic.cli.utils.output import print_error, print_info, print_success, print_warning

_BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def run_restore(args: argparse.Namespace) -> int:
    """Restore one verified pair.

    Without ``--archive``, the newest pair in ``--backup-dir`` that passes
    the sidecar, manifest, and member checks is used. Secrets and config are
    written only when a destination flag is set, and only after ``--yes``.
    """
    cfg = resolve_config(args)
    archive_arg = str(getattr(args, "archive", "") or "").strip()
    yes = bool(getattr(args, "yes", False))
    archive = Path(archive_arg) if archive_arg else None
    report: dict[str, Any] = {
        "ok": False,
        "action": "restore",
        "config": cfg.public_dict(),
        "archive": str(archive) if archive else "",
        "backup_id": "",
        "detail": "",
    }

    if archive is not None and (
        ".." in archive.parts or not archive.name.endswith(".tar.zst")
    ):
        report["detail"] = "restore requires --archive pointing at a .tar.zst pair"
        return _emit(args, report, 2)
    try:
        secrets_dest = _destination(getattr(args, "secrets_dest", None))
        config_dest = _destination(getattr(args, "config_dest", None))
    except ArchiveError as exc:
        report["detail"] = str(exc)
        return _emit(args, report, 2)

    if not yes and not cfg.dry_run:
        report["detail"] = (
            "refusing restore without --yes (destructive). "
            "Re-run with --yes after confirming the archive, or use --dry-run."
        )
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

    landing = Path(cfg.backup_dir)
    if archive is not None and not archive.is_file() and archive.parent == Path("."):
        archive = landing / archive.name
    pair = LandingPair(landing)
    try:
        if cfg.dry_run:
            if archive is not None:
                chosen = archive
                manifest = pair.manifest_of(archive)
            else:
                chosen, manifest = pair.manifest_of_latest()
            backup_id = manifest.artifacts.backup_id
            _require_backup_id(backup_id)
            report["archive"] = str(chosen)
            report["backup_id"] = backup_id
            report["ok"] = True
            report["detail"] = (
                "dry-run: would exec in "
                f"{cfg.gitlab_service}: gitlab-backup restore BACKUP={backup_id} force=yes"
            )
            return _emit(args, report, 0)
        opened = (
            pair.open(archive, landing / ".restore")
            if archive is not None
            else pair.open_latest(landing / ".restore")
        )
    except ArchiveError as exc:
        report["detail"] = str(exc)
        return _emit(args, report, 1)

    backup_id = opened.manifest.artifacts.backup_id
    if _BACKUP_ID_RE.fullmatch(backup_id) is None:
        report["detail"] = "backup id is not safe to restore"
        return _emit(args, report, 1)
    report["archive"] = str(opened.archive)
    report["backup_id"] = backup_id
    shell_cmd = f"gitlab-backup restore BACKUP={backup_id} force=yes"

    try:
        opened.place_application_tar(landing)
        if secrets_dest is not None:
            write_snapshot(opened.secrets_file, secrets_dest)
        if config_dest is not None:
            write_snapshot(opened.config_file, config_dest)
    except ArchiveError as exc:
        report["detail"] = str(exc)
        return _emit(args, report, 1)

    print_warning("Restore is destructive and will overwrite GitLab application data.")
    print_info(f"Restoring backup id {backup_id!r} in {cfg.gitlab_service}…")
    proc = runner.exec_service(
        cfg.gitlab_service,
        ["bash", "-lc", shell_cmd],
        dry_run=False,
    )
    if proc is None:
        report["detail"] = "exec did not run"
        return _emit(args, report, 1)

    report["returncode"] = proc.returncode
    report["stdout_tail"] = (proc.stdout or "")[-2000:]
    report["stderr_tail"] = (proc.stderr or "")[-2000:]
    if proc.returncode == 0:
        report["ok"] = True
        report["detail"] = (
            "restore completed; reconfigure GitLab EE if your runbook requires it"
        )
        return _emit(args, report, 0)

    report["detail"] = f"gitlab-backup restore failed (exit {proc.returncode})"
    return _emit(args, report, proc.returncode or 1)


def _require_backup_id(backup_id: str) -> None:
    if _BACKUP_ID_RE.fullmatch(backup_id) is None:
        raise ArchiveError("backup id is not safe to restore")


def _destination(value: object) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    path = Path(str(value))
    if ".." in path.parts:
        raise ArchiveError("refusing a destination path that contains ..")
    return path


def _emit(args: argparse.Namespace, report: dict[str, Any], exit_code: int) -> int:
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
        return exit_code

    if report["ok"]:
        print_success(report["detail"] or "Restore OK")
    else:
        print_error(report["detail"] or "Restore failed")

    if report.get("backup_id"):
        print_info(f"Backup id: {report['backup_id']}")
    print_info(f"Archive: {report.get('archive') or '-'}")
    print_info(f"Service: {report['config']['gitlab_service']}")
    if report.get("stderr_tail"):
        print_warning(report["stderr_tail"][:500])
    return exit_code
