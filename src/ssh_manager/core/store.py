from __future__ import annotations

import shutil
import time
from pathlib import Path

from .model import HostConfig
from .util import sanitize_filename


def write_host_config(config_d_dir: Path, host: HostConfig) -> Path:
    config_d_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = sanitize_filename(host.host or host.hostname or "host")
    path = config_d_dir / f"{safe_stem}.conf"
    tmp = path.with_suffix('.tmp')
    tmp.write_text(host.serialize(), encoding='utf-8')
    tmp.replace(path)
    return path


def backup_snapshot(ssh_dir: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    dest = backup_dir / stamp
    dest.mkdir(mode=0o700)
    # Copy selected items
    for name in ["config", "config.d", "keys"]:
        p = ssh_dir / name
        if p.exists():
            if p.is_dir():
                shutil.copytree(p, dest / name)
            else:
                shutil.copy2(p, dest / name)
    return dest
