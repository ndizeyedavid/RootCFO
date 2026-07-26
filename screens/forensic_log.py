"""Calvin: Color-coded anomaly table with clickable rows."""

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, Static

from services.db import DatabaseError

SEVERITY_STYLES = {
    "critical": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
}


def _sort_key(value):
    """Calvin: normalize a cell value for sorting.

    Text cells (used for the color-coded Severity column) are reduced to
    their plain string. Currency-formatted Amount cells ("$1,234.56") are
    parsed back to a float so they sort numerically instead of
    lexicographically. Everything else (Date is stored ISO-formatted, so
    it already sorts correctly as a string) is left as-is.
    """
    if isinstance(value, Text):
        value = value.plain
    if isinstance(value, str) and value.startswith("$"):
        try:
            return float(value.replace("$", "").replace(",", ""))
        except ValueError:
            pass
    return value


class ForensicLogPane(Vertical):
    """Calvin: Embeddable anomaly list. Shows all anomalies in sortable DataTable.

    Columns: Date, Description, Amount, Type, Severity
    Color coding: critical (red), warning (yellow), info (blue) — applied
    per-cell via rich.text.Text, since DataTable rows don't support CSS
    classes the way other widgets do.
    Click a row -> push ReportScreen with anomaly_id.

    Use: self.app.db.fetch_anomalies(company_id), self.app.db.fetch_transaction()
    """

    DEFAULT_CSS = """
    ForensicLogPane {
        height: 1fr;
    }

    ForensicLogPane #forensic-log-title {
        padding: 1 2 0 2;
        text-style: bold;
    }

    ForensicLogPane #anomaly-table {
        height: 1fr;
    }

    ForensicLogPane #empty-state {
        padding: 2;
        color: $text-muted;
        display: none;
    }

    ForensicLogPane #empty-state.-visible {
        display: block;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tracks ascending/descending toggle state per column for click-to-sort.
        self._sort_reverse: dict = {}

    def compose(self) -> ComposeResult:
        # Calvin: Title row + empty-state Label + sortable DataTable.
        with Horizontal():
            yield Label("Forensic Log", id="forensic-log-title")
        yield Label(
            "No anomalies found for this company. Ingest a ledger via Ledger Ingestion to populate.",
            id="empty-state",
        )
        yield DataTable(id="anomaly-table", cursor_type="row")

    def on_mount(self) -> None:
        # Calvin: add columns to DataTable, fetch anomalies from DB, populate rows with style classes
        table = self.query_one("#anomaly-table", DataTable)
        table.add_columns("Date", "Description", "Amount", "Type", "Severity")
        self._load_anomalies()

    @work(thread=True, exclusive=True)
    def _load_anomalies(self) -> None:
        """Calvin: fetch anomalies + related transactions off the UI thread.

        Runs in a worker thread since mysql-connector is a blocking client;
        this keeps the UI responsive while the query is in flight.
        """
        self.app.call_from_thread(setattr, self, "loading", True)

        db = self.app.db
        if db is None:
            self.app.call_from_thread(
                self.notify,
                "Database is not connected. Please try again shortly.",
                title="Connection error",
                severity="error",
            )
            self.app.call_from_thread(setattr, self, "loading", False)
            return

        company_id = self._resolve_company_id()
        if company_id is None:
            self.app.call_from_thread(
                self.notify,
                "No company is associated with the current session.",
                title="Missing company context",
                severity="warning",
            )
            self.app.call_from_thread(setattr, self, "loading", False)
            self.app.call_from_thread(self._show_empty_state, True)
            return

        try:
            anomalies = db.fetch_anomalies(company_id)
        except DatabaseError as exc:
            self.app.call_from_thread(
                self.notify,
                f"Could not load anomalies: {exc}",
                title="Database error",
                severity="error",
            )
            self.app.call_from_thread(setattr, self, "loading", False)
            return

        if not anomalies:
            self.app.call_from_thread(setattr, self, "loading", False)
            self.app.call_from_thread(self._show_empty_state, True)
            return

        # Fetch each anomaly's related transaction for Date/Amount.
        # NOTE: this is one query per anomaly (db.py has no batch-fetch-by-ids
        # method yet) -- fine for a demo dataset, but worth revisiting with a
        # fetch_transactions(ids=...) helper if the anomaly count grows large.
        rows = []
        for anomaly in anomalies:
            transaction = None
            transaction_id = anomaly.get("transaction_id")
            if transaction_id is not None:
                try:
                    transaction = db.fetch_transaction(transaction_id)
                except DatabaseError:
                    transaction = None
            rows.append((anomaly, transaction))

        self.app.call_from_thread(self._populate_table, rows)
        self.app.call_from_thread(setattr, self, "loading", False)

    def _resolve_company_id(self):
        """Calvin: resolve current company_id from app.current_user.

        Depends on Bruce's auth flow setting self.app.current_user to a
        User with a .company_id attribute. Returns None (triggering the
        empty state) if that isn't wired up yet, rather than crashing.
        """
        user = getattr(self.app, "current_user", None)
        if isinstance(user, dict):
            return user.get("company_id")
        return getattr(user, "company_id", None)

    def _populate_table(self, rows: list) -> None:
        """Calvin: clear + repopulate the DataTable (must run on the UI thread)."""
        table = self.query_one("#anomaly-table", DataTable)
        table.clear()
        self._show_empty_state(False)

        for anomaly, transaction in rows:
            date_value = transaction.get("date") if transaction else None
            amount_value = transaction.get("amount") if transaction else None
            description = anomaly.get("description") or "(no description)"
            anomaly_type = anomaly.get("anomaly_type") or "unknown"
            severity = (anomaly.get("severity") or "info").lower()

            date_text = date_value.isoformat() if hasattr(date_value, "isoformat") else "—"
            amount_text = f"${float(amount_value):,.2f}" if amount_value is not None else "—"

            style = SEVERITY_STYLES.get(severity, "")
            row = (
                Text(date_text, style=style),
                Text(description, style=style),
                Text(amount_text, style=style),
                Text(anomaly_type, style=style),
                Text(severity.capitalize(), style=style),
            )
            table.add_row(*row, key=str(anomaly.get("id")))

    def _show_empty_state(self, visible: bool) -> None:
        """Calvin: toggle the empty-state message and table visibility."""
        empty_label = self.query_one("#empty-state", Label)
        table = self.query_one("#anomaly-table", DataTable)
        empty_label.set_class(visible, "-visible")
        table.display = not visible

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Calvin: click a column header to sort by it, toggling asc/desc."""
        ascending = not self._sort_reverse.get(event.column_key, False)
        event.data_table.sort(event.column_key, key=_sort_key, reverse=not ascending)
        self._sort_reverse[event.column_key] = ascending

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # Calvin: extract anomaly_id from row key, push "report" screen with it
        anomaly_id_raw = event.row_key.value
        if anomaly_id_raw is None:
            return

        try:
            anomaly_id = int(anomaly_id_raw)
        except (TypeError, ValueError):
            return

        # Importing here (rather than at module level) avoids a circular
        # import, since report.py doesn't need to import this module back.
        from screens.report import ReportScreen

        self.app.push_screen(ReportScreen(anomaly_id=anomaly_id))


class ForensicLogScreen(Screen):
    """Calvin: Standalone screen wrapper around ForensicLogPane."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield ForensicLogPane()
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-dashboard":
            self.app.switch_screen("dashboard")
