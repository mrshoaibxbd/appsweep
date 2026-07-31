from appsweep import __version__
from appsweep.application import APP_ID


def test_application_metadata() -> None:
    assert APP_ID == "tech.shoaib.AppSweep"
    assert __version__ == "0.1.0"
