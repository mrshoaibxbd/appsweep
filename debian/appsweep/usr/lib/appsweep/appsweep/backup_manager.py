import hashlib
import json
import tarfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from appsweep.models import InstalledApplication
from appsweep.removal_analyzer import RemovalAnalysis


@dataclass(frozen=True, slots=True)
class BackupResult:
    directory: Path
    archive: Path | None
    manifest: Path


@dataclass(frozen=True, slots=True)
class BackupVerification:
    valid: bool
    message: str


class BackupManager:
    def __init__(self) -> None:
        self._root = Path.home() / ".local" / "share" / "appsweep" / "backups"

    def create(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
    ) -> BackupResult:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        directory = self._next_available_directory(
            self._root / f"{application.package_name}-{timestamp}"
        )
        directory.mkdir(parents=True, exist_ok=False)

        archive = self._create_archive(directory, analysis.leftover_paths)
        manifest = directory / "manifest.json"

        archive_hash = self._sha256(archive) if archive is not None else None

        manifest.write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "created_at": datetime.now(UTC).isoformat(),
                    "application": asdict(application),
                    "analysis": {
                        "package_name": analysis.package_name,
                        "installed_size": analysis.installed_size,
                        "additional_removals": analysis.additional_removals,
                        "dependent_packages": analysis.dependent_packages,
                        "leftover_paths": [str(path) for path in analysis.leftover_paths],
                    },
                    "archive": {
                        "filename": archive.name,
                        "sha256": archive_hash,
                    }
                    if archive is not None
                    else None,
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

    def verify(self, result: BackupResult) -> BackupVerification:
        if not result.directory.is_dir():
            return BackupVerification(False, "Backup directory is missing.")

        if not result.manifest.is_file():
            return BackupVerification(False, "Backup manifest is missing.")

        try:
            manifest_data = json.loads(result.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return BackupVerification(
                False,
                f"Backup manifest is invalid: {error}",
            )

        if manifest_data.get("format_version") != 1:
            return BackupVerification(
                False,
                "Unsupported backup manifest format.",
            )

        archive_data = manifest_data.get("archive")

        if archive_data is None:
            if result.archive is not None:
                return BackupVerification(
                    False,
                    "Manifest and archive state do not match.",
                )

            return BackupVerification(
                True,
                "Manifest verified. No user-data archive was required.",
            )

        if result.archive is None or not result.archive.is_file():
            return BackupVerification(False, "User-data archive is missing.")

        expected_hash = archive_data.get("sha256")
        actual_hash = self._sha256(result.archive)

        if not expected_hash or actual_hash != expected_hash:
            return BackupVerification(
                False,
                "User-data archive checksum verification failed.",
            )

        try:
            with tarfile.open(result.archive, "r:gz") as archive:
                for member in archive.getmembers():
                    if not self._safe_archive_member(member.name):
                        return BackupVerification(
                            False,
                            f"Unsafe archive entry detected: {member.name}",
                        )

                archive.getmembers()
        except (OSError, tarfile.TarError) as error:
            return BackupVerification(
                False,
                f"User-data archive is invalid: {error}",
            )

        return BackupVerification(
            True,
            "Manifest, archive structure, and checksum verified.",
        )

    @staticmethod
    def _next_available_directory(preferred: Path) -> Path:
        if not preferred.exists():
            return preferred

        counter = 1

        while True:
            candidate = preferred.with_name(f"{preferred.name}-{counter}")

            if not candidate.exists():
                return candidate

            counter += 1

    @staticmethod
    def _create_archive(
        directory: Path,
        paths: tuple[Path, ...],
    ) -> Path | None:
        existing_paths = [path for path in paths if path.exists() or path.is_symlink()]

        if not existing_paths:
            return None

        archive_path = directory / "user-data.tar.gz"
        home = Path.home()

        with tarfile.open(archive_path, "w:gz") as archive:
            for path in existing_paths:
                try:
                    archive_name = path.relative_to(home)
                except ValueError:
                    continue

                archive.add(
                    path,
                    arcname=str(archive_name),
                    recursive=True,
                )

        return archive_path

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def _safe_archive_member(name: str) -> bool:
        path = PurePosixPath(name)

        return not path.is_absolute() and ".." not in path.parts and bool(path.parts)
