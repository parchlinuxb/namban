import gi
from typing import List, Optional
from gi.repository import Gtk, Adw, GLib, Gio
from models import DNSProfile
from dns_manager import DNSManager
from profile_manager import ProfileManager
from ui_components import ProfileRow, ProfileEditSheet, SettingsPage

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dns_manager = DNSManager()
        self.profile_manager = ProfileManager()
        self.profile_rows: List[ProfileRow] = []
        self.active_profile: Optional[DNSProfile] = None

        self.set_title("Namban DNS Manager")
        self.set_default_size(450, 600)
        self._build_ui()
        self._load_profiles()
        self._update_status()
        GLib.timeout_add_seconds(10, self._update_status)

    def _build_ui(self):
        self.bottom_sheet = Adw.BottomSheet()
        self.toast_overlay = Adw.ToastOverlay(child=self.bottom_sheet)
        self.set_content(self.toast_overlay)
        self.bottom_sheet.set_content(self._build_main_content())

    def _build_main_content(self):
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Namban DNS Manager"))
        add_button = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add New Profile")
        add_button.connect('clicked', self._on_add_profile)
        header.pack_end(add_button)
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=Gio.Menu.new())
        menu_button.get_menu_model().append("Settings", "app.settings")
        menu_button.get_menu_model().append("About", "app.about")
        menu_button.get_menu_model().append("Quit", "app.quit")
        header.pack_end(menu_button)
        toolbar_view.add_top_bar(header)

        status_group = Adw.PreferencesGroup(title="Current Status")
        self.status_row = Adw.ActionRow(title="DNS Status", subtitle="Loading...")
        status_group.add(self.status_row)

        self.profiles_group = Adw.PreferencesGroup(title="DNS Profiles", description="Select a profile to apply")
        page = Adw.PreferencesPage()
        page.add(status_group)
        page.add(self.profiles_group)
        toolbar_view.set_content(Gtk.ScrolledWindow(child=page, hscrollbar_policy='never'))
        return toolbar_view

    def _load_profiles(self):
        for row in self.profile_rows:
            self.profiles_group.remove(row)
        self.profile_rows.clear()
        for profile in self.profile_manager.profiles:
            row = ProfileRow(profile,
                             on_activate=self._on_profile_activate,
                             on_edit=self._on_profile_edit,
                             on_delete=self._on_profile_delete)
            self.profiles_group.add(row)
            self.profile_rows.append(row)

    def _update_status(self):
        current_dns = self.dns_manager.get_current_dns()
        self.status_row.set_subtitle(", ".join(current_dns) or "System default")
        return True

    def _on_profile_activate(self, profile: DNSProfile, state: bool):
        if state:
            if self.dns_manager.apply_profile(profile):
                self.toast_overlay.add_toast(Adw.Toast.new(f"Applied: {profile.name}"))
                self.active_profile = profile
                for row in self.profile_rows:
                    if row.profile != profile:
                        row.set_active(False)
            else:
                self.toast_overlay.add_toast(Adw.Toast.new("Failed to apply profile"))
                for row in self.profile_rows:
                    if row.profile == profile:
                        row.set_active(False)
                        break
        elif self.active_profile == profile:
            if self.dns_manager.restore_previous_config():
                self.toast_overlay.add_toast(Adw.Toast.new("Restored default DNS"))
                self.active_profile = None
            else:
                self.toast_overlay.add_toast(Adw.Toast.new("Failed to restore settings"))
                for row in self.profile_rows:
                    if row.profile == profile:
                        row.set_active(True)
                        break
        self._update_status()

    def _show_profile_sheet(self, old_profile: Optional[DNSProfile] = None):
        sheet_content = ProfileEditSheet(profile=old_profile)
        toolbar_view = Adw.ToolbarView()
        title = "Edit Profile" if old_profile else "Add New Profile"
        header = Adw.HeaderBar(title_widget=Adw.WindowTitle(title=title))
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(sheet_content)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect('clicked', lambda _: self.bottom_sheet.set_open(False))
        header.pack_start(cancel_button)

        save_button = Gtk.Button(label="Save", css_classes=["suggested-action"])
        header.pack_end(save_button)

        def on_save(_):
            new_profile = sheet_content.get_profile()
            if new_profile:
                if old_profile:
                    self._on_profile_updated(old_profile, new_profile)
                else:
                    self._on_profile_added(new_profile)
                self.bottom_sheet.set_open(False)
            else:
                self.toast_overlay.add_toast(Adw.Toast.new("Profile Name and Primary DNS are required."))

        save_button.connect('clicked', on_save)
        self.bottom_sheet.set_sheet(toolbar_view)
        self.bottom_sheet.set_open(True)

    def _show_settings_sheet(self):
        settings_content = SettingsPage()
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Settings"))
        toolbar_view.add_top_bar(header)

        clamp = Adw.Clamp(maximum_size=400, tightening_threshold=300)
        clamp.set_child(settings_content)
        toolbar_view.set_content(clamp)

        close_button = Gtk.Button(label="Done")
        close_button.connect('clicked', lambda _: self.bottom_sheet.set_open(False))
        header.pack_end(close_button)

        self.bottom_sheet.set_sheet(toolbar_view)
        self.bottom_sheet.set_open(True)

    def _on_add_profile(self, _):
        self._show_profile_sheet()

    def _on_profile_edit(self, profile: DNSProfile):
        self._show_profile_sheet(old_profile=profile)

    def _on_profile_delete(self, profile: DNSProfile):
        self.profile_manager.remove_profile(profile)
        self._load_profiles()
        self.toast_overlay.add_toast(Adw.Toast.new(f"Profile '{profile.name}' removed"))
        if self.active_profile == profile:
            self.dns_manager.restore_previous_config()
            self.active_profile = None
            self._update_status()

    def _on_profile_added(self, profile: DNSProfile):
        self.profile_manager.add_profile(profile)
        self._load_profiles()
        self.toast_overlay.add_toast(Adw.Toast.new(f"Profile '{profile.name}' created"))

    def _on_profile_updated(self, old_profile: DNSProfile, new_profile: DNSProfile):
        self.profile_manager.update_profile(old_profile, new_profile)
        self._load_profiles()
        self.toast_overlay.add_toast(Adw.Toast.new(f"Profile '{new_profile.name}' updated"))
