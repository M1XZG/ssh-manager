from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HostConfig:
    host: str
    hostname: str
    user: str = "root"
    port: int = 22
    identity_file: Optional[str] = None
    extra_options: List[str] = field(default_factory=list)

    def serialize(self) -> str:
        lines = [f"Host {self.host}"]
        lines.append(f"  HostName {self.hostname}")
        if self.user:
            lines.append(f"  User {self.user}")
        if self.port and self.port != 22:
            lines.append(f"  Port {self.port}")
        if self.identity_file:
            lines.append(f"  IdentityFile {self.identity_file}")
        lines.extend(self.extra_options)
        return "\n".join(lines) + "\n"
