from dataclasses import dataclass
from pathlib import Path

from appsweep.models import InstalledApplication


@dataclass(frozen=True, slots=True)
class FlatpakRemovalAnalysis:
    application_id: str
    scope: str
    user_data_paths: tuple[Path, ...]


class FlatpakRemovalAnalyzer:
    def analyze(
        self,
        application: InstalledApplication,
    ) -> FlatpakRemovalAnalysis:
        data_path = Path.home() / ".var" / "app" / application.package_name

        paths = (data_path,) if data_path.exists() or data_path.is_symlink() else ()

        return FlatpakRemovalAnalysis(
            application_id=application.package_name,
            scope=application.installation_scope,
            user_data_paths=paths,
        )
