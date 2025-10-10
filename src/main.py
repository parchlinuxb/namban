import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')

import sys
import logging
from gi.repository import Gtk, Adw, Gio
from main_window import MainWindow

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

class NambanApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.parchlinux.namban", flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.get_active_window() or MainWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)

        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self._on_settings)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Ctrl>q"])

    def _on_settings(self, _, __):
        win = self.get_active_window()
        if win:
            win._show_settings_sheet()

    def _on_about(self, _, __):
        Adw.AboutWindow(
            transient_for=self.get_active_window(), application_name="Namban DNS Manager",
            application_icon="com.parchlinux.namban", developer_name="Parch Linux Team & Contributors",
            version="2.0.0", developers=["Meshya", "Sohrab Behdani"],
            copyright="© 2024 Parch Linux Team", license_type=Gtk.License.GPL_3_0_ONLY,
            website="https://github.com/parchlinuxb/namban",
            issue_url="https://github.com/parchlinuxb/namban/issues"
        ).present()

def main():
    try:
        return NambanApplication().run(sys.argv)
    except Exception as e:
        logging.critical(f"Application failed to start: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
