from pathlib import Path

from appsweep.removal_analyzer import RemovalAnalysis
from appsweep.window import AppSweepWindow


def test_removal_analysis_model() -> None:
    analysis = RemovalAnalysis(
        package_name="example",
        installed_size=1024,
        additional_removals=(),
        dependent_packages=("example-helper",),
        leftover_paths=(Path("/tmp/example"),),
    )

    assert analysis.package_name == "example"
    assert analysis.dependent_packages == ("example-helper",)


def test_format_size() -> None:
    assert AppSweepWindow._format_size(512) == "512 B"
    assert AppSweepWindow._format_size(1024) == "1.0 KB"
    assert AppSweepWindow._format_size(1048576) == "1.0 MB"
