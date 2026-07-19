"""``xgic gitlab restore`` — restore a GitLab EE backup (destructive)."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from xgic.cli.gitlab.compose import ComposeRunner
from xgic.cli.gitlab.config import resolve_config
from xgic.cli.utils.output import print_error, print_info, print_success, print_warning

_BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def run_restore(args: argparse.Namespace) -> int:
    """Restore from a backup id via ``gitlab-backup restore`` in the EE container.

    Destructive: requires ``--yes`` unless ``--dry-run``.
    """
    cfg = resolve_config(args)
    backup_id = str(getattr(args, "backup_id", "") or "").strip()
    yes = bool(getattr(args, "yes", False))

    report: dict[str, Any] = {
        "ok": False,
        "action": "restore",
        "config": cfg.public_dict(),
        "backup_id": backup_id,
        "detail": "",
    }

    if not backup_id or not _BACKUP_ID_RE.match(backup_id):
        report["detail"] = (
            "invalid or missing backup id (use alphanumeric, dot, underscore, hyphen)"
        )
        return _emit(args, report, 2)

    if not yes and not cfg.dry_run:
        report["detail"] = (
            "refusing restore without --yes (destructive). "
            "Re-run with --yes after confirming the backup id, or use --dry-run."
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

    # Official Omnibus restore pattern (BACKUP= timestamp id without _gitlab_backup.tar).
    shell_cmd = f"gitlab-backup restore BACKUP={backup_id} force=yes"
    if cfg.dry_run:
        report["ok"] = True
        report["detail"] = (
            f"dry-run: would exec in {cfg.gitlab_service}: {shell_cmd}"
        )
        return _emit(args, report, 0)

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
            "restore completed; reconfigure/restart GitLab EE if your runbook requires it"
        )
        return _emit(args, report, 0)

    report["detail"] = f"gitlab-backup restore failed (exit {proc.returncode})"
    return _emit(args, report, proc.returncode or 1)


def _emit(args: argparse.Namespace, report: dict[str, Any], exit_code: int) -> int:
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
        return exit_code

    if report["ok"]:
        print_success(report["detail"] or "Restore OK")
    else:
        print_error(report["detail"] or "Restore failed")

    print_info(f"Backup id: {report.get('backup_id')}")
    print_info(f"Service: {report['config']['gitlab_service']}")
    if report.get("stderr_tail"):
        print_warning(report["stderr_tail"][:500])
    return exit_code
