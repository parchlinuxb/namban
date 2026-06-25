from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class DNSType(Enum):
    STANDARD = "standard"
    DOH = "doh"
    DOT = "dot"

@dataclass
class DNSServer:
    name: str
    primary: str
    secondary: Optional[str] = None
    dns_type: DNSType = DNSType.STANDARD
    doh_url: Optional[str] = None
    description: Optional[str] = None

class DNSProfile:
    def __init__(self, name: str, servers: List[DNSServer]):
        self.name = name
        self.servers = servers
