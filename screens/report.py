"""Calvin: AI forensic report + follow-up chat.

Redesigned 2026-07-27 v3 — opencode-style chat interface.
"""

from functools import partial
from pathlib import Path
from typing import Optional

from rich.markdown import Markdown
from rich.markup import escape as rich_escape

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label, RichLog, Static

from models.anomaly import Anomaly
from models.transaction import Transaction
from services.ai_forensic import AIForensic, APIError
from services.db import DatabaseError, DatabaseManager


_SYSTEM_CHAT_INTRO = (
    "You are continuing a forensic accounting conversation about a specific flagged "
    "anomaly. Answer the auditor's follow-up questions concisely, grounded in the "
    "original forensic report above. Do not invent data that was not provided."
)


def _fmt_amount(v) -> str:
    try:
        return f"RWF {float(v or 0):,.2f}"
    except (TypeError, ValueError):
        return str(v) if v is not None else "\u2014"


def _fmt_date(v) -> str:
    if v is None:
        return "\u2014"
    if hasattr(v, "isoformat"):
        return str(v.isoformat())
    return str(v)


def _sev_class(sev: str) -> str:
    s = (sev or "info").lower()
    if s in {"warning", "warn", "medium"}:
        return "warning"
    if s in {"error", "critical", "high", "crit", "fatal"}:
        return "critical"
    return "info"


_SEP = "\u2500" * 60


