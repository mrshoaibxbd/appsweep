import json
import tarfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from appsweep.models import InstalledApplication
from appsweep.removal_analyzer import RemovalAnalysis


@dataclass(frozen=True, slots=True)
class BackupResult:
    directory: Path
    archive: Path | None
    manifest: Path


class BackupManager:
    def __init__(self) -> None:
        self._root = Path.home() / ".local" / "share" / "appsweep" / "backups"

    def create(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
    ) -> BackupResult:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        directory = self._root / f"{application.package_name}-{timestamp}"
        directory.mkdir(parents=True, exist_ok=False)

        archive = self._create_archive(directory, analysis.leftover_paths)
        manifest = directory / "manifest.json"

        manifest.write_text(
            json.dumps(
                {
                    "created_at": datetime.now(UTC).isoformat(),
                    "application": asdict(application),
                    "analysis": {
                        "package_name": analysis.package_name,
                        "installed_size": analysis.installed_size,
                        "additional_removals": analysis.additional_removals,
                        "dependent_packages": analysis.dependent_packages,
                        "leftover_paths": [
                            str(path) for path in analysis.leftover_paths
                        ],
                    },
                    "archive": archive.name if archive else None,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return BackupResult(
            directory=directory,
            archive=archive,
            manifest=manifest,
        )

    @staticmethod
    def _create_archive(
        directory: Path,
        paths: tuple[Path, ...],
    ) -> Path | None:
        existing_paths = [
            path
            for path in paths
            if path.exists() or path.is_symlink()
        ]

        if not existing_paths:
            return None

        archive = directory / "user-data.tar.gz"
        home = Path.home()

        with tarfile.open(archive, "w:gz") as tar:
            for path in existing_paths:
                try:
                    archive_name = path.relative_to(home)
                except ValueError:
                    continue

                tar.add(
                    path,
                    arcname=str(archive_name),
                    recursive=True,
                )

        return archive
