# XGIC GitLab CLI

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**XGIC GitLab CLI** (`xgic.cli.gitlab`) provides **GitLab-oriented** commands for the modular [XGIC CLI](https://github.com/xgic/cli).

Architecture: [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md).

**Publishing to PyPI:** [python-package-release.md](https://github.com/xgic/ai/blob/main/docs/python-package-release.md)  
(publish **after** `xgic-cli` for stack releases). Tags: `vX.Y.ZrcN` → TestPyPI; `vX.Y.Z` → PyPI.

| Package | Role |
|---------|------|
| [xgic/cli](https://github.com/xgic/cli) | Thin core framework (`xgic`) |
| [xgic/gitlab-graphql](https://github.com/xgic/gitlab-graphql) | GraphQL client library |
| **This repo** | GitLab product module (`xgic.cli.gitlab`) |

## Status

**0.1.0 — B6a bootstrap.** Nested `xgic gitlab` group with `info` stub. Backup/restore and health automation land in later slices.

## Requirements

- Python **3.14+**
- `xgic-cli` ≥ 0.2.0

Optional: `xgic-gitlab-graphql` via `pip install xgic-gitlab-cli[graphql]` when GraphQL-backed commands ship.

## Install (development)

```bash
python -m pip install -e ../cli
python -m pip install -e ".[dev]"
xgic gitlab --help
xgic gitlab info
```

## Console commands

All product commands are nested under **`xgic gitlab`**.

| Command | Purpose |
|---------|---------|
| `xgic gitlab info` | Module version and status (`--json` supported) |

**Planned (not yet implemented):** `backup`, `restore`, `health` and related ops.

## Public safety

This package is **public-safe only**. Do not hardcode private GitLab hosts, internal inventory, or private tracker IDs. Operators configure endpoints via environment / flags when commands land.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).  
Copyright form: `Copyright 2026 XGIC`.
