from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from pathlib import Path

from ..core import parser

SSH_DIR = Path.home() / ".ssh"
CONFIG_D_DIR = SSH_DIR / "config.d"


class HostsView(Static):
    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        items = []
        for file in sorted(CONFIG_D_DIR.glob("*.conf")):
            try:
                host = parser.parse_host_file(file.read_text(encoding="utf-8"))
                items.append(f"[b]{host.host}[/b] {host.hostname} ({host.user})")
            except Exception as e:  # pragma: no cover - display only
                items.append(f"[red]{file.name}: {e}")
        if not items:
            items.append("No host configs yet. Use 'ssh-manager new' or 'parse'.")
        self.update("\n".join(items))


class SSHManagerApp(App):
    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield Header(show_clock=True)
        yield HostsView()
        yield Footer()

    def action_refresh(self) -> None:
        hv = self.query_one(HostsView)
        hv.refresh_content()


__all__ = ["SSHManagerApp"]
