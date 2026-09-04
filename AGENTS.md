# AI Agent Instructions — XGIC GitLab CLI

Public repository. Follow https://github.com/xgic/ai for multi-repo standards.

## Product

- **Package:** `xgic.cli.gitlab` (distribution `xgic-gitlab-cli`)
- **Depends on:** `xgic-cli` (thin core); optional `xgic-gitlab-graphql`
- **Architecture:** [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md)

## Scope

- Nested `xgic gitlab …` product commands via entry points (`xgic.cli.commands`)
- Missing ACTION prints full usage (exit 2)
- GitLab ops helpers for public exemplary use (`health` / `backup` / `restore` via Compose + env/flags)
- GraphQL automation via [xgic/gitlab-graphql](https://github.com/xgic/gitlab-graphql) when wired

## Out of scope

- Private host defaults or internal inventory
- Thin CLI framework / env detection → https://github.com/xgic/cli
- Dev Container / Docker Compose lifecycle → https://github.com/xgic/dev-cli
- Payload CMS commands → https://github.com/xgic/payload-cms-cli

## Rules


**Public GitHub writes:** Before `gh issue create|edit`, `gh pr create|edit`, or any public comment on this repository, complete the **mandatory public-safe draft gate** in https://github.com/xgic/ai/blob/main/docs/BASE-STANDARDS-FOR-ORCHESTRATED-REPOS.md (fictional placeholders only; never name private hosts, private projects, or private tracker IDs). Optional helper from the hub clone: `python scripts/public-safe-scan.py path/to/draft.md`.
- Public-safe content only
- Human UI review before merge to `main`
- Dedicated issue-number branches; Conventional Commits
- **Labels required** on issues/PRs (see community-health)
- Python 3.14+; Apache-2.0; root `CODEOWNERS` (`@xgic`)
- **No intermediate** `xgic/cli/__init__.py` that clobbers core
- **PyPI releases:** https://github.com/xgic/ai/blob/main/docs/python-package-release.md

