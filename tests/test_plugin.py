"""Tests for GitLab CLI plugin registration."""

from __future__ import annotations

import argparse
import json

from xgic.cli.gitlab.commands.info import run_info
from xgic.cli.gitlab.plugin import register


def test_register_adds_gitlab_group() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)
    args = parser.parse_args(["gitlab", "info"])
    assert args.command == "gitlab"
    assert args.gitlab_command == "info"
    assert callable(args.func)


def test_run_info_json(capsys) -> None:
    ns = argparse.Namespace(json=True)
    assert run_info(ns) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["module"] == "xgic.cli.gitlab"
    assert data["package"] == "xgic-gitlab-cli"
    assert data["status"] == "bootstrap"


def test_run_info_human(capsys) -> None:
    ns = argparse.Namespace(json=False)
    assert run_info(ns) == 0
    out = capsys.readouterr().out
    assert "GitLab CLI" in out
    assert "bootstrap" in out.lower() or "0.1.0" in out
