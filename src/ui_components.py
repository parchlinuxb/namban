import gi
from typing import Optional, Callable
from gi.repository import Gtk, Adw
from models import DNSProfile, DNSServer, DNSType
from proxy_manager import ProxyManager

class SettingsPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        self.proxy_manager = ProxyManager()
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        self.set_title("Settings")
        group = Adw.PreferencesGroup(title="Legacy Proxy Configuration", description="Reads system-wide proxy settings. This feature is read-only.")
        self.add(group)
        self.host_row = Adw.EntryRow(title="Proxy Host", editable=False)
        self.port_row = Adw.EntryRow(title="Proxy Port", editable=False)
        group.add(self.host_row)
        group.add(self.port_row)

    def _load_settings(self):
        settings = self.proxy_manager.get_proxy_settings()
        if settings['enabled']:
            self.host_row.set_text(settings['host'])
            self.port_row.set_text(str(settings['port']))
        else:
            self.host_row.set_text("Proxy is disabled or not configured")
            self.port_row.set_text("")

class ProfileRow(Adw.ActionRow):
    def __init__(self, profile: DNSProfile, on_activate: Callable, on_edit: Callable, on_delete: Callable):
        super().__init__()
        self.profile = profile
        self.set_title(profile.name)
        self.set_subtitle(" • ".join([s.primary + (f", {s.secondary}" if s.secondary else "") for s in profile.servers]))

        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.switch.connect('state-set', lambda _, state: on_activate(self.profile, state))
        self.add_suffix(self.switch)

        edit_button = Gtk.Button(icon_name="edit-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"])
        edit_button.connect('clicked', lambda _: on_edit(self.profile))
        self.add_suffix(edit_button)

        delete_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat", "error"])
        delete_button.connect('clicked', lambda _: on_delete(self.profile))
        self.add_suffix(delete_button)

    def set_active(self, active: bool):
        with self.switch.freeze_notify():
            self.switch.set_active(active)

class ProfileEditSheet(Gtk.Box):
    def __init__(self, profile: Optional[DNSProfile] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.profile = profile
        self._build_form()
        if profile:
            self._populate_fields()

    def _build_form(self):
        clamp = Adw.Clamp(maximum_size=400, tightening_threshold=300)
        self.append(clamp)
        page = Adw.PreferencesPage(margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        clamp.set_child(page)

        group = Adw.PreferencesGroup()
        page.add(group)
        self.name_row = Adw.EntryRow(title="Profile Name")
        self.primary_row = Adw.EntryRow(title="Primary DNS")
        self.secondary_row = Adw.EntryRow(title="Secondary DNS (Optional)")
        self.description_row = Adw.EntryRow(title="Description (Optional)")
        type_model = Gtk.StringList.new(["Standard DNS", "DNS over HTTPS (DoH)", "DNS over TLS (DoT)"])
        self.type_row = Adw.ComboRow(title="DNS Type", model=type_model)
        self.type_row.connect('notify::selected', lambda *_: self.doh_row.set_visible(self.type_row.get_selected() == 1))
        self.doh_row = Adw.EntryRow(title="DoH URL", visible=False)
        for row in [self.name_row, self.type_row, self.primary_row, self.secondary_row, self.doh_row, self.description_row]:
            group.add(row)

    def _populate_fields(self):
        self.name_row.set_text(self.profile.name)
        if self.profile.servers:
            s = self.profile.servers[0]
            self.primary_row.set_text(s.primary)
            self.secondary_row.set_text(s.secondary or "")
            self.description_row.set_text(s.description or "")
            self.doh_row.set_text(s.doh_url or "")
            self.type_row.set_selected({DNSType.STANDARD: 0, DNSType.DOH: 1, DNSType.DOT: 2}.get(s.dns_type, 0))

    def get_profile(self) -> Optional[DNSProfile]:
        name = self.name_row.get_text().strip()
        primary = self.primary_row.get_text().strip()
        if not name or not primary:
            return None
        dns_type = [DNSType.STANDARD, DNSType.DOH, DNSType.DOT][self.type_row.get_selected()]
        server = DNSServer(name=name, primary=primary,
                            secondary=self.secondary_row.get_text().strip() or None,
                            description=self.description_row.get_text().strip() or None,
                            dns_type=dns_type,
                            doh_url=self.doh_row.get_text().strip() if dns_type == DNSType.DOH else None)
        return DNSProfile(name, [server])
