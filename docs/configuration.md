# GitLab CLI configuration

`xgic gitlab` reads an optional JSON file. The file is a Pydantic model,
and the JSON Schema in `src/xgic/cli/gitlab/schemas/gitlab-cli.schema.json`
is generated from that model. Unknown fields are rejected. An API token is
not a field. Pass it with `--token` or `GITLAB_TOKEN`.

```mermaid
flowchart LR
  flags[Command flags]
  env[Environment variables]
  file["gitlab.json"]
  defaults[Built-in defaults]
  flags --> env --> file --> defaults
```

The default path is `~/.config/xgic/gitlab.json` when that file exists.
`--config` selects another file. Missing keys keep the built-in defaults.
A flag wins over an environment variable, and an environment variable wins
over the file for the Docker Compose settings and the GitLab URL.

```json
{
  "schema_version": 1,
  "environment": "production",
  "organization": "example",
  "backup_dir": "/var/backups/gitlab",
  "compose_file": "docker-compose.yml",
  "project_name": "xgic-gitlab",
  "gitlab_service": "gitlab-ee",
  "secrets_file": "/etc/gitlab/gitlab-secrets.json",
  "config_file": "/etc/gitlab/gitlab.rb",
  "allow_missing": [],
  "dry_run": true,
  "gitlab_url": "https://gitlab.example"
}
```

`environment` is `development`, `staging`, or `production`. Leave it unset
when a single file is not tied to one of those. `allow_missing` uses
`registry`, `lfs`, and `packages`. An empty list requires all three inside
the GitLab tar. `dry_run` defaults to false. Backup and restore treat true
as a dry-run until `--apply`. `--dry-run` forces a dry-run. Pass only one of
`--dry-run` and `--apply`.

`secrets_file` and `config_file` are copied into a backup and are not written
back. `secrets_dest` and `config_dest` are written only by a confirmed restore.

This file is the operator interface for one GitLab instance. It does not
prune old archives and it does not call the GitLab API.
