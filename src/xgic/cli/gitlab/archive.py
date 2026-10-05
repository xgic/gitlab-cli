"""Publish and open one GitLab backup pair on the landing host.

The pair is one ``.tar.zst`` and a sibling ``.tar.zst.sha256``. The archive
holds the GitLab application tar, the live secrets file, the live
``gitlab.rb``, and ``backup-manifest.json``. Publishing reads the live files
and does not write them back.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from xgic.cli.gitlab.manifest import BackupManifest, ManifestError, split_members

OUTER_REQUIRED = ("gitlab-secrets.json", "gitlab.rb", "backup-manifest.json")
_SECRET_MODE = 0o600


class ArchiveError(Exception):
    """The backup pair is missing a required member or fails its check."""


class CommandRunner(Protocol):
    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run one command and return its result."""


@dataclass(frozen=True)
class BackupSources:
    """Files copied into the archive. Publish does not modify them."""

    gitlab_tar: Path
    secrets_file: Path
    config_file: Path


@dataclass(frozen=True)
class OpenedPair:
    """A checksum-verified archive extracted into one directory."""

    archive: Path
    gitlab_tar: Path
    manifest: BackupManifest
    secrets_file: Path
    config_file: Path

    def place_application_tar(self, backup_dir: Path) -> Path:
        """Copy the application tar to the directory GitLab restore reads."""
        target = backup_dir / self.gitlab_tar.name
        if target.resolve() == self.gitlab_tar.resolve():
            return target
        _write_private(self.gitlab_tar, target)
        return target


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sidecar_line(digest: str, archive_name: str) -> str:
    return f"{digest}  {archive_name}\n"


