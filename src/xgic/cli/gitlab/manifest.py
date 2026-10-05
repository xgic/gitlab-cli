"""Pydantic model for ``backup-manifest.json``.

The model is the schema. Backup serializes it and validates that document.
Restore validates it again before it uses the archive. ``restore_validation``
records REST and GraphQL checks for a later validator. Adding a check means
adding a model to :data:`RestoreCheck` and regenerating the schema. This
module does not call GitLab.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "backup-manifest.schema.json"
INNER_REQUIRED = ("registry.tar.gz", "lfs.tar.gz", "packages.tar.gz")
COMPONENT_FILES = {
    "registry": "registry.tar.gz",
    "lfs": "lfs.tar.gz",
    "packages": "packages.tar.gz",
}

_APP_TAR = re.compile(r"^(?P<backup_id>[A-Za-z0-9._-]+)_gitlab_backup\.tar$")
_VERSION = re.compile(
    r"^\d+_\d{4}_\d{2}_\d{2}_(?P<version>\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?)$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """The backup manifest does not match the current schema."""


class RestRestoreCheck(BaseModel):
    """One read-only GitLab REST call to make after restore.

    ``expect`` is a flat subset of the JSON object a later validator compares
    with the response. Backup records the check and does not perform it.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["rest"] = "rest"
    method: Literal["GET"] = "GET"
    path: str = Field(pattern=r"^/[-A-Za-z0-9_./]*$")
    expect: dict[str, str] | None = None


