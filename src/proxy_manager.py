import os
import subprocess
from typing import Dict
from gi.repository import Gio

class ProxyManager:
    def __init__(self):
        self.desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    def get_proxy_settings(self) -> Dict:
        settings = {'enabled': False, 'host': '', 'port': 0}
        try:
            if 'gnome' in self.desktop_env:
                gsettings = Gio.Settings.new("org.gnome.system.proxy")
                if gsettings.get_string('mode') == 'manual':
                    settings = {'enabled': True, 'host': gsettings.get_string('http-host'), 'port': gsettings.get_int('http-port')}
            elif 'kde' in self.desktop_env:
                proxy_type = subprocess.run(['kreadconfig5', '--group', 'Proxy Settings', '--key', 'ProxyType'], capture_output=True, text=True, check=False).stdout.strip()
                if proxy_type == '1':
                    proxy_str = subprocess.run(['kreadconfig5', '--group', 'Proxy Settings', '--key', 'httpProxy'], capture_output=True, text=True, check=False).stdout.strip()
                    if '://' in proxy_str:
                        proxy_str = proxy_str.split('://')[1]
                    host, port = proxy_str.split(':')
                    settings = {'enabled': True, 'host': host, 'port': int(port)}
        except (Exception, FileNotFoundError):
            pass
        return settings
