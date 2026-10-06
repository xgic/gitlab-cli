"""Keep command tests off the operator's home config file."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_home_gitlab_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("xgic.cli.gitlab.config.default_config_path", lambda: None)
