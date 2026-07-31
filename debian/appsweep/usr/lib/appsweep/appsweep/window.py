from concurrent.futures import ThreadPoolExecutor
from functools import partial

from gi.repository import Adw, GLib, Gtk

from appsweep.application_scanner import ApplicationScanner
from appsweep.backup_manager import (
    BackupManager,
    BackupResult,
    BackupVerification,
)
from appsweep.flatpak_removal_analyzer import (
    FlatpakRemovalAnalysis,
    FlatpakRemovalAnalyzer,
)
from appsweep.models import InstalledApplication, PackageBackend
from appsweep.removal_analyzer import RemovalAnalysis, RemovalAnalyzer
from appsweep.snap_removal_analyzer import SnapRemovalAnalysis, SnapRemovalAnalyzer
from appsweep.removal_service import (
    LeftoverRemovalResult,
    PackageRemovalResult,
    RemovalService,
)


class AppSweepWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.set_title("AppSweep")
        self.set_default_size(960, 640)
        self.set_size_request(640, 480)

        self._scanner = ApplicationScanner()
        self._analyzer = RemovalAnalyzer()
        self._snap_analyzer = SnapRemovalAnalyzer()
        self._flatpak_analyzer = FlatpakRemovalAnalyzer()
        self._backup_manager = BackupManager()
        self._removal_service = RemovalService()
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
            f"{application.backend.value.upper()} · "
            f"{application.package_name} · {application.version}"
        )

        icon_name = application.icon_name or "application-x-executable-symbolic"
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
        if application.backend is PackageBackend.SNAP:
            analysis = self._snap_analyzer.analyze(application)
            self._show_snap_removal_analysis(application, analysis)
            return

        if application.backend is PackageBackend.FLATPAK:
            analysis = self._flatpak_analyzer.analyze(application)
            self._show_flatpak_review(application, analysis)
            return

        button.set_sensitive(False)
        button.set_icon_name("content-loading-symbolic")

        self._executor.submit(
            self._run_removal_analysis,
            application,
            button,
        )

    def _show_flatpak_review(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
    ) -> None:
        scope = analysis.scope.title() if analysis.scope else "Unknown"
        paths = (
            "\n".join(str(path) for path in analysis.user_data_paths)
            if analysis.user_data_paths
            else "None detected"
        )

        dialog = Adw.AlertDialog(
            heading=f"Review {application.display_name}",
            body=(
                f"{application.summary or 'No application description is available.'}\n\n"
                f"Package type\nFlatpak\n\n"
                f"Application ID\n{analysis.application_id}\n\n"
                f"Version\n{application.version or 'Unknown'}\n\n"
                f"Installation scope\n{scope}\n\n"
                f"User-data paths\n{paths}"
            ),
        )
        dialog.add_response("close", "Close")
        dialog.add_response("backup", "Remove with backup")
        dialog.add_response("permanent", "Remove without backup")
        dialog.set_response_appearance(
            "backup",
            Adw.ResponseAppearance.SUGGESTED,
        )
        dialog.set_response_appearance(
            "permanent",
            Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.connect(
            "response",
            partial(
                self._on_flatpak_review_response,
                application,
                analysis,
            ),
        )
        dialog.present(self)

    def _on_flatpak_review_response(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response == "backup":
            self._executor.submit(
                self._run_flatpak_backup,
                application,
                analysis,
            )
        elif response == "permanent":
            self._show_flatpak_permanent_warning(
                application,
                analysis,
            )

    def _run_flatpak_backup(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
    ) -> None:
        apt_style_analysis = RemovalAnalysis(
            package_name=analysis.application_id,
            installed_size=0,
            additional_removals=(),
            dependent_packages=(),
            leftover_paths=analysis.user_data_paths,
        )

        try:
            result = self._backup_manager.create(
                application,
                apt_style_analysis,
            )
            verification = self._backup_manager.verify(result)
        except Exception as error:
            GLib.idle_add(
                self._show_message,
                "Unable to create rollback backup",
                str(error),
            )
            return

        GLib.idle_add(
            self._show_flatpak_backup_result,
            application,
            analysis,
            result,
            verification,
        )

    def _show_flatpak_backup_result(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
        backup: BackupResult,
        verification: BackupVerification,
    ) -> bool:
        heading = (
            f"Rollback backup verified for {application.display_name}"
            if verification.valid
            else f"Backup verification failed for {application.display_name}"
        )

        dialog = Adw.AlertDialog(
            heading=heading,
            body=(
                f"Backup directory\n{backup.directory}\n\n"
                f"Verification\n{verification.message}\n\n"
                "The backup will remain after removal."
            ),
        )
        dialog.add_response("close", "Close")

        if verification.valid:
            dialog.add_response("remove", "Remove application")
            dialog.set_response_appearance(
                "remove",
                Adw.ResponseAppearance.DESTRUCTIVE,
            )
            dialog.connect(
                "response",
                partial(
                    self._on_flatpak_backup_response,
                    application,
                    analysis,
                    backup,
                ),
            )

        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.present(self)

        return GLib.SOURCE_REMOVE

    def _on_flatpak_backup_response(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
        backup: BackupResult,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "remove":
            return

        self._executor.submit(
            self._run_flatpak_removal,
            application,
            analysis,
            backup,
        )

    def _show_flatpak_permanent_warning(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
    ) -> None:
        paths = (
            "\n".join(str(path) for path in analysis.user_data_paths)
            if analysis.user_data_paths
            else "No user-data directory was detected."
        )

        dialog = Adw.AlertDialog(
            heading=f"Permanently remove {application.display_name}?",
            body=(
                "No rollback backup will be created.\n\n"
                f"The Flatpak application will be uninstalled and these "
                f"verified paths will be deleted:\n\n{paths}"
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove permanently")
        dialog.set_response_appearance(
            "remove",
            Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response",
            partial(
                self._on_flatpak_permanent_response,
                application,
                analysis,
            ),
        )
        dialog.present(self)

    def _on_flatpak_permanent_response(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "remove":
            return

        self._executor.submit(
            self._run_flatpak_removal,
            application,
            analysis,
            None,
        )

    def _run_flatpak_removal(
        self,
        application: InstalledApplication,
        analysis: FlatpakRemovalAnalysis,
        backup: BackupResult | None,
    ) -> None:
        result = self._removal_service.remove_flatpak(
            analysis.application_id,
            analysis.scope,
        )

        if not result.success:
            GLib.idle_add(
                self._show_removal_failure,
                application,
                result,
            )
            return

        leftovers = self._removal_service.remove_leftovers(analysis.user_data_paths)
        self._removal_service.reset_flatpak_permissions(analysis.application_id)

        GLib.idle_add(
            self._show_flatpak_removal_success,
            application,
            result,
            leftovers,
            backup,
        )

    def _show_flatpak_removal_success(
        self,
        application: InstalledApplication,
        result: PackageRemovalResult,
        leftovers: LeftoverRemovalResult,
        backup: BackupResult | None,
    ) -> bool:
        sections = [result.message]

        if leftovers.removed:
            sections.append(
                "Deleted user-data paths\n" + "\n".join(str(path) for path in leftovers.removed)
            )
        else:
            sections.append("Deleted user-data paths\nNone")

        if leftovers.failed:
            sections.append(
                "Paths that could not be deleted\n"
                + "\n".join(f"{path}: {message}" for path, message in leftovers.failed)
            )

        sections.append(
            f"Rollback backup retained at\n{backup.directory}"
            if backup is not None
            else "No rollback backup was created."
        )

        dialog = Adw.AlertDialog(
            heading=f"{application.display_name} removed",
            body="\n\n".join(sections),
        )
        dialog.add_response("close", "Close")
        dialog.connect("response", self._on_removal_result_closed)
        dialog.present(self)

        return GLib.SOURCE_REMOVE

    def _show_snap_removal_analysis(
        self,
        application: InstalledApplication,
        analysis: SnapRemovalAnalysis,
    ) -> None:
        paths = (
            "\n".join(str(path) for path in analysis.user_data_paths)
            if analysis.user_data_paths
            else "None detected"
        )

        sections = [
            application.summary or "No application description is available.",
            (
                f"Package type\nSnap\n\n"
                f"Package\n{analysis.snap_name}\n\n"
                f"Version\n{application.version}"
            ),
            f"User-data paths\n{paths}",
        ]

        if analysis.protected:
            sections.append(
                "Protected Snap component\n"
                + analysis.protection_reason
                + "\n\nAppSweep will not allow this Snap to be removed."
            )

        dialog = Adw.AlertDialog(
            heading=f"Review {application.display_name}",
            body="\n\n".join(sections),
        )
        dialog.add_response("close", "Close")

        if not analysis.protected:
            dialog.add_response("backup", "Remove with Snap backup")
            dialog.add_response("permanent", "Remove without backup")
            dialog.set_response_appearance(
                "backup",
                Adw.ResponseAppearance.SUGGESTED,
            )
            dialog.set_response_appearance(
                "permanent",
                Adw.ResponseAppearance.DESTRUCTIVE,
            )
            dialog.connect(
                "response",
                partial(
                    self._on_snap_analysis_response,
                    application,
                    analysis,
                ),
            )

        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.present(self)

    def _on_snap_analysis_response(
        self,
        application: InstalledApplication,
        analysis: SnapRemovalAnalysis,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response == "backup":
            self._executor.submit(
                self._run_snap_removal,
                application,
                analysis,
                True,
            )
        elif response == "permanent":
            self._show_snap_permanent_warning(application, analysis)

    def _show_snap_permanent_warning(
        self,
        application: InstalledApplication,
        analysis: SnapRemovalAnalysis,
    ) -> None:
        dialog = Adw.AlertDialog(
            heading=f"Permanently remove {application.display_name}?",
            body=(
                "Snap will remove the application and its current user, system, "
                "and configuration data without creating a new rollback snapshot.\n\n"
                "Older Snap snapshots, if any exist, are not deleted by this action."
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove permanently")
        dialog.set_response_appearance(
            "remove",
            Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response",
            partial(
                self._on_snap_permanent_warning_response,
                application,
                analysis,
            ),
        )
        dialog.present(self)

    def _on_snap_permanent_warning_response(
        self,
        application: InstalledApplication,
        analysis: SnapRemovalAnalysis,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "remove":
            return

        self._executor.submit(
            self._run_snap_removal,
            application,
            analysis,
            False,
        )

    def _run_snap_removal(
        self,
        application: InstalledApplication,
        analysis: SnapRemovalAnalysis,
        create_snapshot: bool,
    ) -> None:
        if analysis.protected:
            GLib.idle_add(
                self._show_message,
                "Protected Snap component",
                analysis.protection_reason,
            )
            return

        result = self._removal_service.remove_snap(
            analysis.snap_name,
            create_snapshot,
        )

        if not result.success:
            GLib.idle_add(
                self._show_removal_failure,
                application,
                result,
            )
            return

        GLib.idle_add(
            self._show_snap_removal_success,
            application,
            result,
            create_snapshot,
        )

    def _show_snap_removal_success(
        self,
        application: InstalledApplication,
        result: PackageRemovalResult,
        created_snapshot: bool,
    ) -> bool:
        backup_text = (
            "Snap created and retained a rollback snapshot."
            if created_snapshot
            else "No new rollback snapshot was created."
        )

        dialog = Adw.AlertDialog(
            heading=f"{application.display_name} removed",
            body=f"{result.message}\n\n{backup_text}",
        )
        dialog.add_response("close", "Close")
        dialog.connect("response", self._on_removal_result_closed)
        dialog.present(self)

        return GLib.SOURCE_REMOVE

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

        if analysis.protected:
            sections.append(
                "Protected application\n"
                + analysis.protection_reason
                + "\n\nAppSweep will not allow this package to be removed."
            )

        dialog = Adw.AlertDialog(
            heading=f"Review {application.display_name}",
            body="\n\n".join(sections),
        )
        dialog.add_response("close", "Close")

        if not analysis.protected:
            dialog.add_response("backup", "Remove with backup")
            dialog.add_response("permanent", "Remove without backup")
            dialog.set_response_appearance(
                "backup",
                Adw.ResponseAppearance.SUGGESTED,
            )
            dialog.set_response_appearance(
                "permanent",
                Adw.ResponseAppearance.DESTRUCTIVE,
            )
            dialog.connect(
                "response",
                partial(
                    self._on_analysis_dialog_response,
                    application,
                    analysis,
                ),
            )

        dialog.set_default_response("close")
        dialog.set_close_response("close")
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
        if response == "backup":
            self._executor.submit(
                self._run_backup,
                application,
                analysis,
            )
        elif response == "permanent":
            self._show_permanent_removal_warning(
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
            analysis,
            result,
            verification,
        )

    def _show_backup_result(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
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
            else f"Backup verification failed for {application.display_name}"
        )

        dialog = Adw.AlertDialog(
            heading=heading,
            body=(
                f"Backup directory\n{result.directory}\n\n"
                f"User-data archive\n{archive_text}\n\n"
                f"Removal manifest\n{result.manifest}\n\n"
                f"Verification\n{verification.message}\n\n"
                "The backup will remain stored after removal."
            ),
        )
        dialog.add_response("close", "Close")

        if verification.valid:
            dialog.add_response("remove", "Remove application")
            dialog.set_response_appearance(
                "remove",
                Adw.ResponseAppearance.DESTRUCTIVE,
            )
            dialog.connect(
                "response",
                partial(
                    self._on_backup_dialog_response,
                    application,
                    analysis,
                    result,
                ),
            )

        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.present(self)

        return GLib.SOURCE_REMOVE

    def _on_backup_dialog_response(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
        backup: BackupResult,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "remove":
            return

        self._executor.submit(
            self._run_removal,
            application,
            analysis,
            backup,
        )

    def _show_permanent_removal_warning(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
    ) -> None:
        leftover_text = (
            "\n".join(str(path) for path in analysis.leftover_paths)
            if analysis.leftover_paths
            else "No verified user-data paths were detected."
        )

        dialog = Adw.AlertDialog(
            heading=f"Permanently remove {application.display_name}?",
            body=(
                "No rollback backup will be created.\n\n"
                "The APT package will be purged and these verified user-data "
                f"paths will be permanently deleted:\n\n{leftover_text}\n\n"
                "This action cannot be undone by AppSweep."
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove permanently")
        dialog.set_response_appearance(
            "remove",
            Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response",
            partial(
                self._on_permanent_warning_response,
                application,
                analysis,
            ),
        )
        dialog.present(self)

    def _on_permanent_warning_response(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "remove":
            return

        self._show_final_permanent_confirmation(
            application,
            analysis,
        )

    def _show_final_permanent_confirmation(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
    ) -> None:
        dialog = Adw.AlertDialog(
            heading="Final confirmation",
            body=(
                f"Remove {application.display_name} and permanently delete "
                "its verified user data without creating a backup?"
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("confirm", "Yes, remove it")
        dialog.set_response_appearance(
            "confirm",
            Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response",
            partial(
                self._on_final_confirmation_response,
                application,
                analysis,
            ),
        )
        dialog.present(self)

    def _on_final_confirmation_response(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
        _dialog: Adw.AlertDialog,
        response: str,
    ) -> None:
        if response != "confirm":
            return

        self._executor.submit(
            self._run_removal,
            application,
            analysis,
            None,
        )

    def _run_removal(
        self,
        application: InstalledApplication,
        analysis: RemovalAnalysis,
        backup: BackupResult | None,
    ) -> None:
        if analysis.protected:
            GLib.idle_add(
                self._show_message,
                "Protected application",
                analysis.protection_reason,
            )
            return

        package_result = self._removal_service.purge_package(application.package_name)

        if not package_result.success:
            GLib.idle_add(
                self._show_removal_failure,
                application,
                package_result,
            )
            return

        leftover_result = self._removal_service.remove_leftovers(analysis.leftover_paths)

        GLib.idle_add(
            self._show_removal_success,
            application,
            package_result,
            leftover_result,
            backup,
        )

    def _show_removal_failure(
        self,
        application: InstalledApplication,
        result: PackageRemovalResult,
    ) -> bool:
        details = result.message

        if result.stderr.strip():
            details += f"\n\nDetails\n{result.stderr.strip()}"

        self._show_message(
            f"Unable to remove {application.display_name}",
            details,
        )

        return GLib.SOURCE_REMOVE

    def _show_removal_success(
        self,
        application: InstalledApplication,
        package_result: PackageRemovalResult,
        leftover_result: LeftoverRemovalResult,
        backup: BackupResult | None,
    ) -> bool:
        sections = [package_result.message]

        if leftover_result.removed:
            sections.append(
                "Deleted user-data paths\n"
                + "\n".join(str(path) for path in leftover_result.removed)
            )
        else:
            sections.append("Deleted user-data paths\nNone")

        if leftover_result.failed:
            sections.append(
                "Paths that could not be deleted\n"
                + "\n".join(f"{path}: {message}" for path, message in leftover_result.failed)
            )

        if backup is not None:
            sections.append(f"Rollback backup retained at\n{backup.directory}")
        else:
            sections.append("No rollback backup was created.")

        dialog = Adw.AlertDialog(
            heading=f"{application.display_name} removed",
            body="\n\n".join(sections),
        )
        dialog.add_response("close", "Close")
        dialog.connect("response", self._on_removal_result_closed)
        dialog.present(self)

        return GLib.SOURCE_REMOVE

    def _on_removal_result_closed(
        self,
        _dialog: Adw.AlertDialog,
        _response: str,
    ) -> None:
        self._executor.submit(self._run_scan)

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
            text = f"{visible_count} installed applications found"

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
