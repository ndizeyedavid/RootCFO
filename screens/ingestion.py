"""Juliana: File import screen — upload CSV/JSON, run full pipeline."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, RichLog, Static
from textual.containers import Vertical, Horizontal


class IngestionScreen(Screen):
    """Juliana: User provides file path, clicks Import.

    Pipeline (all in _handle_import):
      1. FileParser.parse(filepath) → list[Transaction]
      2. db.insert_transactions(company_id, transactions)
      3. AnomalyDetector.analyze_all(transactions, business_hours) → list[Anomaly]
      4. db.insert_anomalies(anomalies)
      5. AIForensic.analyze(anomalies, transactions) → narrative
      6. db.update_anomaly_analyses(anomalies)
      7. Show summary counts in status label

    Use: self.app.db, self.app.ai, self.app.current_user
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal():
                yield Button("← Back to Dashboard", id="back-dashboard", variant="default")
            # Juliana: file path Input + Import Button + status Static + log RichLog
            yield Label("Ledger Ingestion", classes="placeholder-title")
            yield Label("File path to CSV/JSON ledger export:")
            yield Input(placeholder="/path/to/transactions.csv", id="ingestion-filepath")
            with Horizontal():
                yield Button("Import & Run Pipeline", id="ingestion-import", variant="primary")
            yield Static("", id="ingestion-status")
            yield Label("Import Log:")
            yield RichLog(id="ingestion-log", wrap=True, markup=True, auto_scroll=True)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id or ""
        if bid == "back-dashboard":
            self.app.switch_screen("dashboard")
            return
        if bid == "ingestion-import":
            self._handle_import()

    def _handle_import(self):
        # Juliana: implement the full 7-step pipeline
        # Wrap everything in try/except
        # Log each step to RichLog
        # Show final summary in status label
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
            "Ingestion pipeline logic in this screen is a placeholder scaffold. "
            "Wire FileParser / AnomalyDetector / AIForensic calls here when ready.",
            title="Scaffold only",
            severity="information",
        )