from pathlib import Path

import pytest

from appsweep.removal_service import RemovalService


def test_remove_leftovers_removes_allowed_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    target = home / ".config" / "example"
    target.mkdir(parents=True)
    (target / "settings.ini").write_text(
        "enabled=true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    result = RemovalService().remove_leftovers((target,))

    assert result.removed == (target,)
    assert result.failed == ()
    assert not target.exists()


def test_remove_leftovers_rejects_path_outside_allowed_roots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    target = home / "Documents" / "important.txt"
    target.parent.mkdir(parents=True)
    target.write_text("keep me\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    result = RemovalService().remove_leftovers((target,))

    assert result.removed == ()
    assert len(result.failed) == 1
    assert target.exists()


def test_remove_leftovers_rejects_protected_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    config = home / ".config"
    config.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    result = RemovalService().remove_leftovers((config,))

    assert result.removed == ()
    assert len(result.failed) == 1
    assert config.exists()


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            '{"success": true, "message": "done"}\n',
            {"success": True, "message": "done"},
        ),
        (
            "noise\n{\"success\": false, \"message\": \"failed\"}\n",
            {"success": False, "message": "failed"},
        ),
    ],
)
def test_read_helper_response(
    output: str,
    expected: dict[str, object],
) -> None:
    assert RemovalService._read_helper_response(output) == expected
