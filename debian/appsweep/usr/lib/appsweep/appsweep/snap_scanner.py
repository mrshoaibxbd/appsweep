import shutil
import subprocess
from pathlib import Path

from gi.repository import Gio, GLib

from appsweep.models import InstalledApplication, PackageBackend


class SnapScanner:
    desktop_directory = Path("/var/lib/snapd/desktop/applications")

    def scan(self) -> list[InstalledApplication]:
        if shutil.which("snap") is None:
            return []

        installed_snaps = self._installed_snaps()

        if not installed_snaps or not self.desktop_directory.is_dir():
            return []

        applications: dict[tuple[str, str], InstalledApplication] = {}

        for desktop_file in sorted(self.desktop_directory.glob("*.desktop")):
            app_info = self._load_desktop_file(desktop_file)

            if app_info is None:
                continue

            if app_info.get_is_hidden() or not app_info.should_show():
                continue

            snap_name = self._snap_name_from_desktop_file(desktop_file)

            if snap_name not in installed_snaps:
                continue

            display_name = app_info.get_display_name() or app_info.get_name()

            if not display_name:
                continue

            metadata = installed_snaps[snap_name]
            icon = app_info.get_icon()

            application = InstalledApplication(
                package_name=snap_name,
                display_name=display_name.strip(),
                version=metadata["version"],
                summary=(app_info.get_description() or metadata["summary"]).strip(),
                desktop_file=str(desktop_file),
                icon_name=icon.to_string() if icon is not None else "",
                backend=PackageBackend.SNAP,
            )

            key = (snap_name, application.display_name.casefold())
            applications[key] = application

        return sorted(
            applications.values(),
            key=lambda item: item.display_name.casefold(),
        )

    @staticmethod
    def _installed_snaps() -> dict[str, dict[str, str]]:
        result = subprocess.run(
            ["/usr/bin/snap", "list", "--unicode=never"],
            capture_output=True,
            text=True,
            check=False,
            env={
                "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                "LC_ALL": "C",
            },
        )

        if result.returncode != 0:
            return {}

        snaps: dict[str, dict[str, str]] = {}

        for line in result.stdout.splitlines()[1:]:
            fields = line.split()

            if len(fields) < 2:
                continue

            name = fields[0]
            version = fields[1]

            snaps[name] = {
                "version": version,
                "summary": f"Snap package {name}",
            }

        return snaps

    @staticmethod
    def _snap_name_from_desktop_file(desktop_file: Path) -> str:
        return desktop_file.stem.split("_", 1)[0]

    @staticmethod
    def _load_desktop_file(
        desktop_file: Path,
    ) -> Gio.DesktopAppInfo | None:
        try:
            return Gio.DesktopAppInfo.new_from_filename(str(desktop_file))
        except (TypeError, GLib.Error):
            return None
