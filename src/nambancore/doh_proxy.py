#!/usr/bin/env python3
"""
Namban Local DNS-over-HTTPS (DoH) Proxy (RFC 8484).
Translates local UDP DNS queries to encrypted HTTPS POST requests.
"""

import sys
import ssl
import asyncio
import urllib.request
import urllib.parse
from typing import Optional

class DoHProxyProtocol(asyncio.DatagramProtocol):
    def __init__(self, doh_url: str, bootstrap_ip: Optional[str] = None):
        self.doh_url = doh_url
        self.bootstrap_ip = bootstrap_ip
        self.transport = None
        self.ssl_context = ssl.create_default_context()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        asyncio.create_task(self._forward_query(data, addr))

    async def _forward_query(self, query_data: bytes, client_addr):
        try:
            req = urllib.request.Request(
                self.doh_url,
                data=query_data,
                headers={
                    "Content-Type": "application/dns-message",
                    "Accept": "application/dns-message",
                    "User-Agent": "Namban-DoH/2.0"
                },
                method="POST"
            )

            loop = asyncio.get_running_loop()
            response_data = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, context=self.ssl_context, timeout=5.0).read()
            )

            if self.transport and response_data:
                self.transport.sendto(response_data, client_addr)
        except Exception:
            pass

def main():
    if len(sys.argv) < 2:
        print("Usage: doh_proxy.py <doh_url> [listen_ip] [listen_port] [bootstrap_ip]")
        sys.exit(1)

    doh_url = sys.argv[1]
    listen_ip = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.54"
    listen_port = int(sys.argv[3]) if len(sys.argv) > 3 else 53
    bootstrap_ip = sys.argv[4] if len(sys.argv) > 4 else None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    endpoint = loop.create_datagram_endpoint(
        lambda: DoHProxyProtocol(doh_url, bootstrap_ip),
        local_addr=(listen_ip, listen_port)
    )
    transport, _ = loop.run_until_complete(endpoint)
    print(f"Namban DoH Proxy active on {listen_ip}:{listen_port} -> {doh_url}")

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
        loop.close()

if __name__ == "__main__":
    main()
