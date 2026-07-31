from appsweep import __version__
from appsweep.application import APP_ID
from appsweep.models import InstalledApplication, PackageBackend


def test_application_metadata() -> None:
    assert APP_ID == "tech.shoaib.AppSweep"
    assert __version__ == "0.1.0"


def test_installed_application_model() -> None:
    application = InstalledApplication(
        package_name="example",
        display_name="Example",
        version="1.0",
        summary="Example application",
        desktop_file="/usr/share/applications/example.desktop",
        icon_name="example",
    )

    assert application.package_name == "example"
    assert application.display_name == "Example"
    assert application.icon_name == "example"
    assert application.backend is PackageBackend.APT


def test_snap_application_model() -> None:
    application = InstalledApplication(
        package_name="firefox",
        display_name="Firefox",
        version="149.0.2-1",
        summary="Web browser",
        desktop_file="/var/lib/snapd/desktop/applications/firefox_firefox.desktop",
        icon_name="firefox",
        backend=PackageBackend.SNAP,
    )

    assert application.backend is PackageBackend.SNAP


def test_flatpak_application_model() -> None:
    application = InstalledApplication(
        package_name="org.example.App",
        display_name="Example",
        version="1.0",
        summary="Example Flatpak",
        desktop_file="",
        icon_name="org.example.App",
        backend=PackageBackend.FLATPAK,
        installation_scope="user",
    )

    assert application.backend is PackageBackend.FLATPAK
    assert application.installation_scope == "user"
