import json
from pathlib import Path

from appsweep.backup_manager import BackupManager
from appsweep.models import InstalledApplication
from appsweep.removal_analyzer import RemovalAnalysis


def create_application() -> InstalledApplication:
    return InstalledApplication(
        package_name="example",
        display_name="Example",
        version="1.0",
        summary="Example application",
        desktop_file="/usr/share/applications/example.desktop",
        icon_name="example",
    )


def test_backup_manager_creates_and_verifies_backup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    data_path = home / ".config" / "example"
    data_path.mkdir(parents=True)
    (data_path / "settings.ini").write_text(
        "enabled=true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    analysis = RemovalAnalysis(
        package_name="example",
        installed_size=1024,
        additional_removals=(),
        dependent_packages=(),
        leftover_paths=(data_path,),
    )

    manager = BackupManager()
    result = manager.create(create_application(), analysis)
    verification = manager.verify(result)

    assert result.archive is not None
    assert result.archive.exists()
    assert result.manifest.exists()
    assert verification.valid is True

    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))

    assert manifest["format_version"] == 1
    assert manifest["application"]["package_name"] == "example"
    assert manifest["archive"]["sha256"]


def test_backup_verification_detects_modified_archive(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    data_path = home / ".config" / "example"
    data_path.mkdir(parents=True)
    (data_path / "settings.ini").write_text(
        "enabled=true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    analysis = RemovalAnalysis(
        package_name="example",
        installed_size=1024,
        additional_removals=(),
        dependent_packages=(),
        leftover_paths=(data_path,),
    )

    manager = BackupManager()
    result = manager.create(create_application(), analysis)

    assert result.archive is not None

    with result.archive.open("ab") as archive:
        archive.write(b"modified")

    verification = manager.verify(result)

    assert verification.valid is False
    assert "checksum" in verification.message.casefold()
