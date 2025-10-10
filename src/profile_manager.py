import json
import os
from pathlib import Path
from typing import List
from models import DNSProfile, DNSServer, DNSType

class ProfileManager:
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'namban'
        self.config_file = self.config_dir / 'profiles.json'
        self.ensure_config_dir()
        self.profiles = self.load_profiles()

    def ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_profiles(self) -> List[DNSProfile]:
        default_profiles = [
            DNSProfile("Cloudflare", [DNSServer("Cloudflare", "1.1.1.1", "1.0.0.1")]),
            DNSProfile("Cloudflare DoH", [DNSServer("Cloudflare DoH", "1.1.1.1", "1.0.0.1", DNSType.DOH, "https://cloudflare-dns.com/dns-query")]),
            DNSProfile("Google", [DNSServer("Google", "8.8.8.8", "8.8.4.4")]),
            DNSProfile("Quad9", [DNSServer("Quad9", "9.9.9.9", "149.112.112.112")]),
            DNSProfile("OpenDNS", [DNSServer("OpenDNS", "208.67.222.222", "208.67.220.220")])
        ]
        if not self.config_file.exists():
            self.save_profiles(default_profiles)
            return default_profiles
        try:
            with self.config_file.open('r') as f:
                return self._deserialize_profiles(json.load(f))
        except (json.JSONDecodeError, TypeError):
            return default_profiles

    def save_profiles(self, profiles: List[DNSProfile]):
        try:
            with self.config_file.open('w') as f:
                json.dump(self._serialize_profiles(profiles), f, indent=4)
        except Exception:
            pass

    def _serialize_profiles(self, profiles: List[DNSProfile]) -> List[dict]:
        return [{'name': p.name, 'servers': [s.__dict__ | {'dns_type': s.dns_type.value} for s in p.servers]} for p in profiles]

    def _deserialize_profiles(self, data: List[dict]) -> List[DNSProfile]:
        return [DNSProfile(item['name'], [DNSServer(**(s | {'dns_type': DNSType(s.get('dns_type', 'standard'))})) for s in item.get('servers', [])]) for item in data]

    def add_profile(self, profile: DNSProfile):
        self.profiles.append(profile)
        self.save_profiles(self.profiles)

    def remove_profile(self, profile: DNSProfile):
        try:
            self.profiles.remove(profile)
            self.save_profiles(self.profiles)
        except ValueError:
            pass

    def update_profile(self, old_profile: DNSProfile, new_profile: DNSProfile):
        try:
            self.profiles[self.profiles.index(old_profile)] = new_profile
            self.save_profiles(self.profiles)
        except ValueError:
            pass
