"""Thin Docker Compose runner for GitLab stack ops (stdlib only)."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from xgic.cli.gitlab.config import GitLabOpsConfig


@dataclass
class ComposeRunner:
    """Run ``docker compose`` against the configured project."""

    config: GitLabOpsConfig

    def available(self) -> bool:
        return shutil.which("docker") is not None

    def base_cmd(self) -> list[str]:
        return [
            "docker",
            "compose",
            "-f",
            self.config.compose_file,
            "-p",
            self.config.project_name,
        ]

    def run(
        self,
        *args: str,
        check: bool = False,
        capture: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [*self.base_cmd(), *args]
        return subprocess.run(
            cmd,
            check=check,
            capture_output=capture,
            text=True,
        )

    def running_services(self) -> list[str]:
        try:
            result = self.run(
                "ps",
                "--services",
                "--filter",
                "status=running",
                check=False,
            )
        except FileNotFoundError:
            return []
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def exec_service(
        self,
        service: str,
        command: Sequence[str],
        *,
        dry_run: bool = False,
    ) -> subprocess.CompletedProcess[str] | None:
        """``docker compose exec -T <service> <command…>``."""
        if dry_run:
            return None
        return self.run("exec", "-T", service, *command, check=False)