class ReportPane(Vertical):
    """Embeddable chat-style forensic report pane."""

    DEFAULT_CSS = """
    ReportPane {
        height: 1fr;
        background: $panel;
    }

    /* HEADER BAR */
    ReportPane > #nav-bar {
        dock: top;
        height: 3;
        padding: 0 1;
        background: $boost;
        border-bottom: solid $accent;
    }
    ReportPane > #nav-bar > #back-btn {
        width: 24;
        height: 3;
    }
    ReportPane > #nav-bar > #title-wrap {
        width: 1fr;
        height: 3;
        align: center middle;
    }
    ReportPane > #nav-bar > #title-wrap > #report-title {
        text-style: bold;
        text-align: center;
        color: $text;
    }
    ReportPane > #nav-bar > #severity-pill {
        width: 14;
        height: 3;
        text-align: center;
        content-align: center middle;
        padding: 0 1;
    }
    ReportPane > #nav-bar > #severity-pill.info {
        color: $success;
    }
    ReportPane > #nav-bar > #severity-pill.warning {
        color: $warning;
    }
    ReportPane > #nav-bar > #severity-pill.critical {
        color: $error;
    }

    /* CHAT AREA */
    ReportPane > #chat {
        height: 1fr;
        background: $surface;
        padding: 1 2;
    }

    /* COMPOSER */
    ReportPane > #composer {
        dock: bottom;
        height: 3;
        padding: 0 1;
        background: $boost;
        border-top: solid $accent;
    }
    ReportPane > #composer > #chat-input {
        width: 1fr;
        height: 3;
    }
    ReportPane > #composer > #ask-btn {
        width: 12;
        height: 3;
        margin-left: 1;
    }
    """

    def __init__(self, anomaly_id: Optional[int] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anomaly_id: Optional[int] = anomaly_id
        self.chat_history: list[dict] = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="nav-bar"):
            yield Button("\u2039 Back to Forensic Log", id="back-btn", variant="default")
            with Vertical(id="title-wrap"):
                yield Label(self._title_text(), id="report-title")
            yield Static("INFO", id="severity-pill")

        yield RichLog(id="chat", wrap=True, markup=True, auto_scroll=True)

        with Horizontal(id="composer"):
            yield Input(
                placeholder="Ask a follow-up question about this anomaly\u2026",
                id="chat-input",
            )
            yield Button("Ask", id="ask-btn", variant="primary")

    def _title_text(self) -> str:
        if self.anomaly_id is None:
            return "Forensic Report"
        return f"Forensic Report \u00b7 Anomaly #{self.anomaly_id}"

    def on_mount(self) -> None:
        try:
            self.query_one("#chat-input", Input).focus()
        except Exception:
            pass
        self._load_report()

    # Nav events
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self._go_back()
        elif event.button.id == "ask-btn":
            self._send_user_question()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            self._send_user_question()

    def _go_back(self) -> None:
        try:
            self.app.pop_screen()
            return
        except Exception:
            pass
        try:
            from screens.dashboard import DashboardScreen
            scr = getattr(self.app, "screen", None)
            if isinstance(scr, DashboardScreen):
                scr.switch_pane("forensic_log")
        except Exception:
            pass

    # Initial load (threaded)
    @work(thread=True, exclusive=True)
    def _load_report(self) -> None:
        app = self.app
        db: Optional[DatabaseManager] = getattr(app, "db", None)
        ai: Optional[AIForensic] = getattr(app, "ai", None)

        if db is None:
            self._ui(self.notify,
                     "Database is not connected. Please try again shortly.",
                     title="Connection error", severity="error")
            return

        if self.anomaly_id is None:
            self._ui(self.notify, "No anomaly was specified for this report.",
                     title="Missing anomaly", severity="warning")
            self._ui(self._write_assistant,
                     "*No anomaly specified \u2014 open this page from the Forensic Log table.*")
            return

        try:
            anomaly_row = db.fetch_anomaly(self.anomaly_id)
        except DatabaseError as exc:
            self._ui(self.notify, f"Could not load this anomaly: {exc}",
                     title="Database error", severity="error")
            return
        if anomaly_row is None:
            self._ui(self.notify, f"Anomaly #{self.anomaly_id} was not found.",
                     title="Not found", severity="error")
            self._ui(self._write_assistant,
                     f"*Anomaly #{self.anomaly_id} does not exist.*")
            return

        anomaly = Anomaly(**anomaly_row)

        transaction: Optional[Transaction] = None
        tx_row = None
        if anomaly.transaction_id is not None:
            try:
                tx_row = db.fetch_transaction(anomaly.transaction_id)
            except DatabaseError:
                tx_row = None
            if tx_row:
                try:
                    transaction = Transaction.from_csv_row(
                        tx_row,
                        company_id=tx_row.get("company_id"),
                        source_file=tx_row.get("source_file"),
                    )
                except Exception:
                    try:
                        tid = tx_row.get("id")
                        transaction = Transaction(
                            id=tid if tid is not None else anomaly.transaction_id,
                            company_id=tx_row.get("company_id") or 0,
                            date=tx_row.get("date"),
                            timestamp=tx_row.get("timestamp"),
                            category=tx_row.get("category") or "",
                            description=tx_row.get("description") or "",
                            amount=float(tx_row.get("amount") or 0.0),
                            account=tx_row.get("account") or "",
                            person=tx_row.get("person") or "",
                            source_file=tx_row.get("source_file") or "",
                        )
                    except Exception:
                        transaction = None

        self._ui(self._render_metadata, anomaly, transaction)

        analysis_text = anomaly.ai_analysis
        generated_now = False
        if not analysis_text:
            if ai is None:
                analysis_text = self._raw_details_fallback(
                    anomaly, transaction,
                    reason="AI analysis unavailable (service not initialized).")
            else:
                try:
                    analysis_text = ai.analyze(
                        [anomaly], [transaction] if transaction else [])
                    generated_now = True
                except APIError as exc:
                    analysis_text = self._raw_details_fallback(
                        anomaly, transaction,
                        reason=f"AI analysis failed: {exc}")
                else:
                    try:
                        db.update_anomaly_analysis(anomaly.id, analysis_text)
                    except DatabaseError:
                        pass

        self._ui(self._display_initial_report,
                 anomaly, transaction, analysis_text, generated_now)

    # UI helpers
    def _render_metadata(self, anomaly: Anomaly,
                         transaction: Optional[Transaction]) -> None:
        sev = _sev_class(anomaly.severity or "info")
        try:
            pill = self.query_one("#severity-pill", Static)
            pill.update(sev.upper())
            pill.set_classes(sev)
        except Exception:
            pass

    def _display_initial_report(self, anomaly: Anomaly,
                                transaction: Optional[Transaction],
                                analysis_text: str,
                                generated_now: bool) -> None:
        ctx: list[str] = [
            f"Anomaly #{getattr(anomaly, 'id', '?')} \u00b7 {anomaly.anomaly_type or 'unknown'} \u00b7 {anomaly.severity or 'info'}",
            f"Flagged at: {_fmt_date(getattr(anomaly, 'flagged_at', None))}",
        ]
        if anomaly.description:
            ctx.append(f"Description: {anomaly.description}")
        if transaction:
            ctx.append("")
            ctx.append(f"Related Transaction #{getattr(transaction, 'id', '?')}:")
            ctx.append(
                f"  Date: {_fmt_date(getattr(transaction, 'date', None))}  \u00b7  "
                f"Amount: {_fmt_amount(getattr(transaction, 'amount', None))}"
            )
            _em = "\u2014"
            ctx.append(
                f"  Account: {getattr(transaction, 'account', _em) or _em}  \u00b7  "
                f"Person: {getattr(transaction, 'person', _em) or _em}"
            )
            src = getattr(transaction, "source_file", None)
            if src:
                ctx.append(f"  Source: {Path(src).name}")
            txdesc = getattr(transaction, "description", None)
            if txdesc:
                ctx.append(f"  Description: {txdesc}")

        ctx.append("")
        _live = "\u26a1 Generated live"
        _cached = "\U0001f4e6 Cached from DB"
        ctx.append(f"Status: {_live if generated_now else _cached}")

        preamble = "\n".join(ctx)
        body = f"{preamble}\n\n{analysis_text or '*No analysis text available.*'}"

        self._write_assistant(body)

        self.chat_history = [
            {
                "role": "system",
                "content": (
                    f"{_SYSTEM_CHAT_INTRO}\n\n"
                    f"Anomaly id: {getattr(anomaly, 'id', '?')}\n"
                    f"Anomaly type: {anomaly.anomaly_type}\n"
                    f"Severity: {anomaly.severity}\n"
                    f"Description: {anomaly.description}\n"
                    f"\nOriginal forensic report produced above:\n\n"
                    f"{analysis_text or ''}\n"
                ),
            }
        ]

    @staticmethod
    def _raw_details_fallback(anomaly: Anomaly,
                              transaction: Optional[Transaction],
                              reason: str) -> str:
        _em = "\u2014"
        p = [f"* {reason} * Showing raw anomaly details instead.", "",
             "-- Anomaly --",
             f"Type: {anomaly.anomaly_type}",
             f"Severity: {anomaly.severity}",
             f"Description: {anomaly.description or _em}",
             f"Flagged at: {_fmt_date(getattr(anomaly, 'flagged_at', None))}"]
        if transaction is not None:
            p.extend(["", "-- Related transaction --",
                      f"Txn #.: {getattr(transaction, 'id', '?')}",
                      f"Date: {_fmt_date(getattr(transaction, 'date', None))}",
                      f"Amount: {_fmt_amount(getattr(transaction, 'amount', None))}",
                      f"Account: {getattr(transaction, 'account', _em) or _em}",
                      f"Person: {getattr(transaction, 'person', _em) or _em}",
                      f"Description: {getattr(transaction, 'description', _em) or _em}"])
        return "\n".join(p)

    # Chat: compose + send
    def _send_user_question(self) -> None:
        inp = self.query_one("#chat-input", Input)
        q = (inp.value or "").strip()
        if not q:
            return
        inp.value = ""
        self._write_user(q)
        self._ask_ai(q)

    @work(thread=True, exclusive=True)
    def _ask_ai(self, question: str) -> None:
        ai: Optional[AIForensic] = getattr(self.app, "ai", None)
        if ai is None:
            self._ui(self._write_assistant,
                     "*AI service is unavailable right now. Check GROQ_API_KEY in `.env`.*")
            return
        try:
            reply = ai.chat(self.chat_history, question)
        except APIError as exc:
            self._ui(self.notify, f"AI request failed: {exc}",
                     title="AI error", severity="error")
            return
        if not reply:
            reply = "*(The AI returned an empty response. Try rephrasing your question.)*"
        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": reply})
        self._ui(self._write_assistant, reply)

    # Transcript writers (opencode-style)
    def _write_user(self, text: str) -> None:
        chat = self._chat_ref()
        if chat is None:
            return
        chat.write(f"\n{_SEP}\nYou\n{rich_escape(text)}\n")

    def _write_assistant(self, text: str) -> None:
        chat = self._chat_ref()
        if chat is None:
            return
        text = text or "\u2026"
        chat.write(f"\n{_SEP}\nAI Forensic\n")
        self.app.set_timer(0.08, partial(self._stream_md, chat, text))

    def _stream_md(self, chat: RichLog, text: str) -> None:
        try:
            chat.write(Markdown(text))
        except Exception:
            chat.write(rich_escape(text))
        chat.write("\n")

    def _chat_ref(self) -> Optional[RichLog]:
        try:
            return self.query_one("#chat", RichLog)
        except Exception:
            return None

    # Cross-thread marshal
    def _ui(self, fn, *args, **kwargs) -> None:
        try:
            self.app.call_from_thread(fn, *args, **kwargs)
        except Exception:
            pass


class ReportScreen(Screen):
    def __init__(self, anomaly_id: Optional[int] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pane = ReportPane(anomaly_id=anomaly_id, id="report_pane")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self._pane
