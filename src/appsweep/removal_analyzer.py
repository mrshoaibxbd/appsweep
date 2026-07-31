import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import apt

from appsweep.models import InstalledApplication


@dataclass(frozen=True, slots=True)
class RemovalAnalysis:
    package_name: str
    installed_size: int
    additional_removals: tuple[str, ...]
    dependent_packages: tuple[str, ...]
    leftover_paths: tuple[Path, ...]


class RemovalAnalyzer:
    def analyze(self, application: InstalledApplication) -> RemovalAnalysis:
        cache = apt.Cache()

        if application.package_name not in cache:
            raise ValueError(f"Package '{application.package_name}' is not available in APT.")

        package = cache[application.package_name]

        if not package.is_installed or package.installed is None:
            raise ValueError(f"Package '{application.package_name}' is not installed.")

        simulated_removals = self._simulate_purge(application.package_name)
        additional_removals = tuple(
            name for name in simulated_removals if name != application.package_name
        )

        return RemovalAnalysis(
            package_name=application.package_name,
            installed_size=package.installed.installed_size,
            additional_removals=additional_removals,
            dependent_packages=self._installed_reverse_dependencies(application.package_name),
            leftover_paths=self._find_leftovers(application),
        )

    @staticmethod
    def _simulate_purge(package_name: str) -> tuple[str, ...]:
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"

        result = subprocess.run(
            [
                "apt-get",
                "--simulate",
                "purge",
                package_name,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )

        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(message or "APT simulation failed.")

        removals: list[str] = []

        for line in result.stdout.splitlines():
            if not line.startswith("Remv "):
                continue

            fields = line.split()

            if len(fields) >= 2:
                removals.append(fields[1])

        return tuple(dict.fromkeys(removals))

    @staticmethod
    def _installed_reverse_dependencies(
        package_name: str,
    ) -> tuple[str, ...]:
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"

        result = subprocess.run(
            ["apt-cache", "rdepends", "--installed", package_name],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )

        if result.returncode != 0:
            return ()

        dependencies: list[str] = []

        for line in result.stdout.splitlines()[2:]:
            candidate = line.strip()

            if not candidate:
                continue

            if candidate.startswith("|"):
                candidate = candidate[1:].strip()

            if candidate and " " not in candidate:
                dependencies.append(candidate)

        return tuple(sorted(set(dependencies), key=str.casefold))

    @staticmethod
    def _find_leftovers(
        application: InstalledApplication,
    ) -> tuple[Path, ...]:
        home = Path.home()
        desktop_stem = Path(application.desktop_file).stem

        identifiers = {
            application.package_name,
            desktop_stem,
        }

        roots = (
            home / ".config",
            home / ".cache",
            home / ".local" / "share",
            home / ".local" / "state",
        )

        candidates: set[Path] = set()

        for root in roots:
            for identifier in identifiers:
                candidate = root / identifier

                if candidate.exists() or candidate.is_symlink():
                    candidates.add(candidate)

        desktop_launcher = home / ".local" / "share" / "applications" / f"{desktop_stem}.desktop"

        if desktop_launcher.exists() or desktop_launcher.is_symlink():
            candidates.add(desktop_launcher)

        return tuple(sorted(candidates, key=lambda path: str(path).casefold()))
