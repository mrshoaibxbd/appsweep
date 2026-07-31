import sys

from gi.repository import Adw, Gio

from appsweep.window import AppSweepWindow

APP_ID = "tech.shoaib.AppSweep"


class AppSweepApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, application: Adw.Application) -> None:
        window = self.props.active_window

        if window is None:
            window = AppSweepWindow(application=application)

        window.present()


def main() -> int:
    application = AppSweepApplication()
    return application.run(sys.argv)
