"""David: Master dashboard — sidebar navigation + screen switcher + audit console."""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Button,
    RichLog,
    Static,
    Label,
)
from textual.containers import VerticalScroll, Vertical, Container


SIDEBAR_BUTTONS = [
    ("dashboard", "Dashboard"),
    ("ingestion", "Ledger Ingestion"),
    ("forensic_log", "Forensic Log"),
    ("settings", "Settings"),
]


class DashboardScreen(Screen):
    """David: Main navigation hub.

    Layout:
      [Sidebar (width=24)]  |  [Main Content Pane]
      [  Dashboard      ]   |  Sidebar buttons either
      [  Ledger Ingest ]   |  show an embedded tab
      [  Forensic Log   ]   |  (dashboard/settings) or
      [  Settings       ]   |  switch_screen() to a
      [                              ]   full registered screen
      [  Audit Console (RichLog)     ]   (ingestion/forensic_log).

    Return nav: IngestionScreen / ForensicLogScreen each have a
    "Back to Dashboard" button that calls app.switch_screen("dashboard").
    """

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
                with Vertical(id="dashboard"):
                    yield Static("Audit Overview", classes="placeholder-title")
                    yield Static(
                        "Welcome to RootCFO. Use the sidebar to navigate.\n"
                        "• Ledger Ingestion — import CSV/JSON and run the pipeline\n"
                        "• Forensic Log   — review flagged anomalies\n"
                        "• Settings       — configure preferences",
                        classes="placeholder-body",
                    )
                with Vertical(id="settings"):
                    yield Static("Settings", classes="placeholder-title")
                    yield Static(
                        "Settings module placeholder.\n"
                        "Business hours, API keys, and theme options live here.",
                        classes="placeholder-body",
                    )

        with Container(id="audit-console"):
            yield Label("Audit Console", id="audit-label")
            yield RichLog(
                id="audit-log",
                auto_scroll=True,
                markup=True,
                wrap=True,
            )

        yield Footer()

    def on_mount(self) -> None:
        self._current_tab = self._initial_tab
        self._update_active_button(self._initial_tab)
        self._set_embedded_tab_visibility(self._initial_tab)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if not btn_id.startswith("nav-"):
            return
        target = btn_id[len("nav-"):]
        self._navigate_to(target, event.button.label)

    def _navigate_to(self, target: str, label_text: str) -> None:
        # Embedded tabs handled within this screen (keep audit console visible)
        if target in ("dashboard", "settings"):
            self._current_tab = target
            self._update_active_button(target)
            self._set_embedded_tab_visibility(target)
            self.write_audit(f"Switched to [b]{label_text}[/b]")
            return

        # Full registered screens: ingestion / forensic_log / any future ones.
        installed_screens = getattr(self.app, "SCREENS", {})
        if target not in installed_screens:
            self.notify(
                f"Screen '{target}' is not registered yet.",
                title="Not implemented",
                severity="warning",
            )
            return

        self._current_tab = target
        self._update_active_button(target)
        self.write_audit(f"Switched to [b]{label_text}[/b]")
        try:
            self.app.switch_screen(target)
        except Exception as e:
            self.notify(
                f"Could not open {label_text}: {e}",
                title="Navigation failed",
                severity="error",
            )

    def _set_embedded_tab_visibility(self, active_tab: str) -> None:
        """Show only the active embedded pane inside #content-pane."""
        for pane_id in ("dashboard", "settings"):
            try:
                pane = self.query_one(f"#{pane_id}", Vertical)
            except Exception:
                continue
            pane.display = (pane_id == active_tab)

    def _update_active_button(self, active_id: str) -> None:
        all_buttons = self.query(".nav-btn")
        for btn in all_buttons:
            btn.remove_class("-active")
        if not active_id:
            return
        try:
            target = self.query_one(f"#nav-{active_id}", Button)
        except Exception:
            return
        target.add_class("-active")

    def write_audit(self, message: str) -> None:
        """David: helper to append message to the audit console RichLog."""
        try:
            audit_log = self.query_one("#audit-log", RichLog)
        except Exception:
            return
        audit_log.write(message)