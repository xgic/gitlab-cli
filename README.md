# XGIC GitLab CLI

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/xgic-gitlab-cli.svg)](https://pypi.org/project/xgic-gitlab-cli/)
[![Python](https://img.shields.io/pypi/pyversions/xgic-gitlab-cli.svg)](https://pypi.org/project/xgic-gitlab-cli/)
[![Release](https://img.shields.io/github/v/release/xgic/gitlab-cli)](https://github.com/xgic/gitlab-cli/releases)
[![CI](https://github.com/xgic/gitlab-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/xgic/gitlab-cli/actions/workflows/ci.yml)

**GitLab product commands for the modular [XGIC CLI](https://github.com/xgic/cli)—ops under
`xgic gitlab …`.**

Namespace: **`xgic.cli.gitlab`** · Console group: **`xgic gitlab …`** · Brand: **XGIC CLI only**
([ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md))

Standards hub: [xgic/ai](https://github.com/xgic/ai) ·
[README standards](https://github.com/xgic/ai/blob/main/docs/readme-standards.md)

---

## Vision

Self-managed GitLab operators need a **stable, public-safe command surface** for versioned ops—
not a grab bag of one-off scripts. This module owns the **GitLab product** namespace under `xgic`.
The GraphQL client library lives in [gitlab-graphql](https://github.com/xgic/gitlab-graphql);
the Compose **template** and orchestration **image producer** live in
[gitlab](https://github.com/xgic/gitlab) and [gitlab-dev](https://github.com/xgic/gitlab-dev).

One brand (`xgic`), clear ownership, and no private hosts or tracker IDs in the package.

---

## Why this module exists

| Benefit | Detail |
|---------|--------|
| **Domain clarity** | Nested under `xgic gitlab`—no clash with core or Payload commands |
| **Composable stack** | Depends on `xgic-cli`; optional GraphQL extra when automation lands |
| **Public-safe by design** | Endpoints via env/flags—never hard-coded private inventory |
| **AI + human parity** | Same command map in README and [AGENTS.md](AGENTS.md) |
| **Open-source rigor** | Apache-2.0, Python 3.14+, RC → TestPyPI → PyPI |

---

## Ecosystem

| Package / repo | Role |
|----------------|------|
| [xgic/cli](https://github.com/xgic/cli) | Thin core framework (`xgic`) |
| [xgic/gitlab-graphql](https://github.com/xgic/gitlab-graphql) | GraphQL client library |
| **This repo** | GitLab product module (`xgic.cli.gitlab`) |
| [xgic/gitlab-dev](https://github.com/xgic/gitlab-dev) | Orchestration image **producer** (`ghcr.io/xgic/xgic-gitlab`) |
| [xgic/gitlab](https://github.com/xgic/gitlab) | End-user Docker Compose **template** |

Architecture: [ADR-0001](https://github.com/xgic/ai/blob/main/docs/adr/0001-xgic-gitlab-architecture-and-repository-naming.md)
· [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md).

---

## Quick start

### Development (editable) — current primary path

```bash
uv pip install -e ../cli
uv pip install -e ".[dev]"
xgic gitlab --help
xgic gitlab info
```

Optional GraphQL extra (when GraphQL-backed commands ship):

```bash
uv pip install -e ".[graphql]"
```

### Install (PyPI)

[xgic-gitlab-cli 0.1.1](https://pypi.org/project/xgic-gitlab-cli/0.1.1/) is on PyPI.
Further cuts follow the hub
[python-package-release.md](https://github.com/xgic/ai/blob/main/docs/python-package-release.md)
path (RC → TestPyPI → PyPI).

```bash
uv pip install "xgic-gitlab-cli"
xgic gitlab --help
```

### Requirements

- Python **3.14+**
- `xgic-cli` ≥ 0.2.1
- Docker / Docker Compose for stack ops (`health` / `backup` / `restore`)

---

## Console commands

All product commands nest under **`xgic gitlab`**:

| Command | Purpose |
|---------|---------|
| `xgic gitlab info` | Module version and status (`--json` supported) |
| `xgic gitlab health` | Compose service checks + optional HTTP `/-/health` |
| `xgic gitlab backup` | `gitlab-backup create` via `docker compose exec` |
| `xgic gitlab restore <id>` | Destructive restore (`--yes` required; prefer `--dry-run` first) |

### Configuration (no private host defaults)

| Setting | Flag | Environment |
|---------|------|-------------|
| Compose file | `--compose-file` | `XGIC_GITLAB_COMPOSE_FILE` (default `docker-compose.yml`) |
| Project name | `--project` | `XGIC_GITLAB_COMPOSE_PROJECT` (default `xgic-gitlab`) |
| GitLab EE service | `--gitlab-service` | `XGIC_GITLAB_EE_SERVICE` (default `gitlab-ee`) |
| Orchestration service | `--xgic-service` | `XGIC_GITLAB_ORCH_SERVICE` (default `xgic-gitlab`) |
| Backup dir hint | `--backup-dir` | `XGIC_GITLAB_BACKUP_DIR` |
| GitLab URL | `--url` | `GITLAB_URL` (**no default**) |
| Token | `--token` | `GITLAB_TOKEN` (never logged) |

Shared: `--dry-run`, `--json`.

### Examples

```bash
# From a checked-out xgic/gitlab template directory
export GITLAB_URL=http://localhost:8929
xgic gitlab health --json
xgic gitlab backup --dry-run
xgic gitlab restore 20240101_1200 --dry-run
# after confirmation:
xgic gitlab restore 20240101_1200 --yes
```

---

## Status

**0.1.1 — experimental.** Nested `xgic gitlab` commands: `info`, `health`, `backup`, `restore` against
Docker Compose stacks (typically [xgic/gitlab](https://github.com/xgic/gitlab)).

---

## AI agent guidance

- Use **`xgic gitlab …`** for product ops; do not hardcode private GitLab hostnames in public
  artifacts or committed examples.
- Prefer **fictional placeholders** (`https://gitlab.example.com`) in docs and tests.
- Destructive restore always needs **`--yes`**; start with **`--dry-run`**.
- Follow hub
  [public-safe](https://github.com/xgic/ai/blob/main/docs/BASE-STANDARDS-FOR-ORCHESTRATED-REPOS.md)
  rules before any public GitHub write.

---

## Public safety

This package is **public-safe only**. Do not hardcode private GitLab hosts, internal inventory, or
private tracker IDs. Operators configure endpoints via environment / flags.

---

## Publishing

Follow
[python-package-release.md](https://github.com/xgic/ai/blob/main/docs/python-package-release.md)
(publish **after** `xgic-cli` for stack releases). Tags: `vX.Y.ZrcN` → TestPyPI; `vX.Y.Z` → PyPI.

---

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).  
Copyright form: `Copyright 2026 XGIC`.
