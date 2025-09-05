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
    original_hosts = parser.parse_ssh_config(text)
    processed: list[HostConfig] = []
    for h in original_hosts:
        base_raw = (h.hostname or h.host)
        safe = sanitize_filename(base_raw)
        h.host = safe
        if not h.hostname:
            h.hostname = safe
        if h.hostname == '*':
            click.echo("Skipping wildcard/default block with HostName * (not writing separate file)")
            continue
        processed.append(h)

    # Handle identity files: group by original expanded path
    identity_groups: dict[Path, list[HostConfig]] = {}
    for h in processed:
        if h.identity_file:
            p = Path(h.identity_file).expanduser()
            if p.exists():
                identity_groups.setdefault(p, []).append(h)

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    for orig_path, group in identity_groups.items():
        if len(group) == 1:
            # Move (rename) single ownership key
            host_cfg = group[0]
            try:
                relocate_identity_file(host_cfg, host_cfg.host)
            except Exception as exc:  # pragma: no cover
                click.echo(f"Warning: relocate failed for {host_cfg.host}: {exc}", err=True)
        else:
            # Duplicate the key for each host (copy) keeping original in place
            base = orig_path.name
            pub_src = _derive_pub_path(orig_path)
            for host_cfg in group:
                if base.startswith(host_cfg.host):
                    new_name = base
                else:
                    new_name = f"{host_cfg.host}_{base}"
                dest = KEYS_DIR / new_name
                if not dest.exists():
                    try:
                        _copy_file(orig_path, dest)
                        dest.chmod(0o600)
                    except Exception as exc:  # pragma: no cover
                        click.echo(f"Warning: copy failed for {host_cfg.host}: {exc}", err=True)
                # Public key
                if pub_src.exists():
                    pub_dest = _match_pub_dest(dest)
                    if not pub_dest.exists():
                        try:
                            _copy_file(pub_src, pub_dest)
                            pub_dest.chmod(0o644)
                        except Exception:
                            pass
                host_cfg.identity_file = str(dest)

    # Write host configs
    for h in processed:
        store.write_host_config(CONFIG_D_DIR, h)
    regenerate_main_config()
    click.echo(f"Parsed {len(processed)} host blocks -> {CONFIG_D_DIR}")


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


def relocate_identity_file(host_cfg: HostConfig, safe_alias: str) -> None:
    """Move the referenced identity file (and its .pub) into KEYS_DIR.

    Naming strategy:
      - If original basename already starts with the sanitized alias, keep it.
      - Else prefix with '<alias>_'. E.g., alias 'web1' + 'id_ed25519' -> 'web1_id_ed25519'.
      - Preserve original basename when already under KEYS_DIR (no move needed).
    Updates host_cfg.identity_file with the absolute path to the relocated key.
    """
    original_str = host_cfg.identity_file
    if not original_str:
        return
    orig_path = Path(original_str).expanduser()
    if not orig_path.exists():  # nothing to move
        return
    # If already in KEYS_DIR, just normalize to absolute path and return
    if KEYS_DIR in orig_path.parents or orig_path.parent == KEYS_DIR:
        host_cfg.identity_file = str(orig_path)
        return

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    base = orig_path.name
    if base.startswith(safe_alias):
        new_name = base
    else:
        new_name = f"{safe_alias}_{base}"
    dest = KEYS_DIR / new_name
    if not dest.exists():  # avoid overwriting; if exists we reuse
        orig_path.replace(dest)
    # Move .pub if exists
    pub_src = orig_path.with_suffix(orig_path.suffix + '.pub') if orig_path.suffix else Path(str(orig_path) + '.pub')
    if pub_src.exists():
        pub_dest = dest.with_suffix(dest.suffix + '.pub') if dest.suffix else Path(str(dest) + '.pub')
        if not pub_dest.exists():
            try:
                pub_src.replace(pub_dest)
            except Exception:
                pass
        # set permissions
        try:
            pub_dest.chmod(0o644)
        except Exception:
            pass
    # Set private key perms
    try:
        dest.chmod(0o600)
    except Exception:
        pass
    host_cfg.identity_file = str(dest)


def _derive_pub_path(priv: Path) -> Path:
    # If private key has a suffix (like .pem) append .pub to full name, else just add .pub
    return priv.with_suffix(priv.suffix + '.pub') if priv.suffix else Path(str(priv) + '.pub')


def _match_pub_dest(priv_dest: Path) -> Path:
    return _derive_pub_path(priv_dest)


def _copy_file(src: Path, dest: Path) -> None:
    data = src.read_bytes()
    dest.write_bytes(data)
