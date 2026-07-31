from appsweep import __version__
from appsweep.application import APP_ID
from appsweep.models import InstalledApplication


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
