from pathlib import Path

from appsweep.snap_scanner import SnapScanner


def test_extracts_snap_name_from_desktop_file() -> None:
    desktop_file = Path("/var/lib/snapd/desktop/applications/firefox_firefox.desktop")

    assert SnapScanner._snap_name_from_desktop_file(desktop_file) == "firefox"


def test_extracts_name_without_command_suffix() -> None:
    desktop_file = Path("/var/lib/snapd/desktop/applications/code_code.desktop")

    assert SnapScanner._snap_name_from_desktop_file(desktop_file) == "code"
