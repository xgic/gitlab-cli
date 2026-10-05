"""Tests for the GitLab backup pair and its Pydantic manifest."""

from __future__ import annotations

import json
import os
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from xgic.cli.gitlab.archive import (
    ArchiveError,
    BackupSources,
    LandingPair,
    sha256_file,
)
from xgic.cli.gitlab.manifest import (
    SCHEMA_PATH,
    BackupManifest,
    GraphqlRestoreCheck,
    RestRestoreCheck,
    backup_manifest_schema,
)

INNER = ("registry.tar.gz", "lfs.tar.gz", "packages.tar.gz", "db/database.sql.gz")


def _inner_tar(path: Path, members: tuple[str, ...]) -> None:
    with tarfile.open(path, "w") as archive:
        for name in members:
            info = tarfile.TarInfo(name)
            info.size = 0
            archive.addfile(info)


def _sources(tmp_path: Path, members: tuple[str, ...] = INNER) -> BackupSources:
    gitlab_tar = tmp_path / "1_gitlab_backup.tar"
    _inner_tar(gitlab_tar, members)
    secrets = tmp_path / "live-secrets.json"
    config = tmp_path / "live.rb"
    secrets.write_text('{"secret_key_base":"x"}\n', encoding="utf-8")
    config.write_text("external_url 'https://gitlab.example'\n", encoding="utf-8")
    return BackupSources(gitlab_tar, secrets, config)


def _manifest(
    sources: BackupSources,
    checks: list[GraphqlRestoreCheck] | None = None,
) -> BackupManifest:
    return BackupManifest.create(
        application_tar=sources.gitlab_tar.name,
        sha256=sha256_file(sources.gitlab_tar),
        compose_project="xgic-gitlab",
        external_url="https://gitlab.example",
        now=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        checks=checks or (),
    )


