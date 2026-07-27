import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label

from services.db import DatabaseError

SEVERITY_STYLES = {
    "critical": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
}


def _sort_key(value):
    if isinstance(value, Text):
        value = value.plain
    if isinstance(value, str) and value.startswith("RWF "):
        try:
            return float(value.replace("RWF ", "").replace(",", ""))
        except ValueError:
            pass
    return value


def _resolve_company_id(app) -> Optional[int]:
    user = getattr(app, "current_user", None)
    if user is None:
        return None
    if isinstance(user, dict):
        return user.get("company_id")
    return getattr(user, "company_id", None)


class ForensicLogPane(Vertical):

    DEFAULT_CSS = """
    ForensicLogPane {
        height: 1fr;
        padding: 1 2;
    }
    ForensicLogPane #forensic-header {
        height: auto;
        margin-bottom: 1;
    }
    ForensicLogPane #forensic-log-title {
        text-style: bold;
        color: $primary;
        width: 1fr;
    }
    ForensicLogPane #report-btn {
        width: 20;
    }
    ForensicLogPane #search-row {
        height: auto;
        margin-bottom: 1;
    }
    ForensicLogPane #search-input {
        width: 1fr;
    }
    ForensicLogPane #search-clear {
        width: 10;
        margin-left: 1;
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
        self._sort_reverse: dict = {}
        self._all_rows: list = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="forensic-header"):
            yield Label("Forensic Log", id="forensic-log-title")
            yield Button("Create Report", id="report-btn", variant="default")
        with Horizontal(id="search-row"):
            yield Input(placeholder="Search anomalies (use * as wildcard)...", id="search-input")
            yield Button("Clear", id="search-clear", variant="default")
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
        self._all_rows = rows
        self._apply_filter()

    def _apply_filter(self) -> None:
        inp = self.query_one("#search-input", Input)
        pattern = (inp.value or "").strip()
        table = self.query_one("#anomaly-table", DataTable)
        table.clear()
        self._show_empty_state(False)

        filtered = self._filter_rows(self._all_rows, pattern) if pattern else self._all_rows

        if not filtered:
            self._show_empty_state(True)
            return

        for anomaly, transaction in filtered:
            date_value = transaction.get("date") if transaction else None
            amount_value = transaction.get("amount") if transaction else None
            raw_desc = anomaly.get("description") or "(no description)"
            description = raw_desc[:55] + "..." if len(raw_desc) > 55 else raw_desc
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
                    amount_text = f"RWF {float(amount_value):,.2f}"
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

    def _filter_rows(self, rows: list, pattern: str) -> list:
        try:
            regex = re.compile(
                re.escape(pattern).replace(r"\*", ".*").replace(r"\?", "."),
                re.IGNORECASE,
            )
        except re.error:
            return rows

        def _search_text(anomaly: dict, transaction: dict | None) -> str:
            parts = [
                str(anomaly.get("description", "")),
                str(anomaly.get("anomaly_type", "")),
                str(anomaly.get("severity", "")),
            ]
            if transaction:
                parts.extend([
                    str(transaction.get("description", "")),
                    str(transaction.get("person", "")),
                    str(transaction.get("account", "")),
                ])
            return " ".join(parts)

        return [(a, t) for a, t in rows if regex.search(_search_text(a, t))]

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._apply_filter()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._apply_filter()

    def refresh_data(self) -> None:
        self._load_anomalies()

    @work(thread=True, exclusive=True)
    def _generate_report(self) -> None:
        self._audit_thread("Generating anomaly report ...", "info")

        db = getattr(self.app, "db", None)
        if db is None:
            self._call_thread(self.notify, "Database not connected.", severity="error")
            return

        company_id = _resolve_company_id(self.app)
        if company_id is None:
            self._call_thread(self.notify, "No company context.", severity="warning")
            return

        try:
            anomalies = db.fetch_anomalies(company_id)
        except DatabaseError as exc:
            self._audit_thread(f"Database error during report: {exc}", "crit")
            self._call_thread(self.notify, f"Database error: {exc}", severity="error")
            return

        if not anomalies:
            self._audit_thread("No anomalies found — nothing to export.", "warn")
            self._call_thread(self.notify, "No anomalies to export.", severity="warning")
            return

        self._audit_thread(f"Fetched [yellow]{len(anomalies)}[/yellow] anomalies, enriching with transaction data ...", "info")

        rows = []
        for i, anomaly in enumerate(anomalies):
            transaction = None
            transaction_id = anomaly.get("transaction_id")
            if transaction_id is not None:
                try:
                    transaction = db.fetch_transaction(transaction_id)
                except DatabaseError:
                    transaction = None

            person = (transaction or {}).get("person") or ""
            txn_date = transaction.get("date") if transaction else ""
            if hasattr(txn_date, "isoformat"):
                txn_date = txn_date.isoformat()
            txn_desc = (transaction or {}).get("description") or ""
            amount = (transaction or {}).get("amount") or ""
            if amount:
                try:
                    amount = f"RWF {float(amount):,.2f}"
                except (TypeError, ValueError):
                    pass

            rows.append({
                "Anomaly ID": anomaly.get("id"),
                "Anomaly Type": anomaly.get("anomaly_type", ""),
                "Severity": anomaly.get("severity", ""),
                "Anomaly Description": anomaly.get("description", ""),
                "Transaction ID": transaction_id,
                "Transaction Date": txn_date,
                "Transaction Description": txn_desc,
                "Amount": amount,
                "Person": person,
                "AI Analysis": anomaly.get("ai_analysis") or "",
            })

            if (i + 1) % 25 == 0 or i == len(anomalies) - 1:
                self._audit_thread(f"  Enriched {i + 1}/{len(anomalies)} anomalies ...", "info")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(f"anomaly_report_{ts}.csv")
        self._audit_thread(f"Writing CSV with [green]{len(rows)}[/green] rows to [b]{path.name}[/b] ...", "info")
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            self._audit_thread(f"Failed to write CSV: {exc}", "crit")
            self._call_thread(self.notify, f"Could not write CSV: {exc}", severity="error")
            return

        self._audit_thread(
            f"Report exported: [green]{path.resolve()}[/green] "
            f"({len(rows)} rows, {len(anomalies)} anomalies).",
            "info",
        )
        self._call_thread(
            self.notify,
            f"Report saved to [bold]{path.name}[/bold]",
            severity="information",
            title="Export complete",
        )

    # ── Event handlers ─────────────────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "report-btn":
            self._generate_report()
        elif event.button.id == "search-clear":
            inp = self.query_one("#search-input", Input)
            inp.value = ""
            self._apply_filter()

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

    # ── Cross-thread UI helpers ─────────────────────────────────────────
    def _call_thread(self, fn, *args, **kwargs) -> None:
        try:
            self.app.call_from_thread(fn, *args, **kwargs)
        except Exception:
            pass

    def _audit(self, message: str, level: str = "info") -> None:
        try:
            fn = getattr(self.app, "_audit", None)
            if callable(fn):
                fn(message, level=level)
                return
        except Exception:
            pass
        try:
            active = getattr(self.app, "screen", None)
            writer = getattr(active, "write_audit", None)
            if callable(writer):
                writer(message)
        except Exception:
            pass

    def _audit_thread(self, message: str, level: str = "info") -> None:
        self._call_thread(self._audit, message, level)


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
