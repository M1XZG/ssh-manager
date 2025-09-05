from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

import click

from .core.model import HostConfig
from .core import parser, store
from .core.util import sanitize_filename
from . import __version__

DEFAULTS_BLOCK = """##########\n# defaults\n##########\nHost *\n  ForwardX11 no\n  Protocol 2\n  TCPKeepAlive yes\n  ServerAliveInterval 10\n  Compression yes\n"""

SSH_DIR = Path.home() / ".ssh"
CONFIG_FILE = SSH_DIR / "config"
CONFIG_D_DIR = SSH_DIR / "config.d"
KEYS_DIR = SSH_DIR / "keys"
BACKUP_DIR = SSH_DIR / "manager_backups"

@click.group()
@click.version_option(__version__)
def main() -> None:
    """ssh-manager: organize and manage your ~/.ssh directory."""


def ensure_layout() -> None:
    for p in [SSH_DIR, CONFIG_D_DIR, KEYS_DIR, BACKUP_DIR]:
        p.mkdir(mode=0o700, exist_ok=True)


@main.command()
@click.option("--input", "input_path", type=click.Path(path_type=Path), default=CONFIG_FILE, help="Source SSH config to parse")
@click.option("--backup/--no-backup", default=True, help="Create a backup snapshot before modifying files")
def parse(input_path: Path, backup: bool) -> None:
    """Parse a monolithic SSH config and split into config.d/*.conf."""
    ensure_layout()
    if backup:
        snapshot = store.backup_snapshot(SSH_DIR, BACKUP_DIR)
        click.echo(f"Backup created at {snapshot}")

    text = input_path.read_text(encoding="utf-8") if input_path.exists() else ""
    hosts = parser.parse_ssh_config(text)
    for h in hosts:
        base_raw = (h.hostname or h.host)
        safe = sanitize_filename(base_raw)
        h.host = safe  # ensure alias line matches the sanitized filename stem
        if not h.hostname:
            h.hostname = safe
        store.write_host_config(CONFIG_D_DIR, h)
    regenerate_main_config()
    click.echo(f"Parsed {len(hosts)} host blocks -> {CONFIG_D_DIR}")


def regenerate_main_config(single: bool = False) -> str:
    hosts = []
    for file in sorted(CONFIG_D_DIR.glob("*.conf")):
        hosts.append(file.read_text(encoding="utf-8").rstrip() + "\n")

    if single:
        combined = "".join(hosts) + "\n" + DEFAULTS_BLOCK
        CONFIG_FILE.write_text(combined, encoding="utf-8")
        return combined

    include_lines = ["Include config.d/*.conf", "", DEFAULTS_BLOCK]
    content = "\n".join(include_lines)
    CONFIG_FILE.write_text(content, encoding="utf-8")
    return content


@main.command()
@click.option("--single", is_flag=True, help="Generate single combined config instead of Include-based")
def build(single: bool) -> None:
    """Regenerate the main ~/.ssh/config file."""
    ensure_layout()
    regenerate_main_config(single=single)
    click.echo("Main config regenerated")


@main.command()
@click.option("--host", required=True)
@click.option("--user", default="root")
@click.option("--hostname", help="Actual host/IP if Host alias differs")
@click.option("--port", type=int, default=22)
@click.option("--key-type", type=click.Choice(["ed25519", "rsa"]), default="ed25519")
@click.option("--no-copy-id", is_flag=True, help="Do not attempt ssh-copy-id after key generation")
def new(host: str, user: str, hostname: Optional[str], port: int, key_type: str, no_copy_id: bool) -> None:
    """Create a new host config + key pair (and optionally copy key to remote)."""
    ensure_layout()
    safe_host = sanitize_filename(host)
    host = safe_host  # normalized alias stored
    key_name = f"{safe_host}_{key_type}"
    priv = KEYS_DIR / key_name
    pub = KEYS_DIR / (key_name + ".pub")
    if priv.exists():
        click.echo(f"Key {priv} already exists", err=True)
        raise SystemExit(1)

    # Generate key
    cmd = ["ssh-keygen", "-t", key_type, "-f", str(priv), "-N", "", "-C", f"{user}@{host}"]
    subprocess.run(cmd, check=True)
    # Restrict permissions explicitly
    priv.chmod(0o600)
    if pub.exists():
        pub.chmod(0o644)

    hc = HostConfig(
        host=host,
        hostname=hostname or host,
        user=user,
        port=port,
        identity_file=str(priv),
    )
    store.write_host_config(CONFIG_D_DIR, hc)
    regenerate_main_config()
    click.echo(f"Created host config {host} with key {priv}")

    if not no_copy_id:
        try:
            subprocess.run(["ssh-copy-id", f"{user}@{hc.hostname}"], check=True)
        except subprocess.CalledProcessError:
            click.echo("ssh-copy-id failed; you may need to add the key manually", err=True)


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output JSON for scripting")
def audit(as_json: bool) -> None:
    """Report orphaned keys, missing keys, duplicate hosts, and permission issues."""
    ensure_layout()
    host_files = list(CONFIG_D_DIR.glob("*.conf"))
    hosts = [parser.parse_host_file(f.read_text(encoding="utf-8")) for f in host_files]
    by_alias = {}
    duplicates = []
    for h in hosts:
        if h.host in by_alias:
            duplicates.append(h.host)
        else:
            by_alias[h.host] = h

    # Keys on disk
    priv_keys = [k for k in KEYS_DIR.glob("*") if k.is_file() and not k.name.endswith('.pub')]
    referenced = set(Path(h.identity_file).name for h in hosts if h.identity_file)
    orphaned = [k.name for k in priv_keys if k.name not in referenced]
    missing = [h.identity_file for h in hosts if h.identity_file and not Path(h.identity_file).expanduser().exists()]

    # Simple permission checks (private keys should be 600)
    bad_perms = []
    for k in priv_keys:
        mode = k.stat().st_mode & 0o777
        if mode != 0o600:
            bad_perms.append(f"{k.name} (mode {oct(mode)})")

    report = {
        "host_count": len(hosts),
        "duplicates": duplicates,
        "orphaned_private_keys": orphaned,
        "missing_referenced_keys": missing,
        "bad_key_permissions": bad_perms,
    }
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return

    click.echo(f"Hosts: {report['host_count']}")
    if duplicates:
        click.echo(f"Duplicate host aliases: {', '.join(duplicates)}")
    if orphaned:
        click.echo(f"Orphaned private keys: {', '.join(orphaned)}")
    if missing:
        click.echo(f"Missing referenced keys: {', '.join(missing)}")
    if bad_perms:
        click.echo(f"Keys with insecure permissions: {', '.join(bad_perms)}")
    if not any([duplicates, orphaned, missing, bad_perms]):
        click.echo("No issues detected")


@main.command()
def backup() -> None:
    """Create a backup snapshot of the ~/.ssh layout."""
    ensure_layout()
    snapshot = store.backup_snapshot(SSH_DIR, BACKUP_DIR)
    click.echo(f"Backup created: {snapshot}")


@main.command()
def tui() -> None:  # pragma: no cover - UI launcher
    """Launch the Textual TUI interface."""
    try:
        from .tui.app import SSHManagerApp
    except Exception as exc:  # broad for user friendliness
        raise SystemExit(f"TUI not available: {exc}")
    SSHManagerApp().run()


# End of file