def test_publish_pair_does_not_change_source_files(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    before = (
        sources.secrets_file.read_bytes(),
        sources.config_file.read_bytes(),
        sources.secrets_file.stat().st_mtime_ns,
        sources.config_file.stat().st_mtime_ns,
    )
    archive = LandingPair(tmp_path / "out").publish(sources, _manifest(sources))
    assert archive.name == "1.tar.zst"
    assert archive.stat().st_mode & 0o777 == 0o600
    sidecar = archive.with_name("1.tar.zst.sha256")
    assert sidecar.read_text(encoding="utf-8") == (
        f"{sha256_file(archive)}  1.tar.zst\n"
    )
    assert not (tmp_path / "out" / "backup-manifest.json").exists()
    assert (sources.secrets_file.read_bytes(), sources.config_file.read_bytes()) == before[:2]
    assert sources.secrets_file.stat().st_mtime_ns == before[2]
    assert sources.config_file.stat().st_mtime_ns == before[3]
    opened = LandingPair(tmp_path / "out").open(archive, tmp_path / "restore")
    assert opened.gitlab_tar.name == "1_gitlab_backup.tar"
    assert opened.secrets_file.read_text(encoding="utf-8").startswith("{")
    assert opened.config_file.is_file()
    assert opened.manifest.artifacts.sha256 == sha256_file(sources.gitlab_tar)
    assert opened.manifest.environment.external_url == "https://gitlab.example"
    assert any(
        isinstance(check, RestRestoreCheck) and check.path == "/-/health"
        for check in opened.manifest.restore_validation.checks
    )


def test_manifest_records_a_graphql_check_for_a_later_validator(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    check = GraphqlRestoreCheck(query_name="metadata", expect={"version": "19.2.1"})
    manifest = _manifest(sources, checks=[check])
    again = BackupManifest.model_validate_json(manifest.to_json())
    graphql = [
        item
        for item in again.restore_validation.checks
        if isinstance(item, GraphqlRestoreCheck)
    ]
    assert graphql[0].query_name == "metadata"
    assert graphql[0].expect == {"version": "19.2.1"}


def test_manifest_rejects_an_unknown_check_kind() -> None:
    payload = {
        "schema_version": 1,
        "created_at": "2026-10-05T12:00:00Z",
        "backup_date": "2026-10-05",
        "environment": {"compose_project": "xgic-gitlab"},
        "artifacts": {
            "application_tar": "1_gitlab_backup.tar",
            "backup_id": "1",
            "sha256": "a" * 64,
        },
        "restore_validation": {"checks": [{"kind": "soap", "path": "/"}]},
    }
    with pytest.raises(ValidationError):
        BackupManifest.model_validate(payload)


def test_committed_schema_matches_the_model() -> None:
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert committed == backup_manifest_schema()
    assert committed["$id"] == "backup-manifest.schema.json"
    assert "RestRestoreCheck" in committed["$defs"]
    assert "GraphqlRestoreCheck" in committed["$defs"]


def test_publish_allows_an_explicit_missing_registry(tmp_path: Path) -> None:
    sources = _sources(tmp_path, ("lfs.tar.gz", "packages.tar.gz"))
    manifest = BackupManifest.create(
        application_tar=sources.gitlab_tar.name,
        sha256=sha256_file(sources.gitlab_tar),
        compose_project="xgic-gitlab",
        now=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        members=["lfs.tar.gz", "packages.tar.gz"],
        omitted=["registry.tar.gz"],
    )
    archive = LandingPair(tmp_path / "out").publish(sources, manifest)
    opened = LandingPair(tmp_path / "out").open(archive, tmp_path / "restore")
    assert opened.manifest.artifacts.omitted == ["registry.tar.gz"]
    assert "lfs.tar.gz" in opened.manifest.artifacts.members


def test_publish_rejects_tar_without_registry(tmp_path: Path) -> None:
    sources = _sources(tmp_path, ("lfs.tar.gz", "packages.tar.gz"))
    with pytest.raises(ArchiveError, match="registry.tar.gz"):
        LandingPair(tmp_path / "out").publish(sources, _manifest(sources))


def test_open_rejects_a_sidecar_mismatch(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    archive = LandingPair(tmp_path / "out").publish(sources, _manifest(sources))
    archive.with_name(archive.name + ".sha256").write_text(
        f"{'0' * 64}  {archive.name}\n",
        encoding="utf-8",
    )
    with pytest.raises(ArchiveError, match="sidecar does not match"):
        LandingPair(tmp_path / "out").open(archive, tmp_path / "restore")


def test_open_latest_skips_a_pair_with_a_bad_sidecar(tmp_path: Path) -> None:
    out = tmp_path / "out"
    sources = _sources(tmp_path)
    landing = LandingPair(out)
    older = landing.publish(sources, _manifest(sources))
    newer = out / "9.tar.zst"
    newer.write_bytes(b"not-an-archive")
    (out / "9.tar.zst.sha256").write_text(f"{'ab' * 32}  9.tar.zst\n", encoding="utf-8")
    os.utime(newer, (newer.stat().st_atime, older.stat().st_mtime + 10))
    opened = landing.open_latest(tmp_path / "restore")
    assert opened.archive == older


def test_newest_application_tar_uses_mtime(tmp_path: Path) -> None:
    older = tmp_path / "1_gitlab_backup.tar"
    newer = tmp_path / "2_gitlab_backup.tar"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    assert LandingPair(tmp_path).newest_application_tar() == newer


def test_version_check_is_recorded_from_the_gitlab_tar_name(tmp_path: Path) -> None:
    gitlab_tar = tmp_path / "178_2026_10_05_19.2.1-ee_gitlab_backup.tar"
    _inner_tar(gitlab_tar, INNER)
    manifest = BackupManifest.create(
        application_tar=gitlab_tar.name,
        sha256=sha256_file(gitlab_tar),
        compose_project="xgic-gitlab",
        now=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
    )
    version = manifest.restore_validation.checks[0]
    assert isinstance(version, RestRestoreCheck)
    assert version.path == "/api/v4/version"
    assert version.expect == {"version": "19.2.1-ee"}
    assert manifest.environment.ee_version == "19.2.1-ee"
