import subprocess
from pathlib import Path

import apt
from gi.repository import Gio, GLib

from appsweep.models import InstalledApplication


class AptScanner:
    desktop_directories = (
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
    )

    def scan(self) -> list[InstalledApplication]:
        cache = apt.Cache()
        applications: dict[str, InstalledApplication] = {}

        for desktop_file in self._desktop_files():
            app_info = self._load_desktop_file(desktop_file)

            if app_info is None:
                continue

            if app_info.get_is_hidden() or not app_info.should_show():
                continue

            package_name = self._package_owner(desktop_file)

            if package_name is None or package_name not in cache:
                continue

            package = cache[package_name]
            installed = package.installed

            if not package.is_installed or installed is None:
                continue

            display_name = app_info.get_display_name() or app_info.get_name()

            if not display_name:
                continue

            description = app_info.get_description() or installed.summary or ""
            icon = app_info.get_icon()
            icon_name = icon.to_string() if icon is not None else ""

            application = InstalledApplication(
                package_name=package_name,
                display_name=display_name.strip(),
                version=installed.version or "",
                summary=description.strip(),
                desktop_file=str(desktop_file),
                icon_name=icon_name,
            )

            existing = applications.get(package_name)

            if existing is None or len(application.display_name) < len(
                existing.display_name
            ):
                applications[package_name] = application

        return sorted(
            applications.values(),
            key=lambda item: item.display_name.casefold(),
        )

    def _desktop_files(self) -> list[Path]:
        files: list[Path] = []

        for directory in self.desktop_directories:
            if directory.is_dir():
                files.extend(directory.glob("*.desktop"))

        return sorted(files)

    @staticmethod
    def _load_desktop_file(
        desktop_file: Path,
    ) -> Gio.DesktopAppInfo | None:
        try:
            return Gio.DesktopAppInfo.new_from_filename(str(desktop_file))
        except (TypeError, GLib.Error):
            return None

    @staticmethod
    def _package_owner(desktop_file: Path) -> str | None:
        result = subprocess.run(
            ["dpkg-query", "-S", str(desktop_file)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        owner, separator, _path = result.stdout.partition(": ")

        if not separator:
            return None

        package_name = owner.split(":", 1)[0].strip()
        return package_name or None
