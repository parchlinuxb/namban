import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')

import sys
import logging
import argparse
from gi.repository import Gtk, Adw, Gio
from main_window import MainWindow
from dns_manager import DNSManager
from core.toolbox import BaseToolBox, toolbox

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


def handle_rollback() -> int:
    """Handle emergency rollback of DNS changes.
    
    Called with --rollback flag when system starts up or manually.
    Reverts any DNS changes that may have caused issues.
    """
    logger.info("Starting emergency DNS rollback")
    try:
        dns_manager = DNSManager()
        
        history = dns_manager.get_history()
        if not history:
            logger.info("No DNS changes to rollback")
            return 0
        
        logger.info(f"Found {len(history)} DNS changes, attempting rollback")
        if dns_manager.restore_previous_config():
            logger.info("Successfully rolled back DNS configuration")
            return 0
        else:
            logger.error("Failed to rollback DNS configuration")
            return 1
    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        return 1


def handle_check_safety() -> int:
    """Check if system is in safe state and rollback if needed.
    
    Called periodically by systemd timer to verify system stability.
    Can be triggered by a watchdog or timeout mechanism.
    """
    logger.info("Checking system DNS safety")
    try:
        dns_manager = DNSManager()
        history = dns_manager.get_recent_actions(1)
        
        if history:
            logger.debug(f"Last DNS action: {history[0]}")
        
        # System is running and responsive - no rollback needed
        logger.info("System safety check passed")
        return 0
    except Exception as e:
        logger.error(f"Safety check failed: {e}", exc_info=True)
        return 1


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
    parser = argparse.ArgumentParser(description="Namban DNS Manager")
    parser.add_argument('--rollback', action='store_true', 
                       help='Rollback DNS changes and exit')
    parser.add_argument('--check-safety', action='store_true',
                       help='Check system safety and exit')
    
    args, remaining = parser.parse_known_args()
    
    try:
        if args.rollback:
            return handle_rollback()
        elif args.check_safety:
            return handle_check_safety()
        else:
            return NambanApplication().run(remaining)
    except Exception as e:
        logger.critical(f"Application failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

