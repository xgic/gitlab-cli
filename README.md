# XGIC GitLab CLI

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/xgic/gitlab-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/xgic/gitlab-cli/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.14+-blue?logo=python&logoColor=white)](https://www.python.org/)

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

PyPI publish follows the hub
[python-package-release.md](https://github.com/xgic/ai/blob/main/docs/python-package-release.md)
path (RC → TestPyPI → PyPI). Until the first release is published:

```bash
# After first PyPI release:
uv pip install "xgic-cli>=0.2.0" "xgic-gitlab-cli"
xgic gitlab --help
```

---

## Console commands

All product commands nest under **`xgic gitlab`**:

| Command | Purpose |
|---------|---------|
| `xgic gitlab info` | Module version and status (`--json` supported) |

**Planned (not yet implemented):** `backup`, `restore`, `health`, and related ops.

---

## Status

**0.1.0 — bootstrap.** Nested `xgic gitlab` group with `info` stub. Backup/restore and health
automation land in later slices.

### Requirements

- Python **3.14+**
- `xgic-cli` ≥ 0.2.0

---

## AI agent guidance

- Use **`xgic gitlab …`** for product ops; do not hardcode private GitLab hostnames in public
  artifacts or committed examples.
- Prefer **fictional placeholders** (`https://gitlab.example.com`) in docs and tests.
- Follow hub
  [public-safe](https://github.com/xgic/ai/blob/main/docs/BASE-STANDARDS-FOR-ORCHESTRATED-REPOS.md)
  rules before any public GitHub write.

---

## Public safety

This package is **public-safe only**. Do not hardcode private GitLab hosts, internal inventory, or
private tracker IDs. Operators configure endpoints via environment / flags when commands land.

---

## Publishing

Follow
[python-package-release.md](https://github.com/xgic/ai/blob/main/docs/python-package-release.md)
(publish **after** `xgic-cli` for stack releases). Tags: `vX.Y.ZrcN` → TestPyPI; `vX.Y.Z` → PyPI.

---

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).  
Copyright form: `Copyright 2026 XGIC`.
