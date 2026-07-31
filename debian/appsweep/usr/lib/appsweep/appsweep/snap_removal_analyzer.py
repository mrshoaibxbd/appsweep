from dataclasses import dataclass
from pathlib import Path

from appsweep.models import InstalledApplication


@dataclass(frozen=True, slots=True)
class SnapRemovalAnalysis:
    snap_name: str
    user_data_paths: tuple[Path, ...]
    protected: bool
    protection_reason: str


class SnapRemovalAnalyzer:
    protected_snaps = frozenset(
        {
            "snapd",
            "bare",
            "core",
            "core18",
            "core20",
            "core22",
            "core24",
            "gtk-common-themes",
        }
    )

    protected_prefixes = (
        "gnome-",
        "desktop-security-center",
    )

    def analyze(self, application: InstalledApplication) -> SnapRemovalAnalysis:
        snap_name = application.package_name

        protected = snap_name in self.protected_snaps or snap_name.startswith(
            self.protected_prefixes
        )

        reason = (
            "This Snap provides platform, runtime, or desktop components required "
            "by other installed Snap applications."
            if protected
            else ""
        )

        data_path = Path.home() / "snap" / snap_name
        paths = (data_path,) if data_path.exists() or data_path.is_symlink() else ()

        return SnapRemovalAnalysis(
            snap_name=snap_name,
            user_data_paths=paths,
            protected=protected,
            protection_reason=reason,
        )
