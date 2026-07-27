"""Juliana: File import pane — type the CSV/JSON path, then run the 7-step pipeline:

  1. FileParser.parse(filepath)           → list[Transaction]
  2. db.insert_transactions(company_id, transactions) → write rows, assign DB ids
  3. AnomalyDetector.analyze_all(txns, bh) → list[Anomaly]
  4. db.insert_anomalies(anomalies)       → write anomalies, assign DB ids
  5. ai.analyze_and_assign(anomalies, txns) → per-anomaly AI narrative
  6. db.update_anomaly_analyses(anomalies) → persist ai_analysis column
  7. Aggregate counts → status label + audit console

NOTE: All step progress and final summaries are routed through ``self.app._audit``
so they appear in the **dashboard's shared Audit Console** at the bottom of the
screen. There is no separate per-pane log — this avoids multiple consoles.
"""

from pathlib import Path
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Static,
)

from models.anomaly import Anomaly
from models.transaction import Transaction
from services.ai_forensic import AIForensic
from services.db import DatabaseError, DatabaseManager
from services.detector import AnomalyDetector
from services.parser import FileParser, ParserError


DEFAULT_BUSINESS_HOURS = "Mon-Fri 09:00-17:00"


def _resolve_company_id(app) -> Optional[int]:
    """Dict-or-attribute safe resolver (matches pattern from ForensicLogPane)."""
    user = getattr(app, "current_user", None)
    if user is None:
        return None
    if isinstance(user, dict):
        return user.get("company_id")
    return getattr(user, "company_id", None)


def _resolve_business_hours(app) -> str:
    """Try to read business hours from app state; fall back to DEFAULT."""
    settings = getattr(app, "settings", None)
    if isinstance(settings, dict):
        bh = settings.get("business_hours")
        if bh and isinstance(bh, str) and bh.strip():
            return bh.strip()
    start = getattr(app, "business_hours_start", None)
    end = getattr(app, "business_hours_end", None)
    if isinstance(start, str) and isinstance(end, str) and start and end:
        return f"Mon-Fri {start}-{end}"
    return DEFAULT_BUSINESS_HOURS


