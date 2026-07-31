from pathlib import Path

from appsweep.flatpak_removal_analyzer import FlatpakRemovalAnalyzer
from appsweep.models import InstalledApplication, PackageBackend


def create_application(scope: str = "user") -> InstalledApplication:
    return InstalledApplication(
        package_name="org.example.App",
        display_name="Example",
        version="1.0",
        summary="Example Flatpak",
        desktop_file="",
        icon_name="org.example.App",
        backend=PackageBackend.FLATPAK,
        installation_scope=scope,
    )


def test_detects_flatpak_user_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    data_path = home / ".var" / "app" / "org.example.App"
    data_path.mkdir(parents=True)

    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: home),
    )

    analysis = FlatpakRemovalAnalyzer().analyze(create_application())

    assert analysis.application_id == "org.example.App"
    assert analysis.scope == "user"
    assert analysis.user_data_paths == (data_path,)


def test_handles_missing_flatpak_user_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: home),
    )

    analysis = FlatpakRemovalAnalyzer().analyze(create_application("system"))

    assert analysis.scope == "system"
    assert analysis.user_data_paths == ()
