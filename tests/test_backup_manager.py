import json
from pathlib import Path

from appsweep.backup_manager import BackupManager
from appsweep.models import InstalledApplication
from appsweep.removal_analyzer import RemovalAnalysis


def test_backup_manager_creates_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    data_path = home / ".config" / "example"
    data_path.mkdir(parents=True)
    (data_path / "settings.ini").write_text("enabled=true\n")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    application = InstalledApplication(
        package_name="example",
        display_name="Example",
        version="1.0",
        summary="Example application",
        desktop_file="/usr/share/applications/example.desktop",
        icon_name="example",
    )

    analysis = RemovalAnalysis(
        package_name="example",
        installed_size=1024,
        additional_removals=(),
        dependent_packages=(),
        leftover_paths=(data_path,),
    )

    result = BackupManager().create(application, analysis)

    assert result.archive is not None
    assert result.archive.exists()
    assert result.manifest.exists()

    manifest = json.loads(result.manifest.read_text())
    assert manifest["application"]["package_name"] == "example"
