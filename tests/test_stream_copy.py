"""Pair creation must not load an application tar into memory."""

from __future__ import annotations

from pathlib import Path

from xgic.cli.gitlab.archive import _copy_bytes, _write_private


def test_copies_do_not_read_the_whole_file(tmp_path: Path, monkeypatch) -> None:
    def reject_full_read(self: Path) -> bytes:
        raise AssertionError(f"read_bytes called on {self.name}")

    def reject_full_write(self: Path, data: bytes) -> int:
        raise AssertionError(f"write_bytes called on {self.name}")

    source = tmp_path / "100_2026_01_02_1.2.3_gitlab_backup.tar"
    source.write_bytes(b"payload")
    monkeypatch.setattr(Path, "read_bytes", reject_full_read)
    monkeypatch.setattr(Path, "write_bytes", reject_full_write)
    copied = tmp_path / "copied.tar"
    _copy_bytes(source, copied)
    private = tmp_path / "nested" / "private.tar"
    _write_private(source, private)
    assert copied.open("rb").read() == b"payload"
    assert private.open("rb").read() == b"payload"
    assert oct(copied.stat().st_mode & 0o777) == oct(0o600)
    assert oct(private.stat().st_mode & 0o777) == oct(0o600)
