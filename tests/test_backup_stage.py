"""The backup publish can see a tar that exists only in the service."""

from __future__ import annotations

from pathlib import Path

from xgic.cli.gitlab.commands.backup import stage_application_tar


class _Proc:
    def __init__(self, code: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = code
        self.stdout = stdout
        self.stderr = stderr


class _Runner:
    def __init__(self, listing: _Proc, copy: _Proc) -> None:
        self.listing = listing
        self.copy = copy
        self.copied: list[tuple[str, ...]] = []

    def exec_service(self, service: str, command: list[str], *, dry_run: bool) -> _Proc:
        assert dry_run is False
        assert service == "gitlab-ee"
        return self.listing

    def run(self, *args: str, check: bool = False, capture: bool = True) -> _Proc:
        self.copied.append(args)
        return self.copy


def test_existing_landing_tar_is_not_copied(tmp_path: Path) -> None:
    present = tmp_path / "100_2026_01_02_1.2.3_gitlab_backup.tar"
    present.write_bytes(b"tar")
    runner = _Runner(
        _Proc(0, f"/var/opt/gitlab/backups/{present.name}\n"),
        _Proc(0),
    )
    stage_application_tar(runner, "gitlab-ee", tmp_path)
    assert runner.copied == []


def test_missing_landing_tar_is_copied_from_the_service(tmp_path: Path) -> None:
    name = "100_2026_01_02_1.2.3_gitlab_backup.tar"

    class _Copy:
        def __init__(self) -> None:
            self.returncode = 0
            self.stdout = ""
            self.stderr = ""

        def __call__(self, *_args: str, check: bool = False, capture: bool = True) -> _Proc:
            (tmp_path / name).write_bytes(b"tar")
            return _Proc(0)

    runner = _Runner(_Proc(0, f"/var/opt/gitlab/backups/{name}\n"), _Proc(0))
    runner.run = _Copy().__call__  # type: ignore[method-assign]
    stage_application_tar(runner, "gitlab-ee", tmp_path)
    assert (tmp_path / name).is_file()
