from concurrent.futures import ThreadPoolExecutor
from functools import partial

from gi.repository import Adw, GLib, Gtk

from appsweep.apt_scanner import AptScanner
from appsweep.backup_manager import (
    BackupManager,
    BackupResult,
    BackupVerification,
)
from appsweep.models import InstalledApplication
from appsweep.removal_analyzer import RemovalAnalysis, RemovalAnalyzer


class AppSweepWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.set_title("AppSweep")
        self.set_default_size(960, 640)
        self.set_size_request(640, 480)

        self._scanner = AptScanner()
        self._analyzer = RemovalAnalyzer()
        self._backup_manager = BackupManager()
        self._executor = ThreadPoolExecutor(max_workers=1)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self._status_page = self._build_status_page()
        self._applications_page = self._build_applications_page()

        self._stack.add_named(self._status_page, "welcome")
        self._stack.add_named(self._applications_page, "applications")

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(self._stack)

        self.set_content(toolbar_view)
        self.connect("close-request", self._on_close_request)

    def _build_status_page(self) -> Adw.StatusPage:
        page = Adw.StatusPage()
        page.set_icon_name("user-trash-symbolic")
        page.set_title("AppSweep")
        page.set_description(
            "Safely remove applications and review associated data before deletion."
        )

        self._scan_button = Gtk.Button(label="Scan installed applications")
        self._scan_button.add_css_class("suggested-action")
        self._scan_button.add_css_class("pill")
        self._scan_button.set_halign(Gtk.Align.CENTER)
        self._scan_button.connect("clicked", self._on_scan_clicked)

        page.set_child(self._scan_button)
        return page

    def _build_applications_page(self) -> Gtk.Box:
        page = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_margin_start(18)
        page.set_margin_end(18)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search installed applications")
        self._search_entry.connect("search-changed", self._on_search_changed)
        page.append(self._search_entry)

        self._result_label = Gtk.Label()
        self._result_label.set_halign(Gtk.Align.START)
        self._result_label.add_css_class("dim-label")
        page.append(self._result_label)

        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list_box.add_css_class("boxed-list")
        self._list_box.set_filter_func(self._filter_row)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_child(self._list_box)

        page.append(scrolled_window)
        return page

    def _on_scan_clicked(self, _button: Gtk.Button) -> None:
        self._scan_button.set_sensitive(False)
        self._scan_button.set_label("Scanning…")
        self._executor.submit(self._run_scan)

    def _run_scan(self) -> None:
        try:
            applications = self._scanner.scan()
        except Exception as error:
            GLib.idle_add(self._show_scan_error, str(error))
            return

        GLib.idle_add(self._show_scan_results, applications)

    def _show_scan_results(
        self,
        applications: list[InstalledApplication],
    ) -> bool:
        self._clear_list()

        for application in applications:
            self._list_box.append(self._create_application_row(application))

        self._update_result_count()
        self._stack.set_visible_child_name("applications")
        self._search_entry.grab_focus()

        return GLib.SOURCE_REMOVE

    def _show_scan_error(self, message: str) -> bool:
        self._scan_button.set_sensitive(True)
        self._scan_button.set_label("Scan installed applications")
        self._show_message("Unable to scan applications", message)
        return GLib.SOURCE_REMOVE

    def _create_application_row(
        self,
        application: InstalledApplication,
    ) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(application.display_name)
        row.set_subtitle(
            f"{application.package_name} · {application.version}"
        )

        icon_name = (
            application.icon_name
            or "application-x-executable-symbolic"
        )
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(32)
        row.add_prefix(icon)

        button = Gtk.Button()
        button.set_icon_name("go-next-symbolic")
        button.set_tooltip_text("Review application")
        button.set_valign(Gtk.Align.CENTER)
        button.add_css_class("flat")
        button.connect(
            "clicked",
            partial(self._on_review_clicked, application),
        )

        row.add_suffix(button)
        row.set_activatable_widget(button)
        row.application = application

        return row

    def _on_review_clicked(
        self,
        application: InstalledApplication,
        button: Gtk.Button,
    ) -> None:
        button.set_sensitive(False)
        button.set_icon_name("content-loading-symbolic")

        self._executor.submit(
            self._run_removal_analysis,
            application,
            button,
        )

    def _run_removal_analysis(
        self,
        application: InstalledApplication,
        button: Gtk.Button,
    ) -> None:
        try:
            analysis = self._analyzer.analyze(application)
        except Exception as error:
            GLib.idle_add(
                self._show_analysis_error,
                button,
                str(error),
            )
            return

        GLib.idle_add(
            self._show_removal_analysis,
            application,
            analysis,
            button,
        )

    def _show_removal_analysis(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
        button: Gtk.Button,
    ) -> bool:
        button.set_sensitive(True)
        button.set_icon_name("go-next-symbolic")

        sections = [
            application.summary or "No application description is available.",
            (
                f"Package\n{analysis.package_name}\n\n"
                f"Installed size\n{self._format_size(analysis.installed_size)}"
            ),
            (
                "Additional packages APT would remove\n"
                + (
                    "\n".join(analysis.additional_removals)
                    if analysis.additional_removals
                    else "None"
                )
            ),
            (
                "Installed packages referencing this package\n"
                + (
                    "\n".join(analysis.dependent_packages)
                    if analysis.dependent_packages
                    else "None detected"
                )
            ),
            (
                "Verified user-data paths\n"
                + (
                    "\n".join(str(path) for path in analysis.leftover_paths)
                    if analysis.leftover_paths
                    else "None detected"
                )
            ),
        ]

        dialog = Adw.AlertDialog(
            heading=f"Review {application.display_name}",
            body="\n\n".join(sections),
        )
        dialog.add_response("close", "Close")
        dialog.add_response("backup", "Create rollback backup")
        dialog.set_response_appearance(
            "backup",
            Adw.ResponseAppearance.SUGGESTED,
        )
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.connect(
            "response",
            partial(
                self._on_analysis_dialog_response,
                application,
                analysis,
            ),
        )
        dialog.present(self)

        return GLib.SOURCE_REMOVE

    def _show_analysis_error(
        self,
        button: Gtk.Button,
        message: str,
    ) -> bool:
        button.set_sensitive(True)
        button.set_icon_name("go-next-symbolic")
        self._show_message("Unable to analyze application", message)
        return GLib.SOURCE_REMOVE

    def _on_analysis_dialog_response(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "backup":
            return

        self._executor.submit(
            self._run_backup,
            application,
            analysis,
        )

    def _run_backup(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
    ) -> None:
        try:
            result = self._backup_manager.create(application, analysis)
            verification = self._backup_manager.verify(result)
        except Exception as error:
            GLib.idle_add(
                self._show_message,
                "Unable to create rollback backup",
                str(error),
            )
            return

        GLib.idle_add(
            self._show_backup_result,
            application,
            result,
            verification,
        )

    def _show_backup_result(
        self,
        application: InstalledApplication,
        result: BackupResult,
        verification: BackupVerification,
    ) -> bool:
        archive_text = (
            str(result.archive)
            if result.archive is not None
            else "No user-data archive was required."
        )

        heading = (
            f"Rollback backup verified for {application.display_name}"
            if verification.valid
            else f"Rollback backup failed verification for {application.display_name}"
        )

        dialog = Adw.AlertDialog(
            heading=heading,
            body=(
                f"Backup directory\n{result.directory}\n\n"
                f"User-data archive\n{archive_text}\n\n"
                f"Removal manifest\n{result.manifest}\n\n"
                f"Verification\n{verification.message}\n\n"
                "No package or user data has been removed."
            ),
        )
        dialog.add_response("close", "Close")

        if verification.valid:
            dialog.add_response("continue", "Continue")
            dialog.set_response_appearance(
                "continue",
                Adw.ResponseAppearance.DESTRUCTIVE,
            )
            dialog.connect(
                "response",
                partial(
                    self._on_verified_backup_response,
                    application,
                    result,
                ),
            )

        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.present(self)

        return GLib.SOURCE_REMOVE

    def _on_verified_backup_response(
        self,
        application: InstalledApplication,
        result: BackupResult,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "continue":
            return

        self._show_message(
            "Removal remains disabled",
            (
                f"The verified backup for {application.display_name} is stored at:\n\n"
                f"{result.directory}\n\n"
                "The next stage will add the privileged package-removal service. "
                "No system changes have been made."
            ),
        )

    def _show_message(self, heading: str, body: str) -> bool:
        dialog = Adw.AlertDialog(
            heading=heading,
            body=body,
        )
        dialog.add_response("close", "Close")
        dialog.present(self)
        return GLib.SOURCE_REMOVE

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self._list_box.invalidate_filter()
        self._update_result_count()

    def _update_result_count(self) -> None:
        visible_count = 0
        row = self._list_box.get_first_child()

        while row is not None:
            if row.get_visible():
                visible_count += 1
            row = row.get_next_sibling()

        if self._search_entry.get_text().strip():
            text = f"{visible_count} matching applications"
        else:
            text = f"{visible_count} installed APT applications found"

        self._result_label.set_text(text)

    def _filter_row(self, row: Gtk.ListBoxRow) -> bool:
        query = self._search_entry.get_text().strip().casefold()

        if not query:
            return True

        application = row.application
        searchable_text = " ".join(
            (
                application.package_name,
                application.display_name,
                application.summary,
            )
        ).casefold()

        return query in searchable_text

    def _clear_list(self) -> None:
        child = self._list_box.get_first_child()

        while child is not None:
            next_child = child.get_next_sibling()
            self._list_box.remove(child)
            child = next_child

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)

        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(value)} {unit}"

                return f"{value:.1f} {unit}"

            value /= 1024

        return f"{size} B"

    def _on_close_request(
        self,
        _window: Adw.ApplicationWindow,
    ) -> bool:
        self._executor.shutdown(
            wait=False,
            cancel_futures=True,
        )
        return False
