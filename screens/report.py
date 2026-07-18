"""Calvin: AI forensic report viewer with follow-up chat."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, MarkdownViewer, Input, Button, RichLog, Label
from textual.containers import Vertical, Horizontal


class ReportScreen(Screen):
    """Calvin: Shows AI analysis + allows follow-up questions.

    Receives anomaly_id when pushed (passed via app.push_screen("report", anomaly_id)).
    - Load anomaly from DB
    - Display AI analysis in MarkdownViewer
    - Chat bar at bottom: Input + Ask button → calls AIForensic.chat()

    Use: self.app.db.fetch_anomaly(), self.app.db.fetch_transaction(), self.app.ai.chat()
    """

    def __init__(self, anomaly_id: int = None):
        super().__init__()
        self.anomaly_id = anomaly_id
        self.chat_history = []

    def compose(self) -> ComposeResult:
        # Calvin: MarkdownViewer (report) + RichLog (chat) + Input + Button (ask)
        pass

    def on_mount(self):
        # Calvin: load anomaly from DB, display AI analysis, or run AI if not yet analyzed
        pass

    def on_button_pressed(self, event: Button.Pressed):
        # Calvin: route to _handle_chat
        pass

    def _handle_chat(self):
        # Calvin: get question from Input → call self.app.ai.chat() → show response in RichLog
        pass

    def _load_report(self):
        # Calvin: fetch anomaly from DB, display ai_analysis in MarkdownViewer
        pass
