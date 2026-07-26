"""David: Master dashboard — sidebar navigation + content switcher + audit console."""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Button,
    RichLog,
    ContentSwitcher,
    Static,
    Label,
)
from textual.containers import VerticalScroll, Horizontal, Vertical, Container

from screens.ingestion import IngestionScreen
from screens.forensic_log import ForensicLogScreen

SIDEBAR_BUTTONS = [
    ("dashboard", "Dashboard"),
    ("ingestion", "Ledger Ingestion"),
    ("forensic_log", "Forensic Log"),
    ("settings", "Settings"),
]

BUTTON_TO_CONTENT = {bid: cid for bid, _ in SIDEBAR_BUTTONS for cid in [bid]}


class DashboardScreen(Screen):
    """David: Main navigation hub.

    Layout:
      [Sidebar (width=24)]  |  [Main Content Pane]
      [  Dashboard      ]   |  ContentSwitcher shows
      [  Ledger Ingestion]   |  different views based
      [  Forensic Log    ]   |  on sidebar selection
      [  Settings        ]   |
      [                              ]
      [  Audit Console (RichLog)     ]

    Sidebar buttons switch content via ContentSwitcher.current.
    """

    CSS = "styles.tcss"

    def __init__(self, initial_tab: Optional[str] = None):
        super().__init__()
        self._initial_tab = initial_tab or "dashboard"
        self._current_tab: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="dashboard-body"):
            with VerticalScroll(id="sidebar") as sidebar:
                sidebar.border_title = "RootCFO"
                yield Label("NAVIGATION", id="sidebar-title")
                for button_id, label in SIDEBAR_BUTTONS:
                    yield Button(label, id=f"nav-{button_id}", classes="nav-btn")

            with Container(id="content-pane"):
                with ContentSwitcher(initial=self._initial_tab, id="content-switcher"):
                    with Vertical(id="dashboard"):
                        yield Static("📊  Audit Overview", classes="placeholder-title")
                        yield Static(
                            "Welcome to RootCFO. Use the sidebar to navigate.\n"
                            "• Ledger Ingestion — import CSV/JSON and run the pipeline\n"
                            "• Forensic Log   — review flagged anomalies\n"
                            "• Settings       — configure preferences",
                            classes="placeholder-body",
                        )
                    with Vertical(id="ingestion"):
                        yield Static("📥  Ledger Ingestion", classes="placeholder-title")
                        yield Static(
                            "Ingestion module placeholder.\n"
                            "Integrates with the full IngestionScreen when ready.",
                            classes="placeholder-body",
                        )
                    with Vertical(id="forensic_log"):
                        yield Static("🔍  Forensic Log", classes="placeholder-title")
                        yield Static(
                            "Anomaly review module placeholder.\n"
                            "Integrates with ForensicLogScreen when ready.",
                            classes="placeholder-body",
                        )
                    with Vertical(id="settings"):
                        yield Static("⚙️  Settings", classes="placeholder-title")
                        yield Static(
                            "Settings module placeholder.\n"
                            "Business hours, API keys, and theme options live here.",
                            classes="placeholder-body",
                        )

        with Container(id="audit-console"):
            yield Label("🪵  Audit Console", id="audit-label")
            yield RichLog(
                id="audit-log",
                auto_scroll=True,
                markup=True,
                wrap=True,
            )

        yield Footer()

    def on_mount(self) -> None:
        self._update_active_button(self._initial_tab)
        self._current_tab = self._initial_tab

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if not btn_id.startswith("nav-"):
            return
        target = btn_id[len("nav-"):]
        switcher = self.query_one("#content-switcher", ContentSwitcher)
        if target in switcher.children:
            switcher.current = target
            self._update_active_button(target)
            self._current_tab = target
            self.write_audit(f"Switched to [b]{event.button.label}[/b]")

    def _update_active_button(self, active_id: str) -> None:
        all_buttons = self.query(".nav-btn", Button)
        for btn in all_buttons:
            btn.remove_class("-active")
        target = self.query_one(f"#nav-{active_id}", Button) if active_id else None
        if target is not None:
            target.add_class("-active")

    def write_audit(self, message: str) -> None:
        """David: helper to append message to the audit console RichLog."""
        try:
            audit_log = self.query_one("#audit-log", RichLog)
        except Exception:
            return
        audit_log.write(message)