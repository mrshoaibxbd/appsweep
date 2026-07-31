from appsweep.models import InstalledApplication, PackageBackend
from appsweep.snap_removal_analyzer import SnapRemovalAnalyzer


def create_application(name: str) -> InstalledApplication:
    return InstalledApplication(
        package_name=name,
        display_name=name.title(),
        version="1.0",
        summary="Test Snap",
        desktop_file=f"/var/lib/snapd/desktop/applications/{name}_{name}.desktop",
        icon_name=name,
        backend=PackageBackend.SNAP,
    )


def test_allows_regular_snap() -> None:
    analysis = SnapRemovalAnalyzer().analyze(create_application("firefox"))

    assert analysis.protected is False


def test_protects_core_snap() -> None:
    analysis = SnapRemovalAnalyzer().analyze(create_application("core24"))

    assert analysis.protected is True


def test_protects_gnome_runtime_snap() -> None:
    analysis = SnapRemovalAnalyzer().analyze(create_application("gnome-46-2404"))

    assert analysis.protected is True
