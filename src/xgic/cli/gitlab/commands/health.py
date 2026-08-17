"""``xgic gitlab health`` — Compose + optional HTTP readiness checks."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any

from xgic.cli.gitlab.compose import ComposeRunner
from xgic.cli.gitlab.config import resolve_config
from xgic.cli.utils.output import print_error, print_info, print_success, print_warning


def _http_ok(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            code = getattr(resp, "status", 200)
            if 200 <= int(code) < 400:
                return True, f"HTTP {code}"
            return False, f"HTTP {code}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 — surface any transport failure
        return False, str(exc)


def run_health(args: argparse.Namespace) -> int:
    """Check stack service presence and optional HTTP health endpoints."""
    cfg = resolve_config(args)
    runner = ComposeRunner(cfg)
    report: dict[str, Any] = {
        "ok": False,
        "config": cfg.public_dict(),
        "docker_available": runner.available(),
        "running_services": [],
        "checks": [],
    }

    if not runner.available():
        report["checks"].append(
            {"name": "docker", "ok": False, "detail": "docker CLI not found on PATH"}
        )
        return _emit(args, report, exit_code=1)

    running = runner.running_services()
    report["running_services"] = running
    report["checks"].append(
        {
            "name": "compose_ps",
            "ok": True,
            "detail": f"{len(running)} running service(s)",
        }
    )

    for service, label in (
        (cfg.xgic_service, "orchestration_service"),
        (cfg.gitlab_service, "gitlab_ee_service"),
    ):
        present = service in running
        report["checks"].append(
            {
                "name": label,
                "ok": present,
                "detail": f"{service}: {'running' if present else 'not running'}",
            }
        )

    if cfg.gitlab_url:
        health_url = cfg.gitlab_url.rstrip("/") + "/-/health"
        ok, detail = _http_ok(health_url)
        report["checks"].append(
            {"name": "gitlab_http_health", "ok": ok, "detail": f"{health_url} → {detail}"}
        )
    else:
        report["checks"].append(
            {
                "name": "gitlab_http_health",
                "ok": True,
                "detail": "skipped (set GITLAB_URL or --url to enable)",
                "skipped": True,
            }
        )

    # Optional local orchestration healthz when service is up (container network not required;
    # operators may publish XGIC_GITLAB_PORT — we only probe if --url-style not used).
    # Probe is best-effort via docker compose exec curl if service running.
    if cfg.xgic_service in running and not cfg.dry_run:
        proc = runner.exec_service(
            cfg.xgic_service,
            ["curl", "-fsS", "http://127.0.0.1:8080/healthz"],
            dry_run=False,
        )
        ok = proc is not None and proc.returncode == 0
        detail = "ok" if ok else (proc.stderr or proc.stdout or "failed" if proc else "n/a")
        report["checks"].append(
            {"name": "xgic_healthz", "ok": ok, "detail": str(detail).strip()[:200]}
        )
    elif cfg.dry_run and cfg.xgic_service in running:
        report["checks"].append(
            {
                "name": "xgic_healthz",
                "ok": True,
                "detail": "dry-run: would exec curl healthz in orchestration service",
                "skipped": True,
            }
        )

    critical = [
        c
        for c in report["checks"]
        if not c.get("skipped") and c["name"] in {"docker", "orchestration_service", "gitlab_ee_service", "gitlab_http_health", "xgic_healthz"}
    ]
    # compose_ps alone is not enough; require gitlab-ee running for overall ok
    gitlab_ok = any(
        c["name"] == "gitlab_ee_service" and c["ok"] for c in report["checks"]
    )
    failed = [c for c in critical if not c["ok"]]
    report["ok"] = gitlab_ok and not failed

    return _emit(args, report, exit_code=0 if report["ok"] else 1)


def _emit(args: argparse.Namespace, report: dict[str, Any], *, exit_code: int) -> int:
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
        return exit_code

    if report["ok"]:
        print_success("GitLab stack health: OK")
    else:
        print_error("GitLab stack health: issues detected")

    print_info(f"Compose: {report['config']['compose_file']} (project {report['config']['project_name']})")
    if report["running_services"]:
        print_info("Running: " + ", ".join(report["running_services"]))
    else:
        print_warning("No running Compose services detected")

    for check in report["checks"]:
        status = "ok" if check["ok"] else "FAIL"
        if check.get("skipped"):
            status = "skip"
        print_info(f"[{status}] {check['name']}: {check['detail']}")

    return exit_code
