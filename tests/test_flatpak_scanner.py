from pathlib import Path

from appsweep.flatpak_scanner import FlatpakScanner


def test_reads_existing_field() -> None:
    fields = [
        "org.example.App",
        "Example",
        "1.0",
        "Example application",
    ]

    assert FlatpakScanner._field(fields, 1) == "Example"
    assert FlatpakScanner._field(fields, 3) == "Example application"


def test_missing_field_returns_empty_string() -> None:
    assert FlatpakScanner._field(["org.example.App"], 2) == ""


def test_load_desktop_file_accepts_none() -> None:
    assert FlatpakScanner._load_desktop_file(None) is None


def test_system_desktop_file_returns_none_when_missing() -> None:
    result = FlatpakScanner._desktop_file(
        "tech.shoaib.AppSweep.DoesNotExist",
        "system",
    )

    assert result is None


def test_user_desktop_file_returns_none_when_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: tmp_path),
    )

    result = FlatpakScanner._desktop_file(
        "tech.shoaib.AppSweep.DoesNotExist",
        "user",
    )

    assert result is None
