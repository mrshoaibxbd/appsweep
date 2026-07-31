from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstalledApplication:
    package_name: str
    display_name: str
    version: str
    summary: str
    desktop_file: str
    icon_name: str