class GraphqlRestoreCheck(BaseModel):
    """One named GitLab GraphQL query to run after restore.

    ``query_name`` selects a query owned by the GraphQL client. ``expect`` is
    a subset of the ``data`` object. Backup records the check and does not
    perform it.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["graphql"] = "graphql"
    query_name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    expect: dict[str, Any] | None = None


RestoreCheck = Annotated[
    RestRestoreCheck | GraphqlRestoreCheck,
    Field(discriminator="kind"),
]


class RestoreValidationPlan(BaseModel):
    """API expectations captured with the backup.

    A later validator walks ``checks`` and dispatches on ``kind``. A new API
    check is a new model added to :data:`RestoreCheck`.
    """

    model_config = ConfigDict(extra="forbid")

    checks: list[RestoreCheck] = Field(default_factory=list)


class GitLabEnvironment(BaseModel):
    """GitLab facts known when the backup was published."""

    model_config = ConfigDict(extra="forbid")

    role: str = ""
    gitlab_env: str = ""
    compose_project: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    external_url: str = ""
    external_hostname: str = ""
    ee_version: str = ""
    ee_container: str = ""
    deployment: str = "compose"

    @field_validator("external_url", "external_hostname", "ee_version")
    @classmethod
    def no_whitespace(cls, value: str) -> str:
        if any(character.isspace() for character in value):
            raise ValueError("must not contain whitespace")
        return value


class DockerHost(BaseModel):
    """Host paths recorded with the backup. Empty when the caller did not set them."""

    model_config = ConfigDict(extra="forbid")

    inventory_hostname: str = ""
    lan_ip: str = ""
    backup_bind: str = ""
    data_root: str = ""
    deploy_dir: str = ""


class ControlRecord(BaseModel):
    """Who requested the backup. Empty when the caller did not set them."""

    model_config = ConfigDict(extra="forbid")

    inventory: str = ""
    node: str = ""
    playbook: str = ""


class BackupArtifacts(BaseModel):
    """The GitLab application tar inside the outer archive."""

    model_config = ConfigDict(extra="forbid")

    application_tar: str
    backup_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    sha256: str
    members: list[str] = Field(default_factory=lambda: list(INNER_REQUIRED))
    omitted: list[str] = Field(
        default_factory=list,
        description=(
            "Components absent from the application tar because the publisher "
            "allowed it. Empty means registry, LFS, and packages are present."
        ),
    )

    @field_validator("sha256")
    @classmethod
    def lowercase_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("sha256 must be 64 lowercase hex digits")
        return value

    @model_validator(mode="after")
    def tar_matches_id_and_members(self) -> BackupArtifacts:
        expected = f"{self.backup_id}_gitlab_backup.tar"
        if self.application_tar != expected:
            raise ValueError("application_tar must be the backup id plus _gitlab_backup.tar")
        unknown = [name for name in self.omitted if name not in INNER_REQUIRED]
        if unknown:
            raise ValueError(f"omitted has unknown components: {', '.join(unknown)}")
        overlap = [name for name in self.omitted if name in self.members]
        if overlap:
            raise ValueError(f"omitted components are also present: {', '.join(overlap)}")
        missing = [
            name
            for name in INNER_REQUIRED
            if name not in self.members and name not in self.omitted
        ]
        if missing:
            raise ValueError(f"application tar is missing {', '.join(missing)}")
        return self


class BackupManifest(BaseModel):
    """Provenance stored inside the backup archive."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    created_at: datetime
    backup_date: date
    retention_class: str = ""
    org: str = ""
    environment: GitLabEnvironment
    docker_host: DockerHost = Field(default_factory=DockerHost)
    control: ControlRecord = Field(default_factory=ControlRecord)
    artifacts: BackupArtifacts
    restore_validation: RestoreValidationPlan = Field(default_factory=RestoreValidationPlan)

    @field_validator("created_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    @field_serializer("backup_date")
    def serialize_backup_date(self, value: date) -> str:
        return value.isoformat()

    @classmethod
    def create(
        cls,
        *,
        application_tar: str,
        sha256: str,
        compose_project: str,
        external_url: str = "",
        backup_bind: str = "",
        org: str = "",
        now: datetime | None = None,
        checks: tuple[RestoreCheck, ...] | list[RestoreCheck] = (),
        members: list[str] | None = None,
        omitted: list[str] | None = None,
    ) -> BackupManifest:
        """Build a manifest and validate its serialized JSON."""
        backup_id, version = application_identity(application_tar)
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            raise ManifestError("created_at must be timezone-aware")
        plan = recorded_checks(version=version)
        plan.extend(checks)
        manifest = cls(
            created_at=current,
            backup_date=current.astimezone(UTC).date(),
            org=org,
            environment=GitLabEnvironment(
                compose_project=compose_project,
                external_url=external_url,
                ee_version=version,
            ),
            docker_host=DockerHost(backup_bind=backup_bind),
            artifacts=BackupArtifacts(
                application_tar=application_tar,
                backup_id=backup_id,
                sha256=sha256,
                members=list(INNER_REQUIRED if members is None else members),
                omitted=list(omitted or []),
            ),
            restore_validation=RestoreValidationPlan(checks=plan),
        )
        return cls.model_validate_json(manifest.to_json())

    def to_json(self) -> str:
        return self.model_dump_json(indent=2) + "\n"


def parse_allow_missing(value: str | None) -> tuple[str, ...]:
    """Map ``registry,lfs,packages`` to application-tar member names.

    An empty value requires every component. GitLab's ``SKIP`` can omit
    ``registry``, ``lfs``, and ``packages``. An object-storage install also
    leaves those members out of the tar.
    """
    if value is None or value.strip() == "":
        return ()
    files: list[str] = []
    for part in value.split(","):
        key = part.strip()
        if key not in COMPONENT_FILES:
            raise ManifestError("allow-missing accepts registry, lfs, and packages")
        filename = COMPONENT_FILES[key]
        if filename not in files:
            files.append(filename)
    return tuple(files)


def split_members(present: set[str], allow_missing: set[str]) -> tuple[list[str], list[str]]:
    """Return present component files and the allowed absences."""
    unknown = sorted(allow_missing - set(INNER_REQUIRED))
    if unknown:
        raise ManifestError(f"unknown component {', '.join(unknown)}")
    missing = [name for name in INNER_REQUIRED if name not in allow_missing and name not in present]
    if missing:
        raise ManifestError(f"application tar is missing {', '.join(missing)}")
    members = [name for name in INNER_REQUIRED if name in present]
    omitted = [name for name in INNER_REQUIRED if name not in present]
    return members, omitted


def application_identity(name: str) -> tuple[str, str]:
    """Return the backup id and, when the GitLab name carries one, the version."""
    match = _APP_TAR.fullmatch(name)
    if match is None:
        raise ManifestError(f"application tar name is not a GitLab backup: {name}")
    backup_id = match.group("backup_id")
    version_match = _VERSION.fullmatch(backup_id)
    version = version_match.group("version") if version_match else ""
    return backup_id, version


def recorded_checks(*, version: str) -> list[RestoreCheck]:
    """REST checks a later validator can run. No call is made here."""
    checks: list[RestoreCheck] = [RestRestoreCheck(path="/-/health")]
    if version:
        checks.insert(
            0,
            RestRestoreCheck(path="/api/v4/version", expect={"version": version}),
        )
    return checks


def backup_manifest_schema() -> dict[str, Any]:
    """JSON Schema generated from :class:`BackupManifest`."""
    document: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_PATH.name,
    }
    document.update(BackupManifest.model_json_schema())
    return document


def schema_text() -> str:
    return json.dumps(backup_manifest_schema(), indent=4) + "\n"
