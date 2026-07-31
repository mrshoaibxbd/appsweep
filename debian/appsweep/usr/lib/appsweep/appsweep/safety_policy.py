from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProtectionDecision:
    protected: bool
    reason: str


class SafetyPolicy:
    protected_packages = frozenset(
        {
            "apt",
            "bash",
            "coreutils",
            "dbus",
            "dpkg",
            "gdm3",
            "gnome-control-center",
            "gnome-shell",
            "grub-common",
            "grub-pc",
            "grub-pc-bin",
            "libc6",
            "linux-generic",
            "linux-image-generic",
            "nautilus",
            "network-manager",
            "nm-connection-editor",
            "policykit-1",
            "polkitd",
            "sudo",
            "systemd",
            "systemd-sysv",
            "ubuntu-desktop",
            "ubuntu-desktop-minimal",
            "util-linux",
        }
    )

    protected_prefixes = (
        "linux-image-",
        "linux-modules-",
        "linux-headers-",
        "grub-",
        "shim-",
    )

    def evaluate(self, package_name: str) -> ProtectionDecision:
        normalized = package_name.split(":", 1)[0]

        if normalized in self.protected_packages:
            return ProtectionDecision(
                protected=True,
                reason="This package is required for the operating system or desktop session.",
            )

        if normalized.startswith(self.protected_prefixes):
            return ProtectionDecision(
                protected=True,
                reason="Kernel and boot packages cannot be removed through AppSweep.",
            )

        return ProtectionDecision(protected=False, reason="")
