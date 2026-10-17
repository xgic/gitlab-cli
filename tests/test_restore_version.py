"""Product-release comparison for restore. Versions here are fixtures."""

from __future__ import annotations

from xgic.cli.gitlab.manifest import (
    ManifestError,
    product_release,
    same_product_release,
    version_from_env_info,
)


def test_image_build_suffix_is_the_same_release() -> None:
    assert product_release("19.4.2-ee.0") == "19.4.2-ee"
    assert same_product_release("19.4.2-ee", "19.4.2-ee.0")


def test_different_release_does_not_match() -> None:
    assert not same_product_release("19.2.1-ee", "19.4.2-ee")
    assert not same_product_release("19.4.2-ce", "19.4.2-ee.0")
    assert not same_product_release("", "19.4.2-ee")


def test_unrecognized_version_is_rejected() -> None:
    try:
        product_release("not-a-version")
    except ManifestError:
        return
    raise AssertionError("expected ManifestError")


class _Proc:
    def __init__(self, code: int, stdout: str) -> None:
        self.returncode = code
        self.stdout = stdout
        self.stderr = ""


class _Runner:
    def __init__(self, proc: _Proc | None) -> None:
        self.proc = proc
        self.calls: list[tuple[str, list[str], bool]] = []

    def exec_service(self, service: str, command: list[str], *, dry_run: bool) -> _Proc | None:
        self.calls.append((service, list(command), dry_run))
        return self.proc


def test_mismatch_is_reported_without_a_further_call() -> None:
    from xgic.cli.gitlab.commands.restore import _release_mismatch

    runner = _Runner(_Proc(0, "Version:\t19.4.2-ee.0\n"))
    detail = _release_mismatch(runner, "gitlab", "19.2.1-ee")
    assert detail is not None
    assert "does not match" in detail
    assert runner.calls == [("gitlab", ["gitlab-rake", "gitlab:env:info"], False)]


def test_suffix_match_allows_the_restore() -> None:
    from xgic.cli.gitlab.commands.restore import _release_mismatch

    runner = _Runner(_Proc(0, "Version:\t19.4.2-ee.0\n"))
    assert _release_mismatch(runner, "gitlab", "19.4.2-ee") is None


def test_archive_without_a_release_does_not_query_the_service() -> None:
    from xgic.cli.gitlab.commands.restore import _release_mismatch

    runner = _Runner(None)
    assert _release_mismatch(runner, "gitlab", "") is None
    assert runner.calls == []


def test_unreadable_target_refuses_the_restore() -> None:
    from xgic.cli.gitlab.commands.restore import _release_mismatch

    runner = _Runner(_Proc(1, ""))
    assert _release_mismatch(runner, "gitlab", "19.4.2-ee") == (
        "cannot read the target GitLab version"
    )


def test_env_info_uses_the_gitlab_version_line() -> None:
    text = "\n".join(
        [
            "Ruby Version:\t3.3.12",
            "Version:\t19.4.2-ee",
            "DB Version:\t17.11",
            "Version:\t14.57.3",
        ]
    )
    assert version_from_env_info(text) == "19.4.2-ee"