class IngestionPane(Vertical):
    """Reusable ingestion component — file path input + 7-step pipeline runner.

    All logs and step summaries go to the **shared dashboard audit console**
    via ``self.app._audit(...)``. There is no per-pane RichLog.
    """

    DEFAULT_CSS = """
    IngestionPane {
        height: 1fr;
        padding: 1 2;
    }
    IngestionPane #ingestion-title {
        text-style: bold;
        color: $primary;
        padding: 0 0 1 0;
    }
    IngestionPane #path-row {
        height: auto;
        margin-bottom: 1;
    }
    IngestionPane #file-path {
        width: 1fr;
    }
    IngestionPane #import-btn {
        margin-left: 1;
        min-width: 16;
    }
    IngestionPane #import-progress {
        width: 1fr;
        margin: 0 0 1 0;
    }
    IngestionPane #ingestion-status {
        padding: 0 1;
        color: $text-muted;
        min-height: 4;
    }
    IngestionPane #ingestion-notice {
        padding: 0 1;
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._detector = AnomalyDetector()

    # ── Compose ───────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Label("Ledger Ingestion", id="ingestion-title")
        yield Static(
            "Supported formats: .csv and .json."
            ""
            "",
            id="ingestion-notice",
        )
        with Horizontal(id="path-row"):
            yield Input(
                placeholder="e.g. C:\\Users\\MELLOW\\Downloads\\ledger.csv",
                id="file-path",
            )
            yield Button("Import", id="import-btn", variant="primary")
        yield ProgressBar(id="import-progress", total=100, show_eta=False)
        yield Static(
            "",
            id="ingestion-status",
        )

    def on_mount(self) -> None:
        try:
            self.query_one("#file-path", Input).focus()
        except Exception:
            pass

    # ── File input handlers ───────────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "import-btn":
            self._start_import_from_input()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "file-path":
            self._start_import_from_input()

    # ── Trigger helpers ───────────────────────────────────────────────
    def _start_import_from_input(self) -> None:
        path = self.query_one("#file-path", Input).value.strip()
        if not path:
            self.notify("Enter a file path first.", severity="error")
            return
        self._start_import(path)

    def _start_import(self, path: str) -> None:
        """Kick off the pipeline worker (runs off the UI thread)."""
        if getattr(self, "_import_worker_running", False):
            self.notify("An import is already running — please wait.",
                        severity="warning")
            return
        start_msg = f"Starting import of [b]{Path(path).name}[/b] ..."
        self._update_status(start_msg)
        self._update_progress(0)
        self._audit(start_msg, "info")
        self._run_pipeline(path)

    # ── Pipeline ──────────────────────────────────────────────────────
    @work(thread=True, exclusive=True)
    def _run_pipeline(self, filepath_str: str) -> None:
        """Full 7-step pipeline. Runs in a worker thread."""
        self._set_attr_thread("_import_worker_running", True)
        app = self.app
        db: Optional[DatabaseManager] = getattr(app, "db", None)
        ai: Optional[AIForensic] = getattr(app, "ai", None)

        counts = {
            "parsed": 0,
            "inserted_txns": 0,
            "anomalies": 0,
            "inserted_anomalies": 0,
            "ai_ok": None,
        }
        ok = False
        error_text: Optional[str] = None
        filepath = Path(filepath_str)

        try:
            # ── Guard: company context ─────────────────────────────
            company_id = _resolve_company_id(app)
            if company_id is None:
                raise RuntimeError(
                    "No company_id for current user. "
                    "Please re-authenticate via the sign-up/login screen."
                )
            if db is None:
                raise RuntimeError("Database is not connected.")

            bh = _resolve_business_hours(app)

            # ── Step 1: parse ─────────────────────────────────────
            self._audit_thread(f"[1/7] Parsing [b]{filepath.name}[/b] ...", "info")
            self._call_thread(self._update_progress, 5)
            transactions: list[Transaction] = FileParser.parse(
                str(filepath),
                company_id=company_id,
                source_file=filepath.name,
            )
            counts["parsed"] = len(transactions)
            self._call_thread(self._update_progress, 15)
            self._audit_thread(
                f"[1/7] Parsed [green]{counts['parsed']}[/green] transactions from {filepath.name}.",
                "info",
            )

            # ── Step 2: insert transactions → get DB ids ──────────
            self._audit_thread(
                "[2/7] Writing transactions to database ...",
                "info",
            )
            inserted_ids: list[int] = db.insert_transactions(company_id, transactions)
            counts["inserted_txns"] = len(inserted_ids)
            if len(inserted_ids) != len(transactions):
                self._audit_thread(
                    f"[yellow]Warning: DB returned {len(inserted_ids)} ids for "
                    f"{len(transactions)} parsed rows[/yellow]",
                    "warn",
                )
            for txn, new_id in zip(transactions, inserted_ids):
                if new_id:
                    txn.id = new_id
            self._call_thread(self._update_progress, 30)
            self._audit_thread(
                f"[2/7] Inserted [green]{counts['inserted_txns']}[/green] transactions.",
                "info",
            )

            # ── Step 3: detect anomalies ──────────────────────────
            self._audit_thread(
                f"[3/7] Running anomaly detection (business hours: {bh}) ...",
                "info",
            )
            anomalies: list[Anomaly] = self._detector.analyze_all(
                transactions, business_hours=bh
            )
            counts["anomalies"] = len(anomalies)
            self._call_thread(self._update_progress, 45)
            level = "info" if counts["anomalies"] == 0 else "warn"
            self._audit_thread(
                f"[3/7] Detected [yellow]{counts['anomalies']}[/yellow] anomalies.",
                level,
            )

            # ── Step 4: insert anomalies → get DB ids ────────────
            if counts["anomalies"] > 0:
                self._audit_thread(
                    "[4/7] Writing anomalies to database ...",
                    "info",
                )
                anomaly_ids = db.insert_anomalies(anomalies)
                counts["inserted_anomalies"] = len(anomaly_ids)
                for a, new_id in zip(anomalies, anomaly_ids):
                    if new_id:
                        a.id = new_id
                self._call_thread(self._update_progress, 55)
                self._audit_thread(
                    f"[4/7] Inserted [green]{counts['inserted_anomalies']}[/green] anomalies.",
                    "info",
                )
            else:
                self._call_thread(self._update_progress, 55)
                self._audit_thread(
                    "[4/7] No anomalies — nothing to insert.",
                    "info",
                )
                counts["inserted_anomalies"] = 0

            # ── Step 5 & 6: AI analyze + persist analyses ────────
            if counts["anomalies"] > 0:
                if ai is None:
                    for a in anomalies:
                        a.ai_analysis = (
                            "AI analysis skipped — AIForensic client not loaded."
                        )
                    counts["ai_ok"] = False
                    self._call_thread(self._update_progress, 90)
                    self._audit_thread(
                        "[5/7] AI not available — writing placeholder.",
                        "warn",
                    )
                else:
                    self._call_thread(self._update_progress, 60)
                    self._audit_thread(
                        "[5/7] Calling AI forensic analysis (this may take a few seconds) ...",
                        "info",
                    )
                    ai_ok, ai_summary = ai.analyze_and_assign(anomalies, transactions)
                    self._call_thread(self._update_progress, 90)
                    counts["ai_ok"] = ai_ok
                    if ai_ok:
                        self._audit_thread(
                            "[5/7] AI forensic analysis completed successfully.",
                            "info",
                        )
                    else:
                        self._audit_thread(
                            f"[5/7] [yellow]AI skipped: {ai_summary[:200]}[/yellow]",
                            "warn",
                        )
                self._audit_thread(
                    "[6/7] Persisting AI analyses to database ...",
                    "info",
                )
                db.update_anomaly_analyses(anomalies)
                self._call_thread(self._update_progress, 95)
                self._audit_thread("[6/7] Analyses persisted.", "info")
            else:
                self._audit_thread(
                    "[5/7] No anomalies — AI analysis skipped.",
                    "info",
                )
                self._audit_thread(
                    "[6/7] Nothing to persist.",
                    "info",
                )
                counts["ai_ok"] = True

            # ── Step 7: summary ──────────────────────────────────
            self._call_thread(self._update_progress, 100)
            ok = True

        except ParserError as e:
            error_text = f"Parse error: {e.message}"
            for re in getattr(e, "row_errors", []) or []:
                self._audit_thread(f"[red]• {re}[/red]", "crit")
            self._audit_thread(error_text, "crit")
        except DatabaseError as e:
            error_text = f"Database error: {e}"
            self._audit_thread(error_text, "crit")
        except Exception as e:  # last-resort safety net
            error_text = f"Unexpected error: {type(e).__name__}: {e}"
            self._audit_thread(error_text, "crit")

        finally:
            # Always emit step 7 summary + status update on UI thread
            summary = self._format_summary(counts, ok, error_text)
            level = "info" if ok else ("crit" if error_text else "warn")
            self._audit_thread("[7/7] " + summary, level)
            self._call_thread(self._update_status, summary)

            if ok:
                sev = "information" if counts["anomalies"] == 0 else "warning"
                self._call_thread(
                    self.notify,
                    f"Import complete. {counts['parsed']} txns, "
                    f"{counts['anomalies']} anomalies.",
                    severity=sev,
                )
                self._request_forensic_refresh()
                self._request_dashboard_refresh()
            else:
                self._call_thread(
                    self.notify,
                    f"Import failed. {error_text}",
                    severity="error",
                )
            self._set_attr_thread("_import_worker_running", False)

    # ── Helpers ───────────────────────────────────────────────────────
    def _format_summary(self, counts: dict, ok: bool, error: Optional[str]) -> str:
        parts = []
        if ok:
            parts.append("[green]✓ Import complete[/green]")
        else:
            parts.append(f"[red]✗ Import failed[/red]: {error}")
        parts.append(
            f"Parsed: {counts['parsed']} · "
            f"Txns inserted: {counts['inserted_txns']} · "
            f"Anomalies: {counts['anomalies']} · "
            f"Anomalies inserted: {counts['inserted_anomalies']}"
        )
        if counts["anomalies"] > 0:
            ai_status = "OK" if counts["ai_ok"] else "skipped"
            parts.append(f"AI analysis: {ai_status}")
        return "  ".join(parts)

    def _request_forensic_refresh(self) -> None:
        try:
            from screens.forensic_log import ForensicLogPane
        except Exception:
            return
        try:
            pane = self.app.query_one("#forensic_log", ForensicLogPane)
        except Exception:
            return
        try:
            pane.refresh_data()
        except Exception:
            pass

    def _request_dashboard_refresh(self) -> None:
        try:
            from screens.dashboard import DashboardPane
        except Exception:
            return
        try:
            pane = self.app.query_one("#dashboard", DashboardPane)
        except Exception:
            return
        try:
            pane.refresh_data()
        except Exception:
            pass

    # ── Cross-thread UI helpers ───────────────────────────────────────
    def _call_thread(self, fn, *args, **kwargs) -> None:
        try:
            self.app.call_from_thread(fn, *args, **kwargs)
        except Exception:
            pass

    def _set_attr_thread(self, name: str, value) -> None:
        self._call_thread(setattr, self, name, value)

    def _update_status(self, message: str) -> None:
        try:
            self.query_one("#ingestion-status", Static).update(message)
        except Exception:
            pass

    def _update_progress(self, value: float) -> None:
        try:
            self.query_one("#import-progress", ProgressBar).progress = value
        except Exception:
            pass

    def _audit(self, message: str, level: str = "info") -> None:
        """Route status/step messages to the shared dashboard audit console."""
        try:
            fn = getattr(self.app, "_audit", None)
            if callable(fn):
                fn(message, level=level)
                return
        except Exception:
            pass
        # Fallback: dashboard.write_audit if app._audit unavailable (old flow).
        try:
            active = getattr(self.app, "screen", None)
            writer = getattr(active, "write_audit", None)
            if callable(writer):
                writer(message)
        except Exception:
            pass

    def _audit_thread(self, message: str, level: str = "info") -> None:
        """Audit helper safe to call from worker thread."""
        self._call_thread(self._audit, message, level)


class IngestionScreen(Screen):
    """Thin standalone screen wrapper — embeds IngestionPane + Header/Footer.

    Kept for backwards compatibility: `push_screen("ingestion")` still works.
    The dashboard embeds ``IngestionPane`` directly in a ``ContentSwitcher``.
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield IngestionPane()
        yield Footer()
