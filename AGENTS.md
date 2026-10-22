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
- Published backup archives are `{project}_{YYYYMMDD}T{HHMMSS}Z_{version}.tar.zst` (example `gitlab-example_20261005T120000Z_19.2.1-ee.tar.zst`). The GitLab backup id stays inside the archive.
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
- **Labels (mandatory):** Every issue and pull request gets exactly one type label in the create call: `bug`, `enhancement`, `documentation`, `standards`, or `chore`. Welcome Discussion posts use `welcome` and `documentation`. Do not put scoped GitLab labels on GitHub. https://github.com/xgic/ai/blob/main/docs/community-health.md#labels-required
- Python 3.14+; Apache-2.0; root `CODEOWNERS` (`@xgic`)
- **No intermediate** `xgic/cli/__init__.py` that clobbers core
- **PyPI releases:** https://github.com/xgic/ai/blob/main/docs/python-package-release.md
- **Release milestone:** titled `X.Y.Z`, matching the published version. The Git tag stays `vX.Y.Z`. Set it on every issue and pull request included in the release. GitHub does not copy the issue milestone onto the pull request. The candidate and the final publish share it. When the shipped version changes, move both to that `X.Y.Z` before the milestone closes. Close the parent issue, then the milestone, after the final publish and its acceptance. https://github.com/xgic/ai/blob/main/docs/work-tracking-and-checklists.md

