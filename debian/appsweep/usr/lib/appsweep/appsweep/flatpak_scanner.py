import shutil
import subprocess
from pathlib import Path

from gi.repository import Gio, GLib

from appsweep.models import InstalledApplication, PackageBackend


class FlatpakScanner:
    def scan(self) -> list[InstalledApplication]:
        executable = shutil.which("flatpak")

        if executable is None:
            return []

        applications = [
            *self._scan_scope(executable, "user"),
            *self._scan_scope(executable, "system"),
        ]

        return sorted(
            applications,
            key=lambda item: (
                item.display_name.casefold(),
                item.package_name.casefold(),
                item.installation_scope,
            ),
        )

    def _scan_scope(
        self,
        executable: str,
        scope: str,
    ) -> list[InstalledApplication]:
        result = subprocess.run(
            [
                executable,
                f"--{scope}",
                "list",
                "--app",
                "--columns=application,name,version,description",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={
                "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                "LC_ALL": "C",
            },
        )

        if result.returncode != 0:
            return []

        applications: list[InstalledApplication] = []

        for line in result.stdout.splitlines():
            fields = line.split("\t")

            if not fields or not fields[0].strip():
                continue

            application_id = fields[0].strip()
            name = self._field(fields, 1) or application_id
            version = self._field(fields, 2)
            description = self._field(fields, 3)
            desktop_file = self._desktop_file(application_id, scope)
            app_info = self._load_desktop_file(desktop_file)

            icon_name = ""
            display_name = name
            summary = description

            if app_info is not None:
                display_name = app_info.get_display_name() or app_info.get_name() or display_name
                summary = app_info.get_description() or summary

                icon = app_info.get_icon()

                if icon is not None:
                    icon_name = icon.to_string() or ""

            applications.append(
                InstalledApplication(
                    package_name=application_id,
                    display_name=display_name.strip(),
                    version=version,
                    summary=summary.strip(),
                    desktop_file=(str(desktop_file) if desktop_file is not None else ""),
                    icon_name=icon_name,
                    backend=PackageBackend.FLATPAK,
                    installation_scope=scope,
                )
            )

        return applications

    @staticmethod
    def _field(fields: list[str], index: int) -> str:
        if index >= len(fields):
            return ""

        return fields[index].strip()

    @staticmethod
    def _desktop_file(
        application_id: str,
        scope: str,
    ) -> Path | None:
        if scope == "user":
            path = (
                Path.home()
                / ".local"
                / "share"
                / "flatpak"
                / "exports"
                / "share"
                / "applications"
                / f"{application_id}.desktop"
            )
        else:
            path = Path("/var/lib/flatpak/exports/share/applications") / f"{application_id}.desktop"

        if path.is_file():
            return path

        return None

    @staticmethod
    def _load_desktop_file(
        desktop_file: Path | None,
    ) -> Gio.DesktopAppInfo | None:
        if desktop_file is None:
            return None

        try:
            return Gio.DesktopAppInfo.new_from_filename(str(desktop_file))
        except (TypeError, GLib.Error):
            return None
