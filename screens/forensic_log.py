"""Calvin: Color-coded anomaly table with clickable rows.

Two classes:

* ``ForensicLogPane(Vertical)`` — reusable, embeddable inside a ContentSwitcher
  on the dashboard. Expects to be mounted with ``ForensicLogPane(id="forensic_log")``.
* ``ForensicLogScreen(Screen)`` — thin standalone wrapper with Header/Footer kept
  for backwards compatibility (``push_screen("forensic_log")`` still works).
"""

from typing import Optional

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label

from services.db import DatabaseError

SEVERITY_STYLES = {
    "critical": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
}


def _sort_key(value):
    """Normalize a cell value for sorting.

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


def _resolve_company_id(app) -> Optional[int]:
    """Resolve current company_id from app.current_user.

    Handles both the dict-shape ``self.app.current_user`` set by the auth
    flow via ``set_current_user`` **and** a class-shape User instance so
    the pane works regardless of how the auth layer evolves.
    """
    user = getattr(app, "current_user", None)
    if user is None:
        return None
    if isinstance(user, dict):
        return user.get("company_id")
    return getattr(user, "company_id", None)


class ForensicLogPane(Vertical):
    """Calvin: Embeddable anomaly list — sortable DataTable + empty state.

    Mount on a dashboard ContentSwitcher as::

        ForensicLogPane(id="forensic_log")
    """

    DEFAULT_CSS = """
    ForensicLogPane {
        height: 1fr;
        padding: 1 2;
    }
    ForensicLogPane #forensic-log-title {
        text-style: bold;
        color: $primary;
        padding: 0 0 1 0;
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
        yield Label("Forensic Log", id="forensic-log-title")
        yield Label(
            "No anomalies found for this company. "
            "Ingest a ledger via Ledger Ingestion to populate.",
            id="empty-state",
        )
        yield DataTable(id="anomaly-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#anomaly-table", DataTable)
        table.add_columns("Date", "Description", "Amount", "Type", "Severity")
        self._load_anomalies()

    # ── Background worker ──────────────────────────────────────────────
    @work(thread=True, exclusive=True)
    def _load_anomalies(self) -> None:
        """Fetch anomalies + related transactions off the UI thread.

        mysql-connector is a blocking client; running this in a worker
        keeps the TUI responsive while the query is in flight.
        """
        self._call_thread(setattr, self, "loading", True)

        db = getattr(self.app, "db", None)
        if db is None:
            self._call_thread(
                self.notify,
                "Database is not connected. Please try again shortly.",
                title="Connection error",
                severity="error",
            )
            self._call_thread(setattr, self, "loading", False)
            return

        company_id = _resolve_company_id(self.app)
        if company_id is None:
            self._call_thread(
                self.notify,
                "No company is associated with the current session.",
                title="Missing company context",
                severity="warning",
            )
            self._call_thread(setattr, self, "loading", False)
            self._call_thread(self._show_empty_state, True)
            return

        try:
            anomalies = db.fetch_anomalies(company_id)
        except DatabaseError as exc:
            self._call_thread(
                self.notify,
                f"Could not load anomalies: {exc}",
                title="Database error",
                severity="error",
            )
            self._call_thread(setattr, self, "loading", False)
            return

        if not anomalies:
            self._call_thread(setattr, self, "loading", False)
            self._call_thread(self._show_empty_state, True)
            return

        # NOTE: one DB fetch per anomaly (N+1). db.py already has a comment
        # flagging this; add fetch_transactions(ids=...) later for scale.
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

        self._call_thread(self._populate_table, rows)
        self._call_thread(setattr, self, "loading", False)

    # ── UI rendering helpers (must run on the UI thread) ──────────────
    def _populate_table(self, rows: list) -> None:
        table = self.query_one("#anomaly-table", DataTable)
        table.clear()
        self._show_empty_state(False)

        for anomaly, transaction in rows:
            date_value = transaction.get("date") if transaction else None
            amount_value = transaction.get("amount") if transaction else None
            description = anomaly.get("description") or "(no description)"
            anomaly_type = anomaly.get("anomaly_type") or "unknown"
            severity = (anomaly.get("severity") or "info").lower()

            if hasattr(date_value, "isoformat"):
                date_text = date_value.isoformat()
            elif date_value is not None:
                date_text = str(date_value)
            else:
                date_text = "—"
            if amount_value is not None:
                try:
                    amount_text = f"${float(amount_value):,.2f}"
                except (TypeError, ValueError):
                    amount_text = str(amount_value)
            else:
                amount_text = "—"

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
        empty_label = self.query_one("#empty-state", Label)
        table = self.query_one("#anomaly-table", DataTable)
        empty_label.set_class(visible, "-visible")
        table.display = not visible

    def refresh_data(self) -> None:
        """Public helper: other screens (e.g. IngestionPane post-import)
        can call this to re-pull anomalies after new data lands."""
        self._load_anomalies()

    # ── Event handlers ─────────────────────────────────────────────────
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        ascending = not self._sort_reverse.get(event.column_key, False)
        event.data_table.sort(event.column_key, key=_sort_key, reverse=not ascending)
        self._sort_reverse[event.column_key] = ascending

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        anomaly_id_raw = event.row_key.value
        if anomaly_id_raw is None:
            return

        try:
            anomaly_id = int(anomaly_id_raw)
        except (TypeError, ValueError):
            return

        # Lazy import avoids circular dependency (report.py does not import us).
        from screens.report import ReportScreen

        self.app.push_screen(ReportScreen(anomaly_id=anomaly_id))

    # ── Cross-thread UI helper ─────────────────────────────────────────
    def _call_thread(self, fn, *args, **kwargs) -> None:
        try:
            self.app.call_from_thread(fn, *args, **kwargs)
        except Exception:
            pass


class ForensicLogScreen(Screen):
    """Calvin: Thin standalone screen wrapper — Header + ForensicLogPane + Footer.

    Kept for backwards compat (``push_screen("forensic_log")``). When the
    dashboard embeds ``ForensicLogPane`` directly this code path is not
    used, but it is harmless and gives a clean "fullscreen mode" escape
    hatch later if needed.
    """

    DEFAULT_CSS = """
    ForensicLogScreen .back-btn {
        dock: right;
        margin: 0 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pane: Optional[ForensicLogPane] = None

    def compose(self) -> ComposeResult:
        yield Header()
        self._pane = ForensicLogPane(id="forensic_log")
        yield self._pane
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: F821
        if event.button.id == "back-dashboard":
            self.app.switch_screen("dashboard")
