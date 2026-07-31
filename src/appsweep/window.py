from concurrent.futures import ThreadPoolExecutor

from gi.repository import Adw, GLib, Gtk

from appsweep.apt_scanner import AptScanner
from appsweep.models import InstalledApplication


class AppSweepWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.set_title("AppSweep")
        self.set_default_size(960, 640)
        self.set_size_request(640, 480)

        self._scanner = AptScanner()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._applications: list[InstalledApplication] = []

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
        status_page = Adw.StatusPage()
        status_page.set_icon_name("user-trash-symbolic")
        status_page.set_title("AppSweep")
        status_page.set_description(
            "Safely remove applications and review associated data before deletion."
        )

        self._scan_button = Gtk.Button(label="Scan installed applications")
        self._scan_button.add_css_class("suggested-action")
        self._scan_button.add_css_class("pill")
        self._scan_button.set_halign(Gtk.Align.CENTER)
        self._scan_button.connect("clicked", self._on_scan_clicked)

        status_page.set_child(self._scan_button)
        return status_page

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
        self._applications = applications
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

        dialog = Adw.AlertDialog(
            heading="Unable to scan applications",
            body=message,
        )
        dialog.add_response("close", "Close")
        dialog.present(self)

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

        if application.icon_name:
            icon = Gtk.Image.new_from_icon_name(application.icon_name)
        else:
            icon = Gtk.Image.new_from_icon_name(
                "application-x-executable-symbolic"
            )

        icon.set_pixel_size(32)
        row.add_prefix(icon)
        row.application = application

        return row

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
            self._result_label.set_text(
                f"{visible_count} matching applications"
            )
        else:
            self._result_label.set_text(
                f"{visible_count} installed APT applications found"
            )

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

    def _on_close_request(self, _window: Adw.ApplicationWindow) -> bool:
        self._executor.shutdown(wait=False, cancel_futures=True)
        return False
