from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ListView, ListItem, Input, Button
from textual.reactive import reactive
from textual.containers import Horizontal, Vertical
from textual import events
from pathlib import Path
import subprocess

from ..core import parser, store
from ..cli import regenerate_main_config  # reuse existing logic

SSH_DIR = Path.home() / ".ssh"
CONFIG_D_DIR = SSH_DIR / "config.d"
KEYS_DIR = SSH_DIR / "keys"


class HostRecord:
    """Simple in-memory representation tying a HostConfig to its source file."""
    def __init__(self, file: Path, host_cfg):
        self.file = file
        self.host_cfg = host_cfg


class HostList(ListView):  # pragma: no cover - thin widget wrapper
    pass


class HostDetail(Vertical):
    editing: reactive[bool] = reactive(False)
    current: reactive[HostRecord | None] = reactive(None)
    status: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield Static("Host Details", id="title")
        # Build compact labeled rows (Host directive names shown explicitly)
        self.input_host = Input(placeholder="Host", disabled=True, id="field-host")
        self.input_hostname = Input(placeholder="HostName", disabled=True, id="field-hostname")
        self.input_user = Input(placeholder="User", disabled=True, id="field-user")
        self.input_port = Input(placeholder="Port", disabled=True, id="field-port")
        self.input_identity = Input(placeholder="IdentityFile", disabled=True, id="field-identity")

        def row(label: str, widget: Input) -> Horizontal:
            return Horizontal(Static(f"{label}", classes="label"), widget, classes="row")

        yield row("Host:", self.input_host)
        yield row("HostName:", self.input_hostname)
        yield row("User:", self.input_user)
        yield row("Port:", self.input_port)
        yield row("IdentityFile:", self.input_identity)
        btn_row = Horizontal(
            Button("Edit (e)", id="edit"),
            Button("Save (s)", id="save", disabled=True),
            Button("Gen Key (g)", id="gen", disabled=True),
            Button("Cancel (esc)", id="cancel", disabled=True),
            id="buttons"
        )
        yield btn_row
        self.status_widget = Static(id="status")
        yield self.status_widget

    def watch_status(self, value: str) -> None:  # pragma: no cover - trivial
        self.status_widget.update(value)

    def set_record(self, rec: HostRecord | None) -> None:
        self.current = rec
        if not rec:
            for inp in [self.input_host, self.input_hostname, self.input_user, self.input_port, self.input_identity]:
                inp.value = ""
            return
        h = rec.host_cfg
        self.input_host.value = h.host
        self.input_hostname.value = h.hostname
        self.input_user.value = h.user
        self.input_port.value = str(h.port)
        self.input_identity.value = h.identity_file or ""
        self.status = ""
        self.disable_edit_mode()

    def enable_edit_mode(self) -> None:
        if not self.current:
            return
        self.editing = True
        for inp in [self.input_hostname, self.input_user, self.input_port]:
            inp.disabled = False
        self.query_one('#save', Button).disabled = False
        self.query_one('#gen', Button).disabled = False
        self.query_one('#cancel', Button).disabled = False
        self.query_one('#edit', Button).disabled = True

    def disable_edit_mode(self) -> None:
        self.editing = False
        for inp in [self.input_host, self.input_hostname, self.input_user, self.input_port, self.input_identity]:
            inp.disabled = True
        self.query_one('#save', Button).disabled = True
        self.query_one('#gen', Button).disabled = True
        self.query_one('#cancel', Button).disabled = True
        self.query_one('#edit', Button).disabled = self.current is None

    def action_edit(self) -> None:
        self.enable_edit_mode()

    def action_cancel(self) -> None:
        if self.current:
            self.set_record(self.current)

    def action_save(self) -> None:
        if not self.current:
            return
        h = self.current.host_cfg
        h.hostname = self.input_hostname.value.strip() or h.hostname
        h.user = self.input_user.value.strip() or h.user
        try:
            h.port = int(self.input_port.value.strip()) if self.input_port.value.strip() else h.port
        except ValueError:
            self.status = "Invalid port; keeping previous"
        store.write_host_config(CONFIG_D_DIR, h)
        regenerate_main_config()
        self.status = "Saved." if not self.status else self.status + " Saved."
        self.disable_edit_mode()

    def action_generate_key(self) -> None:
        if not self.current:
            return
        h = self.current.host_cfg
        alias = h.host
        key_type = 'ed25519'  # future: prompt
        KEYS_DIR.mkdir(parents=True, exist_ok=True)
        key_name = f"{alias}_{key_type}"
        priv = KEYS_DIR / key_name
        pub = KEYS_DIR / (key_name + '.pub')
        if priv.exists():
            self.status = f"Key {priv.name} exists"
            self.input_identity.value = str(priv)
            return
        try:
            cmd = ["ssh-keygen", "-t", key_type, "-f", str(priv), "-N", "", "-C", f"{h.user}@{h.hostname}"]
            subprocess.run(cmd, check=True)
            priv.chmod(0o600)
            if pub.exists():
                pub.chmod(0o644)
            h.identity_file = str(priv)
            store.write_host_config(CONFIG_D_DIR, h)
            regenerate_main_config()
            self.input_identity.value = h.identity_file
            self.status = f"Generated key {priv.name}"
        except Exception as exc:  # pragma: no cover - subprocess error visual only
            self.status = f"Key gen failed: {exc}"

    # Button press handling
    def on_button_pressed(self, event: Button.Pressed) -> None:  # pragma: no cover - UI glue
        bid = event.button.id
        if bid == 'edit':
            self.action_edit()
        elif bid == 'save':
            self.action_save()
        elif bid == 'gen':
            self.action_generate_key()
        elif bid == 'cancel':
            self.action_cancel()


class SSHManagerApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("e", "edit", "Edit"),
        ("s", "save", "Save"),
        ("g", "generate_key", "Gen Key"),
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield Header(show_clock=True)
        self.host_list = HostList(id="hosts")
        self.detail = HostDetail(id="detail")
        layout = Horizontal(
            Vertical(Static("Hosts", id="hosts_title"), self.host_list, id="left"),
            self.detail,
            id="main"
        )
        yield layout
        yield Footer()

    def on_mount(self) -> None:  # pragma: no cover - simple load
        self.refresh_hosts()

    def refresh_hosts(self) -> None:
        self.host_list.clear()
        records = []
        for file in sorted(CONFIG_D_DIR.glob("*.conf")):
            try:
                host_cfg = parser.parse_host_file(file.read_text(encoding="utf-8"))
                rec = HostRecord(file, host_cfg)
                records.append(rec)
            except Exception as exc:  # pragma: no cover
                item = ListItem(Static(f"[red]{file.name}: {exc}"))
                self.host_list.append(item)
        for rec in records:
            label = f"{rec.host_cfg.host} ({rec.host_cfg.user}@{rec.host_cfg.hostname})"
            item = ListItem(Static(label))
            item.data = rec  # attach
            self.host_list.append(item)
        if records:
            self.detail.set_record(records[0])
            self.host_list.index = 0
        else:
            self.detail.set_record(None)

    def action_refresh(self) -> None:
        self.refresh_hosts()
        self.detail.status = "Refreshed"

    def on_list_view_highlighted(self, message: ListView.Highlighted) -> None:  # pragma: no cover - UI event
        item = message.item
        if hasattr(item, 'data') and item.data:
            self.detail.set_record(item.data)

    # Key binding actions
    def action_edit(self) -> None:
        self.detail.action_edit()

    def action_save(self) -> None:
        self.detail.action_save()

    def action_generate_key(self) -> None:
        self.detail.action_generate_key()

    def action_cancel(self) -> None:
        self.detail.action_cancel()


__all__ = ["SSHManagerApp"]
