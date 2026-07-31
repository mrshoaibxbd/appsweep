from appsweep.apt_scanner import AptScanner
from appsweep.models import InstalledApplication
from appsweep.snap_scanner import SnapScanner


class ApplicationScanner:
    def __init__(self) -> None:
        self._apt_scanner = AptScanner()
        self._snap_scanner = SnapScanner()

    def scan(self) -> list[InstalledApplication]:
        applications = [
            *self._apt_scanner.scan(),
            *self._snap_scanner.scan(),
        ]

        return sorted(
            applications,
            key=lambda item: (
                item.display_name.casefold(),
                item.backend.value,
                item.package_name,
            ),
        )
