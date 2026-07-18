"""David: Master dashboard — sidebar navigation + content switcher + audit console."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, RichLog, ContentSwitcher, Static
from textual.containers import VerticalScroll, Horizontal, Vertical


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

    def compose(self) -> ComposeResult:
        # David: build Horizontal layout with sidebar (VerticalScroll of Buttons)
        # + main area (ContentSwitcher) + bottom RichLog
        pass

    def on_button_pressed(self, event: Button.Pressed):
        # David: map button id → content switcher target id
        pass

    def write_audit(self, message: str):
        """David: helper to append message to the audit console RichLog."""
        pass
