from dataclasses import dataclass
from enum import StrEnum


class PackageBackend(StrEnum):
    APT = "apt"
    SNAP = "snap"
    FLATPAK = "flatpak"


@dataclass(frozen=True, slots=True)
class InstalledApplication:
    package_name: str
    display_name: str
    version: str
    summary: str
    desktop_file: str
    icon_name: str
    backend: PackageBackend = PackageBackend.APT
    installation_scope: str = ""
