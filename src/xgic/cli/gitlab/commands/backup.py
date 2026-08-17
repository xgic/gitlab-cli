"""``xgic gitlab backup`` — create a GitLab EE backup via Compose exec."""

from __future__ import annotations

import argparse
import json
from typing import Any

from xgic.cli.gitlab.compose import ComposeRunner
from xgic.cli.gitlab.config import resolve_config
from xgic.cli.utils.output import print_error, print_info, print_success, print_warning


def run_backup(args: argparse.Namespace) -> int:
    """Run ``gitlab-backup create`` inside the GitLab EE service container."""
    cfg = resolve_config(args)
    runner = ComposeRunner(cfg)
    report: dict[str, Any] = {
        "ok": False,
        "action": "backup",
        "config": cfg.public_dict(),
        "command": [
            "gitlab-backup",
            "create",
        ],
        "detail": "",
    }

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

    cmd = ["gitlab-backup", "create"]
    # STRATEGY=copy is common for volume-friendly backups; keep optional via env later.
    if cfg.dry_run:
        report["ok"] = True
        report["detail"] = (
            f"dry-run: would exec in {cfg.gitlab_service}: {' '.join(cmd)} "
            f"(host backup dir hint: {cfg.backup_dir})"
        )
        return _emit(args, report, 0)

    print_info(f"Creating backup in service {cfg.gitlab_service}…")
    proc = runner.exec_service(cfg.gitlab_service, cmd, dry_run=False)
    if proc is None:
        report["detail"] = "exec did not run"
        return _emit(args, report, 1)

    report["returncode"] = proc.returncode
    report["stdout_tail"] = (proc.stdout or "")[-2000:]
    report["stderr_tail"] = (proc.stderr or "")[-2000:]
    if proc.returncode == 0:
        report["ok"] = True
        report["detail"] = (
            f"backup create completed; copies typically land under the container "
            f"backup path (host map often {cfg.backup_dir})"
        )
        return _emit(args, report, 0)

    report["detail"] = f"gitlab-backup create failed (exit {proc.returncode})"
    return _emit(args, report, proc.returncode or 1)


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
