"""Self-check for profile apply/undo. Run: python3 tests/test_dns_actions.py (or pytest)."""

import base64
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from models import DNSProfile, DNSServer, DNSType
from nambancore.toolbox import BaseToolBox
from nambancore.dns_actions import (ApplyDNSProfile, doh_stamp, DNSCRYPT_BIN, DNSCRYPT_CONF,
                                    DNSCRYPT_LISTEN, DNSCRYPT_UNIT)

CONF = ApplyDNSProfile.DEFAULT_CONF_PATH


class FakeToolBox(BaseToolBox):
    """In-memory stand-in for the root daemon."""
    def __init__(self, files=()):
        self.fs = dict.fromkeys(files, "")
        self.cmds = []
    def exists(self, p): return p in self.fs
    def read(self, p): return self.fs[p]
    def write(self, p, body): self.fs[p] = body; return True
    def remove(self, p): self.fs.pop(p, None); return True
    def mkdir(self, p): return True
    def execute(self, cmd): self.cmds.append(cmd); return True


def profile(dns_type, primary="", doh_url=None, tls_hostname=None):
    return DNSProfile("p", [DNSServer("p", primary, None, dns_type, doh_url=doh_url, tls_hostname=tls_hostname)])


def test_stamp_matches_cloudflare_reference():
    # From the public resolver list; only the props byte (7 there, 0 here) differs
    ref = "sdns://AgcAAAAAAAAABzEuMC4wLjEAEmRucy5jbG91ZGZsYXJlLmNvbQovZG5zLXF1ZXJ5"
    dec = lambda s: base64.urlsafe_b64decode(s[7:] + "=" * (-len(s[7:]) % 4))
    mine = dec(doh_stamp("https://dns.cloudflare.com/dns-query", "1.0.0.1"))
    assert mine[0] == 2 and mine[9:] == dec(ref)[9:]


def test_switching_profiles_and_undoing_everything():
    tb = FakeToolBox([DNSCRYPT_BIN])
    std = ApplyDNSProfile(profile(DNSType.STANDARD, "8.8.8.8")).do(tb)
    doh = ApplyDNSProfile(profile(DNSType.DOH, "1.1.1.1", "https://cloudflare-dns.com/dns-query")).do(tb)
    assert f"DNS={DNSCRYPT_LISTEN}" in tb.fs[CONF] and "sdns://" in tb.fs[DNSCRYPT_CONF]
    assert ['systemctl', 'enable', DNSCRYPT_UNIT] in tb.cmds
    dot = ApplyDNSProfile(profile(DNSType.DOT, "9.9.9.9", tls_hostname="dns.quad9.net")).do(tb)
    assert "9.9.9.9#dns.quad9.net" in tb.fs[CONF] and DNSCRYPT_CONF not in tb.fs
    assert tb.cmds[-1] == ['systemctl', 'disable', '--now', DNSCRYPT_UNIT]

    ApplyDNSProfile.undo(dot, tb)  # back to DoH: forwarder config restored
    assert f"DNS={DNSCRYPT_LISTEN}" in tb.fs[CONF] and "sdns://" in tb.fs[DNSCRYPT_CONF]
    ApplyDNSProfile.undo(doh, tb)  # back to standard: forwarder gone
    assert "DNS=8.8.8.8" in tb.fs[CONF] and DNSCRYPT_CONF not in tb.fs
    ApplyDNSProfile.undo(std, tb)  # back to nothing
    assert CONF not in tb.fs


def test_doh_refused_without_dnscrypt_or_with_bad_url():
    for tb, url in [(FakeToolBox(), "https://dns.google/dns-query"),
                    (FakeToolBox([DNSCRYPT_BIN]), "http://dns.google/dns-query"),
                    (FakeToolBox([DNSCRYPT_BIN]), "https://x.example/q'\nlisten_addresses = ['0.0.0.0:53']")]:
        try:
            ApplyDNSProfile(profile(DNSType.DOH, doh_url=url)).do(tb)
            raise AssertionError("should have been refused")
        except ValueError:
            pass
        assert set(tb.fs) <= {DNSCRYPT_BIN} and not tb.cmds  # nothing touched


def test_undo_of_record_from_before_doh_support():
    tb = FakeToolBox()
    ApplyDNSProfile.undo({'config_before': None, 'resolved_conf_path': CONF}, tb)
    assert CONF not in tb.fs


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