class LandingPair:
    """Create and open the landing-host pair for one GitLab backup."""

    def __init__(self, output_dir: Path, runner: CommandRunner | None = None) -> None:
        self.output_dir = output_dir
        self._runner = runner or _run

    def newest_application_tar(self) -> Path:
        found = sorted(
            (
                path
                for path in self.output_dir.glob("*_gitlab_backup.tar")
                if path.is_file() and not path.is_symlink()
            ),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
        )
        if not found:
            raise ArchiveError(f"no GitLab backup tar in {self.output_dir}")
        return found[-1]

    def publish(self, sources: BackupSources, manifest: BackupManifest) -> Path:
        """Write the pair. The source secrets and config files are not modified."""
        self._require_sources(sources)
        self._require_recorded_members(sources.gitlab_tar, manifest)
        if manifest.artifacts.application_tar != sources.gitlab_tar.name:
            raise ArchiveError("manifest names a different application tar")
        if manifest.artifacts.sha256 != sha256_file(sources.gitlab_tar):
            raise ArchiveError("manifest digest does not match the application tar")
        confirmed = self._validate_manifest(manifest.to_json())
        archive_name = sources.gitlab_tar.name.replace("_gitlab_backup.tar", ".tar.zst")
        if not archive_name.endswith(".tar.zst") or archive_name == ".tar.zst":
            raise ArchiveError("archive name must end in .tar.zst")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        archive = self.output_dir / archive_name
        partial = self.output_dir / f"{archive_name}.partial"
        sidecar_partial = self.output_dir / f"{archive_name}.sha256.partial"
        sidecar = archive.with_name(archive.name + ".sha256")
        staging = self.output_dir / f".{archive_name}.staging"
        try:
            self._stage(sources, confirmed, staging)
            self._tar_create(partial, staging)
            os.chmod(partial, _SECRET_MODE)
            _write_text(sidecar_partial, sidecar_line(sha256_file(partial), archive.name))
            os.replace(partial, archive)
            try:
                os.replace(sidecar_partial, sidecar)
            except OSError:
                archive.unlink(missing_ok=True)
                raise
            os.chmod(archive, _SECRET_MODE)
            os.chmod(sidecar, _SECRET_MODE)
        finally:
            partial.unlink(missing_ok=True)
            sidecar_partial.unlink(missing_ok=True)
            shutil.rmtree(staging, ignore_errors=True)
        return archive

    def open(self, archive: Path, dest_dir: Path) -> OpenedPair:
        """Check the sidecar, extract the archive, and validate the manifest."""
        if not archive.is_file() or archive.is_symlink():
            raise ArchiveError(f"missing {archive.name}")
        if dest_dir.is_symlink():
            raise ArchiveError("refusing to extract through a symlink")
        if dest_dir.resolve() == self.output_dir.resolve():
            raise ArchiveError("refusing to extract over the landing directory")
        self.verify_sidecar(archive)
        staging = dest_dir.with_name(dest_dir.name + ".partial")
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, mode=0o700)
        try:
            self._extract(archive, staging)
            opened = self._load(archive, staging)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        os.replace(staging, dest_dir)
        os.chmod(dest_dir, 0o700)
        return _retarget(opened, dest_dir)

    def open_latest(self, dest_dir: Path) -> OpenedPair:
        """Open the newest pair that passes the sidecar, manifest, and member checks."""
        last_error: ArchiveError | None = None
        candidates = self._archives_newest_first()
        if not candidates:
            raise ArchiveError(f"no .tar.zst pair in {self.output_dir}")
        for archive in candidates:
            try:
                return self.open(archive, dest_dir)
            except ArchiveError as exc:
                last_error = exc
        raise last_error or ArchiveError(f"no verified .tar.zst pair in {self.output_dir}")

    def manifest_of(self, archive: Path) -> BackupManifest:
        """Validate the sidecar and manifest without extracting the archive."""
        if not archive.is_file() or archive.is_symlink():
            raise ArchiveError(f"missing {archive.name}")
        self.verify_sidecar(archive)
        names = self._members(archive)
        _reject_unsafe(names)
        manifest_name = next(
            (name for name in names if Path(name).name == "backup-manifest.json"),
            None,
        )
        if manifest_name is None:
            raise ArchiveError("archive is missing backup-manifest.json")
        completed = self._runner(["tar", "--zstd", "-xOf", str(archive), manifest_name])
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "cannot read backup-manifest.json"
            raise ArchiveError(detail)
        return self._validate_manifest(completed.stdout)

    def manifest_of_latest(self) -> tuple[Path, BackupManifest]:
        """Return the newest pair whose sidecar and manifest validate."""
        candidates = self._archives_newest_first()
        if not candidates:
            raise ArchiveError(f"no .tar.zst pair in {self.output_dir}")
        last_error: ArchiveError | None = None
        for archive in candidates:
            try:
                return archive, self.manifest_of(archive)
            except ArchiveError as exc:
                last_error = exc
        raise last_error or ArchiveError(f"no verified .tar.zst pair in {self.output_dir}")

    def verify_sidecar(self, archive: Path) -> None:
        sidecar = archive.with_name(archive.name + ".sha256")
        if not sidecar.is_file() or sidecar.is_symlink():
            raise ArchiveError(f"missing sidecar for {archive.name}")
        text = sidecar.read_text(encoding="utf-8")
        prefix = f"{sha256_file(archive)}  {archive.name}\n"
        if text != prefix:
            raise ArchiveError(f"sidecar does not match {archive.name}")

    def _archives_newest_first(self) -> list[Path]:
        found = [
            path
            for path in self.output_dir.glob("*.tar.zst")
            if path.is_file() and not path.is_symlink()
        ]
        found.sort(key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
        return found

    def _require_sources(self, sources: BackupSources) -> None:
        for path in (sources.gitlab_tar, sources.secrets_file, sources.config_file):
            if not path.is_file() or path.is_symlink():
                raise ArchiveError(f"missing {path.name}")

    def _stage(self, sources: BackupSources, manifest: BackupManifest, staging: Path) -> None:
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, mode=0o700)
        _copy_bytes(sources.gitlab_tar, staging / sources.gitlab_tar.name)
        _copy_bytes(sources.secrets_file, staging / "gitlab-secrets.json")
        _copy_bytes(sources.config_file, staging / "gitlab.rb")
        manifest_path = staging / "backup-manifest.json"
        _write_text(manifest_path, manifest.to_json())
        self._validate_manifest(manifest_path.read_text(encoding="utf-8"))

    def _tar_create(self, partial: Path, staging: Path) -> None:
        completed = self._runner(
            ["tar", "--zstd", "-cf", str(partial), "-C", str(staging), "."]
        )
        if completed.returncode != 0:
            raise ArchiveError(completed.stderr.strip() or "tar --zstd failed")

    def _extract(self, archive: Path, dest_dir: Path) -> None:
        names = self._members(archive)
        _reject_unsafe(names)
        completed = self._runner(
            ["tar", "--zstd", "-xf", str(archive), "-C", str(dest_dir)]
        )
        if completed.returncode != 0:
            raise ArchiveError(completed.stderr.strip() or "extract failed")

    def _load(self, archive: Path, dest_dir: Path) -> OpenedPair:
        for name in OUTER_REQUIRED:
            if not (dest_dir / name).is_file():
                raise ArchiveError(f"archive is missing {name}")
        gitlab_tars = [
            path
            for path in dest_dir.glob("*_gitlab_backup.tar")
            if path.is_file() and not path.is_symlink()
        ]
        if len(gitlab_tars) != 1:
            raise ArchiveError("archive must contain one GitLab backup tar")
        gitlab_tar = gitlab_tars[0]
        manifest = self._validate_manifest(
            (dest_dir / "backup-manifest.json").read_text(encoding="utf-8")
        )
        self._require_recorded_members(gitlab_tar, manifest)
        if manifest.artifacts.application_tar != gitlab_tar.name:
            raise ArchiveError("manifest names a different application tar")
        if manifest.artifacts.sha256 != sha256_file(gitlab_tar):
            raise ArchiveError("manifest digest does not match the application tar")
        for path in (gitlab_tar, dest_dir / "gitlab-secrets.json", dest_dir / "gitlab.rb"):
            os.chmod(path, _SECRET_MODE)
        return OpenedPair(
            archive=archive,
            gitlab_tar=gitlab_tar,
            manifest=manifest,
            secrets_file=dest_dir / "gitlab-secrets.json",
            config_file=dest_dir / "gitlab.rb",
        )

    def component_names(self, gitlab_tar: Path) -> set[str]:
        """Return the names stored in the GitLab application tar."""
        return self._members(gitlab_tar)

    def _require_recorded_members(self, gitlab_tar: Path, manifest: BackupManifest) -> None:
        present = {Path(name).name for name in self.component_names(gitlab_tar)}
        try:
            members, omitted = split_members(present, set(manifest.artifacts.omitted))
        except ManifestError as exc:
            raise ArchiveError(str(exc)) from exc
        if members != list(manifest.artifacts.members) or omitted != list(manifest.artifacts.omitted):
            raise ArchiveError("manifest members do not match the application tar")

    def _members(self, path: Path) -> set[str]:
        completed = self._runner(["tar", "-tf", str(path)])
        if completed.returncode != 0:
            raise ArchiveError(completed.stderr.strip() or f"cannot list {path.name}")
        return {line.strip() for line in completed.stdout.splitlines() if line.strip()}

    def _validate_manifest(self, text: str) -> BackupManifest:
        try:
            return BackupManifest.model_validate_json(text)
        except (ValidationError, ManifestError) as exc:
            raise ArchiveError(f"backup manifest is invalid: {exc}") from exc


def write_snapshot(source: Path, dest: Path) -> None:
    """Write one extracted file to ``dest`` at mode 0600."""
    if not source.is_file():
        raise ArchiveError(f"missing {source.name}")
    _write_private(source, dest)


def _copy_bytes(source: Path, dest: Path) -> None:
    dest.write_bytes(source.read_bytes())
    os.chmod(dest, _SECRET_MODE)


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    os.chmod(path, _SECRET_MODE)


def _write_private(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    partial.write_bytes(source.read_bytes())
    os.chmod(partial, _SECRET_MODE)
    os.replace(partial, dest)


def _reject_unsafe(names: set[str]) -> None:
    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ArchiveError(f"unsafe archive member {name}")


def _retarget(opened: OpenedPair, dest_dir: Path) -> OpenedPair:
    return OpenedPair(
        archive=opened.archive,
        gitlab_tar=dest_dir / opened.gitlab_tar.name,
        manifest=opened.manifest,
        secrets_file=dest_dir / "gitlab-secrets.json",
        config_file=dest_dir / "gitlab.rb",
    )


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)
