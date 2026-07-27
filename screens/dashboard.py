"""David: Master dashboard — sidebar navigation + content switcher + audit console.

The sidebar drives a ``ContentSwitcher(id="content-switcher")`` with four
real embedded panes (no screen switching, no placeholders):

  * #dashboard      -> overview Static (TODO handover §3.4: real summary cards)
  * #ingestion      -> IngestionPane(id="ingestion")
  * #forensic_log   -> ForensicLogPane(id="forensic_log")
  * #settings       -> SettingsPane(id="settings")

Textual 8.2.8 quirks fixed:
  * ``query()`` takes 1 arg only (the selector). Use ``query(selector)`` then
    ``isinstance`` checks. ``query_one(selector, Type)`` still takes 2 args.
  * DashboardScreen.__init__ forwards ``*args, **kwargs`` so Textual can pass
    ``id=``, ``name=``, ``classes=`` at mount time.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Label,
    RichLog,
    Static,
)
from textual.containers import Container, Vertical, VerticalScroll

from screens.forensic_log import ForensicLogPane
from screens.ingestion import IngestionPane
from screens.settings import SettingsPane

SIDEBAR_BUTTONS = [
    ("dashboard", "Dashboard"),
    ("ingestion", "Ledger Ingestion"),
    ("forensic_log", "Forensic Log"),
    ("settings", "Settings"),
]


class DashboardScreen(Screen):
    """David: Main navigation hub. Everything loads in the same screen.

<<<<<<< HEAD
    Layout::

      [Sidebar (w=24)]   |   [Main Content Pane]
      [  Dashboard     ]   |   ContentSwitcher shows different
      [  Ledger Ingest.]   |   views based on sidebar selection.
      [  Forensic Log  ]   |
      [  Settings      ]   |
      [                              ]
      [  Audit Console (RichLog)     ]
=======
    Layout:
      [Sidebar (width=24)]  |  [Content Switcher pane   ]
      [  Dashboard      ]   |    Dashboard / IngestionPane
      [  Ledger Ingest ]   |    / ForensicLogPane / SettingsPane
      [  Forensic Log   ]   |
      [  Settings       ]   |
      [                                    ]
      [  Audit Console (RichLog)           ]

    Sidebar clicks → switch ContentSwitcher.current → the correct pane
    shows in place, no screen push/switch, audit console stays visible.
>>>>>>> 13bd0c7c235305c2ef4d66cb0e66aecc4616b3be
    """

    def __init__(self, initial_tab: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                        yield Static("Audit Overview", classes="placeholder-title")
                        yield Static(
                            "Welcome to RootCFO. Use the sidebar to navigate.\n"
                            "• Ledger Ingestion — import CSV/JSON and run the pipeline\n"
                            "• Forensic Log   — review flagged anomalies\n"
                            "• Settings       — configure preferences",
                            classes="placeholder-body",
                        )
                    yield IngestionPane(id="ingestion")
                    yield ForensicLogPane(id="forensic_log")
                    yield SettingsPane(id="settings")

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

    # ── Navigation ────────────────────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if not btn_id.startswith("nav-"):
            return
        target = btn_id[len("nav-"):]
        self._navigate_to(target, event.button.label)

    def _navigate_to(self, target: str, label_text: str) -> None:
        switcher = self.query_one("#content-switcher", ContentSwitcher)
        # Validate target is a registered child id of the switcher.
        child_ids = {getattr(child, "id", None) for child in switcher.children}
        if target in child_ids:
            switcher.current = target
            self._update_active_button(target)
            self._current_tab = target
            self.write_audit(f"Switched to [b]{event.button.label}[/b]")

            # Post-switch side-effects: refresh data when user enters Forensic Log.
            if target == "forensic_log":
                try:
                    pane = self.query_one("#forensic_log", ForensicLogPane)
                    pane.refresh_data()
                except Exception:
                    pass

    def _update_active_button(self, active_id: str) -> None:
        # Textual 8.2.8: query() takes ONLY the selector string (1 arg).
        # query() returns a DOMQuery; iterate it and filter by isinstance.
        all_buttons = self.query(".nav-btn")
        for node in all_buttons:
            if isinstance(node, Button):
                node.remove_class("-active")
        if active_id:
            try:
                target = self.query_one(f"#nav-{active_id}", Button)
            except Exception:
                target = None
            if target is not None:
                target.add_class("-active")

    # ── Audit console helper ──────────────────────────────────────────
    def write_audit(self, message: str) -> None:
        """Append message to the bottom audit-console RichLog."""
        try:
            audit_log = self.query_one("#audit-log", RichLog)
        except Exception:
            return
        audit_log.write(message)
