# ssh-manager

A TUI + CLI tool to organize and manage your `~/.ssh` directory:

- Parse a messy legacy `~/.ssh/config` into structured per-host includes under `~/.ssh/config.d/`
- Maintain a canonical generated `~/.ssh/config` that `Include`s individual host files plus a standardized defaults block
- Detect orphaned private/public keys with no matching host config (potential cleanup candidates)
- Create new host entries with guided key generation and optional `ssh-copy-id`
- Backup & restore configs and keys safely
- Re-compose a single flat config if desired

## Status
Early scaffold (v0.1.0). Core parsing & TUI not implemented yet.

## Planned Features
1. CLI commands (scriptable):
   - `ssh-manager parse --input ~/.ssh/config` -> populate `config.d/*.conf`
   - `ssh-manager new --host mybox --user ubuntu --key-type ed25519` (with optional copy-id)
   - `ssh-manager audit` (list orphaned keys, duplicate hosts, permission issues)
   - `ssh-manager build --single` (emit a flattened combined config)
   - `ssh-manager backup` / `restore`
2. TUI (Textual) dashboard:
   - Sidebar hosts list, detail pane, key status badges
   - Actions: add host, rotate key, archive host, open in editor
3. Safety / backups strategy:
   - Versioned timestamped backups under `~/.ssh/manager_backups/`
   - Pre-change backup & transactional writes (write temp -> fsync -> atomic rename)

## Architecture Outline
- `ssh_manager.cli` (Click entrypoint)
- `ssh_manager.core.config_parser` (robust parser / serializer)
- `ssh_manager.core.model` (dataclasses: HostConfig, SSHKeyPair, ManagerState)
- `ssh_manager.core.store` (filesystem operations, atomic writes, backups)
- `ssh_manager.tui.app` (Textual App)
- `ssh_manager.tui.views.*` (Composable views/widgets)

## Default Canonical Layout
```
~/.ssh/
  config            # Include config.d/*.conf + defaults
  config.d/
    host1.conf
    host2.conf
  keys/
    host1_ed25519    (600)
    host1_ed25519.pub (644)
  manager_backups/
    2025-09-05_120102/
      config
      config.d/*.conf
      keys/*
```

## Generated Defaults Block
```
##########
# defaults
##########
Host *
  ForwardX11 no
  Protocol 2
  TCPKeepAlive yes
  ServerAliveInterval 10
  Compression yes
```

## Development
Install deps:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```
Run CLI help:
```
ssh-manager --help
```
Run test suite:
```
pytest -q
```

## License
MIT
# ssh-manager
SSH Key and Config Manager
