"""Juliana: File import component (used inside dashboard) + standalone screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, RichLog, Static
from textual.containers import Vertical, Horizontal


class IngestionPane(Vertical):
    """Juliana: Embeddable ledger import component.

    Pipeline (stubbed in _handle_import):
      1. FileParser.parse(filepath) → list[Transaction]
      2. db.insert_transactions(company_id, transactions)
      3. AnomalyDetector.analyze_all(transactions, business_hours) → list[Anomaly]
      4. db.insert_anomalies(anomalies)
      5. AIForensic.analyze(anomalies, transactions) → narrative
      6. db.update_anomaly_analyses(anomalies)
      7. Show summary counts in status label

    Accesses: self.app.db, self.app.ai, self.app.current_user
    """

    DEFAULT_CSS = """
    IngestionPane {
        height: 1fr;
    }
    IngestionPane #ingestion-title {
        padding: 1 2 0 2;
        text-style: bold;
    }
    IngestionPane #ingestion-filepath,
    IngestionPane #ingestion-import {
        margin: 0 2;
    }
    IngestionPane #ingestion-status {
        margin: 1 2 0 2;
    }
    IngestionPane Label {
        margin: 1 2 0 2;
    }
    IngestionPane #ingestion-log {
        margin: 1 2;
        border: solid $primary;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Ledger Ingestion", id="ingestion-title")
        yield Label("File path to CSV/JSON ledger export:")
        yield Input(placeholder="/path/to/transactions.csv", id="ingestion-filepath")
        with Horizontal():
            yield Button("Import & Run Pipeline", id="ingestion-import", variant="primary")
        yield Static("", id="ingestion-status")
        yield Label("Import Log:")
        yield RichLog(id="ingestion-log", wrap=True, markup=True, auto_scroll=True)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "ingestion-import":
            self._handle_import()

    def _handle_import(self):
        filepath = self.query_one("#ingestion-filepath", Input).value.strip()
        status = self.query_one("#ingestion-status", Static)
        log = self.query_one("#ingestion-log", RichLog)
        if not filepath:
            self.notify("Enter a file path first.", severity="warning", title="Missing path")
            return
        status.update("")
        log.write(f"[b]Import requested:[/b] {filepath}")
        log.write("[i]Pipeline stub — 7-step flow: parse → insert txns → detect → insert anomalies → AI analyze → persist analysis → summarize[/i]")
        self.notify(
            "Ingestion pipeline logic in this component is a placeholder scaffold. "
            "Wire FileParser / AnomalyDetector / AIForensic calls here when ready.",
            title="Scaffold only",
            severity="information",
        )


class IngestionScreen(Screen):
    """Juliana: Standalone screen wrapper around IngestionPane."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield IngestionPane()
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-dashboard":
            self.app.switch_screen("dashboard")