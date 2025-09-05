from __future__ import annotations

import re
from typing import List

from .model import HostConfig

HOST_RE = re.compile(r"^Host\s+(?P<host>.+)$", re.IGNORECASE)
INDENTED_RE = re.compile(r"^\s+(?P<key>[A-Za-z][A-Za-z0-9]*)\s+(?P<value>.+)$")


def parse_ssh_config(text: str) -> List[HostConfig]:
    hosts: List[HostConfig] = []
    current: HostConfig | None = None
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith('#'):
            continue
        m = HOST_RE.match(line)
        if m:
            if current:
                hosts.append(current)
            # Pick only the first alias if multiple are specified
            raw_host_field = m.group('host').strip()
            first_alias = raw_host_field.split()[0]
            current = HostConfig(host=first_alias, hostname=first_alias)
            continue
        m2 = INDENTED_RE.match(line)
        if m2 and current:
            key = m2.group('key').lower()
            val = m2.group('value').strip()
            if key == 'hostname':
                current.hostname = val
            elif key == 'user':
                current.user = val
            elif key == 'port':
                try:
                    current.port = int(val)
                except ValueError:
                    pass
            elif key == 'identityfile':
                current.identity_file = val
            else:
                current.extra_options.append(line)
    if current:
        hosts.append(current)
    return hosts


def parse_host_file(text: str) -> HostConfig:
    hosts = parse_ssh_config(text)
    if not hosts:
        raise ValueError("No host block found")
    return hosts[0]
