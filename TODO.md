# TODO / Roadmap

Legend:
- [x] done
- [~] partial / basic implementation present
- [ ] not started

## Core Features
- [~] Robust SSH config parser
  - [ ] Multiple host patterns on one line (e.g. `Host web1 web2`)
  - [ ] Wildcard / pattern hosts (e.g. `Host *.corp`) handling (store in a shared file or keep monolithic)
  - [ ] Preserve original comments & blank lines for round-trip fidelity
  - [ ] Support `Match` blocks (retain untouched, maybe separate file)
  - [ ] Support `Include` directives (inline or record + warn)
  - [ ] Parse multi-line values / continuation lines
  - [ ] Parse multiple `IdentityFile` lines
  - [ ] Graceful error reporting with line numbers
- [ ] Serializer round-trip mode (preserve ordering + comments, idempotent rebuild)
- [~] Split monolithic config into `config.d/*.conf` (basic done)
- [ ] Merge logic to detect and unify identical option blocks across hosts (DRY suggestions)

## CLI Commands
- [x] `parse`
- [x] `new`
- [x] `build` (include + single)
- [x] `audit`
- [x] `backup`
- [ ] `restore` (interactive + non-interactive flag for a specific snapshot)
- [ ] `rotate-key` (generate new key, update host, optionally keep old as `.old`)
- [ ] `prune` (guide deletion of orphaned keys / disabled hosts with confirmation + fresh backup)
- [ ] `fix-perms` (auto-correct key & directory permissions)
- [ ] `export --format json|yaml` full structured view of all hosts
- [ ] `import --format json|yaml` apply structured config (with backup + diff)
- [ ] `archive --host <name>` (move host config + keys into an `archived/` subfolder)
- [ ] `rename-host old new` (rename host alias + key filenames if desired)

## Key Management
- [x] Generate key on `new`
- [~] Orphan detection (`audit` shows orphaned) – needs cleanup workflow
- [ ] Key rotation command (preserve old key until confirmed deployed)
- [ ] Detect duplicate public keys (same content used by multiple hosts)
- [ ] SSH agent integration status check (is key loaded?)
- [ ] Optional automatic `ssh-copy-id` retry with host reachability test

## Backups & Safety
- [x] Timestamped snapshot (`backup`)
- [ ] Restore operation (with dry-run diff + confirmation)
- [ ] Retention policy (keep last N or prune > N days old)
- [ ] Integrity verification (hash manifest per snapshot)
- [ ] Pre-change auto-backup wrapper for mutating commands (`new`, `rotate-key`, `prune`, `import`)

## TUI (Textual)
- [~] Basic host list view
- [ ] Split layout (sidebar list + detail pane + status bar)
- [ ] Search/filter hosts (incremental)
- [ ] Host detail panel (options, key status, issues)
- [ ] Audit summary overlay (press a key to view issues)
- [ ] Actions bar / key bindings (N=new, A=audit, R=rotate, D=delete/archive, P=prune orphans, B=backup)
- [ ] Modal forms for creating/rotating hosts
- [ ] Live file system watcher (auto-refresh on external edits)
- [ ] Theming / color severity badges
- [ ] Async task feedback (spinners for key gen / copy-id)

## UX / DX Enhancements
- [ ] Rich diff output before applying destructive changes
- [ ] Global `--dry-run` for mutating commands
- [ ] Global `--backup` flag override (on/off) + config file
- [ ] Configurable defaults (YAML or TOML in `~/.config/ssh-manager/config.toml`)
- [ ] Shell completion scripts generation (bash/zsh/fish)
- [ ] Verbose / debug logging with `--verbose` flag

## Validation / Linting
- [ ] Host alias uniqueness enforcement with suggestion for rename
- [ ] Detection of unreachable IdentityFile paths (already partial in audit) – expand to relative path normalisation
- [ ] Permission auto-fix suggestions (directory 700, private key 600, public 644, config 600)
- [ ] Duplicate option detection inside a host block

## Testing
- [ ] Unit tests for: parser edge cases (multi-alias, comments, duplicates)
- [ ] Tests for `audit` permission + missing key reporting
- [ ] Tests for `backup` + (future) `restore` round-trip
- [ ] TUI smoke tests (Textual App + headless mode)
- [ ] CLI integration tests via `click.testing.CliRunner`
- [ ] Property-based tests for parse -> serialize idempotency when round-trip mode ready

## Packaging & Release
- [ ] Add `__main__.py` for `python -m ssh_manager`
- [ ] Version bump automation (maybe `bumpver` or `hatch version` if tool changed)
- [ ] Publish to PyPI (when stable)
- [ ] Pre-commit hooks (ruff, mypy, pytest quick) – optional
- [ ] GitHub Actions CI (lint + test matrix)

## Documentation
- [ ] Expand README with screenshots (once TUI richer)
- [ ] Add `USAGE.md` with advanced examples
- [ ] Add `SCHEMA.md` for structured JSON/YAML export format
- [ ] FAQ / Troubleshooting section

## Future / Stretch Ideas
- [ ] SSH known_hosts management (prune dead entries, verify fingerprints)
- [ ] Integration with password managers / secret stores for passphrased keys
- [ ] Cloud inventory import (e.g., scan AWS EC2 / GCP / etc.) to prepopulate host stubs
- [ ] Multi-profile environments (different sets of hosts via profile selector)
- [ ] Encryption of archived keys bundle
- [ ] Web / REST API mode (serve config metadata read-only)
- [ ] Ansible inventory export

## Technical Debt / Refactors
- [ ] Replace ad-hoc regex parser with a small tokenizing state machine for resilience
- [ ] Introduce a `Repository` abstraction layer to allow mocking filesystem easily
- [ ] Add structured logging (e.g., `structlog` optional dependency)
- [ ] Consolidate constants (paths, defaults) into a `settings` module
- [ ] Lazy load Textual dependency only for TUI command (already partly done in `tui` command)

## Open Questions
- How to treat multiple aliases: split into multiple `.conf` files or keep a primary file with alias list? (Leaning: keep in one file; represent `aliases` in model.)
- Should defaults block be editable via config file or always fixed? (Plan: user override file appended.)
- Do we allow environment variable expansion inside host configs when parsing/serializing?
- Provide a migration log file when parsing large legacy config? (Maybe store JSON diff summary.)

## Prioritized Next (Suggested Order)
1. Restore command (foundation for safe experimentation)
2. Parser multi-alias + comment preservation
3. Rotate-key command
4. TUI host detail & action bindings
5. Prune + fix-perms commands
6. CI + more tests
7. Export/import structured formats

---
Feel free to check off items as they are completed and adjust priorities as new needs emerge.
