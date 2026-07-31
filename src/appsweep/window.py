from gi.repository import Adw, Gtk


class AppSweepWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.set_title("AppSweep")
        self.set_default_size(960, 640)
        self.set_size_request(640, 480)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        status_page = Adw.StatusPage()
        status_page.set_icon_name("user-trash-symbolic")
        status_page.set_title("AppSweep")
        status_page.set_description(
            "Safely remove applications and review associated data before deletion."
        )

        action_button = Gtk.Button(label="Scan installed applications")
        action_button.add_css_class("suggested-action")
        action_button.add_css_class("pill")
        action_button.set_halign(Gtk.Align.CENTER)
        action_button.set_sensitive(False)

        status_page.set_child(action_button)
        toolbar_view.set_content(status_page)

        self.set_content(toolbar_view)
