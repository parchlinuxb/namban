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

KNOWN_DOT_PROVIDERS = {
    "cloudflare-dns.com": "1.1.1.1",
    "one.one.one.one": "1.1.1.1",
    "dns.google": "8.8.8.8",
    "dns.quad9.net": "9.9.9.9",
    "dns.adguard-dns.com": "94.140.14.14",
    "base.dns.mullvad.net": "194.242.2.2",
    "extended.dns.mullvad.net": "194.242.2.3",
    "dns.nextdns.io": "45.90.28.0",
}

KNOWN_IP_TO_DOT = {
    "1.1.1.1": "cloudflare-dns.com",
    "1.0.0.1": "cloudflare-dns.com",
    "8.8.8.8": "dns.google",
    "8.8.4.4": "dns.google",
    "9.9.9.9": "dns.quad9.net",
    "149.112.112.112": "dns.quad9.net",
    "94.140.14.14": "dns.adguard-dns.com",
    "94.140.15.15": "dns.adguard-dns.com",
}

class ProfileRow(Adw.ActionRow):
    def __init__(self, profile: DNSProfile, on_activate: Callable, on_edit: Callable, on_delete: Callable):
        super().__init__()
        self.profile = profile
        self.on_activate = on_activate
        self._is_updating = False
        self.set_title(profile.name)
        
        subtitle_parts = []
        for s in profile.servers:
            if s.dns_type == DNSType.DOH and s.doh_url:
                subtitle_parts.append(s.doh_url)
            elif s.dns_type == DNSType.DOT:
                entry = f"{s.primary}#{s.tls_hostname}" if s.tls_hostname else s.primary
                if s.secondary:
                    sec_entry = f"{s.secondary}#{s.tls_hostname}" if s.tls_hostname else s.secondary
                    entry += f", {sec_entry}"
                subtitle_parts.append(entry)
            else:
                entry = s.primary + (f", {s.secondary}" if s.secondary else "")
                subtitle_parts.append(entry)
        self.set_subtitle(" • ".join(subtitle_parts))

        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.switch.connect('state-set', self._on_switch_state_set)
        self.add_suffix(self.switch)

        edit_button = Gtk.Button(icon_name="edit-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"])
        edit_button.connect('clicked', lambda _: on_edit(self.profile))
        self.add_suffix(edit_button)

        delete_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat", "error"])
        delete_button.connect('clicked', lambda _: on_delete(self.profile))
        self.add_suffix(delete_button)

    def _on_switch_state_set(self, switch, state):
        if self._is_updating:
            return False
        self.on_activate(self.profile, state)
        return False

    def set_active(self, active: bool):
        self._is_updating = True
        self.switch.set_active(active)
        self._is_updating = False

class ProfileEditSheet(Gtk.Box):
    def __init__(self, profile: Optional[DNSProfile] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.profile = profile
        self._build_form()
        if profile:
            self._populate_fields()
        else:
            self._update_field_visibility(0)

    def _build_form(self):
        clamp = Adw.Clamp(maximum_size=400, tightening_threshold=300)
        self.append(clamp)
        page = Adw.PreferencesPage(margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        clamp.set_child(page)

        group = Adw.PreferencesGroup()
        page.add(group)
        self.name_row = Adw.EntryRow(title="Profile Name")
        
        type_model = Gtk.StringList.new(["Standard DNS", "DNS over TLS (DoT)"])
        self.type_row = Adw.ComboRow(title="DNS Type", model=type_model)
        self.type_row.connect('notify::selected', self._on_type_changed)
        
        # Standard DNS rows
        self.primary_row = Adw.EntryRow(title="Primary DNS (IP)")
        self.secondary_row = Adw.EntryRow(title="Secondary DNS (IP, Optional)")

        # DoT rows
        self.dot_server_row = Adw.EntryRow(title="DoT Server (e.g. 1.1.1.1#cloudflare-dns.com or dns.google)", visible=False)
        self.dot_secondary_row = Adw.EntryRow(title="Secondary DoT Server (Optional)", visible=False)

        self.description_row = Adw.EntryRow(title="Description (Optional)")

        for row in [self.name_row, self.type_row, self.primary_row, self.secondary_row,
                    self.dot_server_row, self.dot_secondary_row, self.description_row]:
            group.add(row)

    def _on_type_changed(self, *_):
        self._update_field_visibility(self.type_row.get_selected())

    def _update_field_visibility(self, selected: int):
        # 0: Standard, 1: DoT
        self.primary_row.set_visible(selected == 0)
        self.secondary_row.set_visible(selected == 0)

        self.dot_server_row.set_visible(selected == 1)
        self.dot_secondary_row.set_visible(selected == 1)

    def _populate_fields(self):
        self.name_row.set_text(self.profile.name)
        if self.profile.servers:
            s = self.profile.servers[0]
            self.description_row.set_text(s.description or "")
            # Legacy DoH profiles open as Standard so they can be converted
            selected_idx = 1 if s.dns_type == DNSType.DOT else 0
            self.type_row.set_selected(selected_idx)

            if s.dns_type == DNSType.DOT:
                if s.tls_hostname and s.primary != s.tls_hostname:
                    self.dot_server_row.set_text(f"{s.primary}#{s.tls_hostname}")
                else:
                    self.dot_server_row.set_text(s.primary or s.tls_hostname or "")
                self.dot_secondary_row.set_text(s.secondary or "")
            else:
                self.primary_row.set_text(s.primary or "")
                self.secondary_row.set_text(s.secondary or "")

            self._update_field_visibility(selected_idx)

    @staticmethod
    def _parse_dot_server(raw: str) -> tuple[str, Optional[str]]:
        raw = raw.strip()
        if '#' in raw:
            parts = raw.split('#', 1)
            return parts[0].strip(), parts[1].strip() or None
        if raw in KNOWN_DOT_PROVIDERS:
            return KNOWN_DOT_PROVIDERS[raw], raw
        if raw in KNOWN_IP_TO_DOT:
            return raw, KNOWN_IP_TO_DOT[raw]
        return raw, None

    def get_profile(self) -> tuple[Optional[DNSProfile], Optional[str]]:
        name = self.name_row.get_text().strip()
        if not name:
            return None, "Profile Name is required."

        selected = self.type_row.get_selected()
        dns_type = [DNSType.STANDARD, DNSType.DOT][selected]
        description = self.description_row.get_text().strip() or None

        if dns_type == DNSType.STANDARD:
            primary = self.primary_row.get_text().strip()
            if not primary:
                return None, "Primary DNS IP is required for Standard DNS."
            secondary = self.secondary_row.get_text().strip() or None
            server = DNSServer(name=name, primary=primary, secondary=secondary,
                               dns_type=dns_type, description=description)
            return DNSProfile(name, [server]), None

        elif dns_type == DNSType.DOT:
            raw_server = self.dot_server_row.get_text().strip()
            if not raw_server:
                return None, "DoT Server address or hostname is required."

            primary, tls_hostname = self._parse_dot_server(raw_server)
            raw_secondary = self.dot_secondary_row.get_text().strip()
            secondary = None
            if raw_secondary:
                sec_primary, _ = self._parse_dot_server(raw_secondary)
                secondary = sec_primary

            server = DNSServer(name=name, primary=primary, secondary=secondary,
                               dns_type=dns_type, tls_hostname=tls_hostname,
                               description=description)
            return DNSProfile(name, [server]), None

        return None, "Invalid DNS type."
