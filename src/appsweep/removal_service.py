import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PackageRemovalResult:
    success: bool
    message: str
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class LeftoverRemovalResult:
    removed: tuple[Path, ...]
    failed: tuple[tuple[Path, str], ...]


class RemovalService:
    helper_path = Path("/usr/libexec/appsweep-helper")

    def purge_package(self, package_name: str) -> PackageRemovalResult:
        result = subprocess.run(
            [
                "/usr/bin/pkexec",
                str(self.helper_path),
                "--purge",
                package_name,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode in (126, 127):
            return PackageRemovalResult(
                success=False,
                message="Authentication was cancelled or denied.",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        response = self._read_helper_response(result.stdout)

        if response is None:
            return PackageRemovalResult(
                success=False,
                message="The privileged helper returned an invalid response.",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        return PackageRemovalResult(
            success=bool(response.get("success")),
            message=str(response.get("message", "Unknown helper response.")),
            stdout=str(response.get("stdout", "")),
            stderr=str(response.get("stderr", result.stderr)),
        )

    def remove_snap(
        self,
        snap_name: str,
        create_snapshot: bool,
    ) -> PackageRemovalResult:
        operation = "--remove-snap" if create_snapshot else "--purge-snap"

        result = subprocess.run(
            [
                "/usr/bin/pkexec",
                str(self.helper_path),
                operation,
                snap_name,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode in (126, 127):
            return PackageRemovalResult(
                success=False,
                message="Authentication was cancelled or denied.",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        response = self._read_helper_response(result.stdout)

        if response is None:
            return PackageRemovalResult(
                success=False,
                message="The privileged helper returned an invalid response.",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        return PackageRemovalResult(
            success=bool(response.get("success")),
            message=str(response.get("message", "Unknown helper response.")),
            stdout=str(response.get("stdout", "")),
            stderr=str(response.get("stderr", result.stderr)),
        )

    def remove_leftovers(
        self,
        paths: tuple[Path, ...],
    ) -> LeftoverRemovalResult:
        removed: list[Path] = []
        failed: list[tuple[Path, str]] = []

        for path in paths:
            try:
                self._validate_leftover_path(path)
                self._remove_path(path)
                removed.append(path)
            except Exception as error:
                failed.append((path, str(error)))

        return LeftoverRemovalResult(
            removed=tuple(removed),
            failed=tuple(failed),
        )

    @staticmethod
    def _read_helper_response(output: str) -> dict[str, object] | None:
        for line in reversed(output.splitlines()):
            candidate = line.strip()

            if not candidate:
                continue

            try:
                response = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            if isinstance(response, dict):
                return response

        return None

    @staticmethod
    def _allowed_roots() -> tuple[Path, ...]:
        home = Path.home()

        return (
            home / ".config",
            home / ".cache",
            home / ".local" / "share",
            home / ".local" / "state",
            home / "snap",
        )

    def _validate_leftover_path(self, path: Path) -> None:
        absolute_path = path.expanduser().absolute()

        if absolute_path == Path.home():
            raise ValueError("Refusing to remove the home directory.")

        for root in self._allowed_roots():
            try:
                relative = absolute_path.relative_to(root)
            except ValueError:
                continue

            if not relative.parts:
                raise ValueError(f"Refusing to remove protected root directory: {root}")

            return

        raise ValueError(f"Path is outside AppSweep's permitted user-data locations: {path}")

    @staticmethod
    def _remove_path(path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
            return

        if path.is_dir():
            shutil.rmtree(path)
            return

        if path.exists():
            raise ValueError(f"Unsupported filesystem object: {path}")
