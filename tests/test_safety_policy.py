from appsweep.safety_policy import SafetyPolicy


def test_protects_core_system_package() -> None:
    decision = SafetyPolicy().evaluate("systemd")

    assert decision.protected is True
    assert decision.reason


def test_protects_kernel_package_prefix() -> None:
    decision = SafetyPolicy().evaluate("linux-image-7.0.0-28-generic")

    assert decision.protected is True


def test_allows_regular_application() -> None:
    decision = SafetyPolicy().evaluate("celluloid")

    assert decision.protected is False
    assert decision.reason == ""


def test_handles_multiarch_package_name() -> None:
    decision = SafetyPolicy().evaluate("libc6:amd64")

    assert decision.protected is True
