"""Calvin: AI forensic report viewer with follow-up chat."""

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, MarkdownViewer, RichLog

from models.anomaly import Anomaly
from models.transaction import Transaction
from services.ai_forensic import APIError
from services.db import DatabaseError

PLACEHOLDER_REPORT = "*Loading forensic report...*"


class ReportScreen(Screen):
    """Calvin: Shows AI analysis + allows follow-up questions.

    Receives anomaly_id when pushed. The correct way to push this screen
    (verified against Textual 8.2.8's push_screen signature, which treats
    a second positional arg as a dismiss callback, not a constructor arg)
    is to push a new instance directly:

        self.app.push_screen(ReportScreen(anomaly_id=some_id))

    - Load anomaly from DB
    - Display AI analysis in MarkdownViewer
    - Chat bar at bottom: Input + Ask button -> calls AIForensic.chat()

    Use: self.app.db.fetch_anomaly(), self.app.db.fetch_transaction(), self.app.ai.chat()
    """

    DEFAULT_CSS = """
    ReportScreen #report-title {
        padding: 1 2 0 2;
        text-style: bold;
    }

    ReportScreen #report-viewer {
        height: 1fr;
        border: solid $accent;
        margin: 1 2;
    }

    ReportScreen #chat-log {
        height: 10;
        margin: 0 2;
        border: solid $primary;
    }

    ReportScreen #chat-bar {
        height: 3;
        margin: 1 2;
    }

    ReportScreen #chat-input {
        width: 1fr;
    }

    ReportScreen #ask-button {
        width: auto;
        margin-left: 1;
    }
    """

    def __init__(self, anomaly_id: int = None):
        super().__init__()
        self.anomaly_id = anomaly_id
        self.chat_history = []  # list[dict]; seeded with a system prompt once the report loads

    def compose(self) -> ComposeResult:
        # Calvin: MarkdownViewer (report) + RichLog (chat) + Input + Button (ask)
        yield Header()
        with Vertical():
            yield Label("Forensic Report", id="report-title")
            yield MarkdownViewer(
                PLACEHOLDER_REPORT,
                id="report-viewer",
                show_table_of_contents=False,
            )
            yield RichLog(id="chat-log", wrap=True, markup=True)
            with Horizontal(id="chat-bar"):
                yield Input(
                    placeholder="Ask a follow-up question about this report...",
                    id="chat-input",
                )
                yield Button("Ask", id="ask-button", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        # Calvin: load anomaly from DB, display AI analysis, or run AI if not yet analyzed
        self._load_report()

    @work(thread=True, exclusive=True)
    def _load_report(self) -> None:
        """Calvin: fetch anomaly + transaction, get/generate AI analysis.

        Runs in a worker thread since both mysql-connector and the Groq
        client are blocking; this keeps the UI responsive while either
        call is in flight.
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

        if self.anomaly_id is None:
            self.app.call_from_thread(
                self.notify,
                "No anomaly was specified for this report.",
                title="Missing anomaly",
                severity="warning",
            )
            self.app.call_from_thread(setattr, self, "loading", False)
            return

        try:
            anomaly_row = db.fetch_anomaly(self.anomaly_id)
        except DatabaseError as exc:
            self.app.call_from_thread(
                self.notify,
                f"Could not load this anomaly: {exc}",
                title="Database error",
                severity="error",
            )
            self.app.call_from_thread(setattr, self, "loading", False)
            return

        if anomaly_row is None:
            self.app.call_from_thread(
                self.notify,
                f"Anomaly #{self.anomaly_id} was not found.",
                title="Not found",
                severity="error",
            )
            self.app.call_from_thread(setattr, self, "loading", False)
            return

        anomaly = Anomaly(**anomaly_row)

        transaction = None
        transaction_row = None
        if anomaly.transaction_id is not None:
            try:
                transaction_row = db.fetch_transaction(anomaly.transaction_id)
            except DatabaseError:
                transaction_row = None
            if transaction_row is not None:
                # NOTE: the transactions table currently has no `category` or
                # `timestamp` column (see Schema.sql), so from_csv_row falls
                # back to sensible defaults ("other" category, midnight
                # timestamp) for those two fields rather than inventing data.
                transaction = Transaction.from_csv_row(
                    transaction_row,
                    company_id=transaction_row.get("company_id"),
                    source_file=transaction_row.get("source_file"),
                )

        analysis_text = anomaly.ai_analysis

        if not analysis_text:
            ai = self.app.ai
            if ai is None:
                analysis_text = (
                    "*AI analysis is unavailable right now (AI service not "
                    "initialized). Showing raw anomaly details instead.*\n\n"
                    f"- **Type:** {anomaly.anomaly_type}\n"
                    f"- **Severity:** {anomaly.severity}\n"
                    f"- **Description:** {anomaly.description}"
                )
            else:
                try:
                    analysis_text = ai.analyze(
                        [anomaly],
                        [transaction] if transaction else [],
                    )
                except APIError as exc:
                    analysis_text = (
                        f"*AI analysis failed: {exc}*\n\n"
                        f"- **Type:** {anomaly.anomaly_type}\n"
                        f"- **Severity:** {anomaly.severity}\n"
                        f"- **Description:** {anomaly.description}"
                    )
                else:
                    try:
                        db.update_anomaly_analysis(anomaly.id, analysis_text)
                    except DatabaseError:
                        # Non-fatal: the report still displays even if the
                        # cache-write fails, it'll just be regenerated next visit.
                        pass

        self.app.call_from_thread(self._display_report, anomaly, analysis_text)
        self.app.call_from_thread(setattr, self, "loading", False)

    def _display_report(self, anomaly: Anomaly, analysis_text: str) -> None:
        """Calvin: push analysis into the MarkdownViewer and seed chat context."""
        viewer = self.query_one("#report-viewer", MarkdownViewer)
        viewer.document.update(analysis_text)

        # Seed the chat's system context so follow-up questions know which
        # anomaly/report they're about, per AIForensic.chat()'s contract that
        # the caller supplies any system prompt.
        self.chat_history = [
            {
                "role": "system",
                "content": (
                    "You are continuing a forensic accounting conversation about "
                    f"anomaly #{anomaly.id} (type: {anomaly.anomaly_type}, "
                    f"severity: {anomaly.severity}). The original report you "
                    f"produced was:\n\n{analysis_text}\n\n"
                    "Answer the auditor's follow-up questions concisely, "
                    "grounded in the report above."
                ),
            }
        ]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Calvin: route to _handle_chat
        if event.button.id == "ask-button":
            self._handle_chat()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Calvin: also allow pressing Enter in the input to ask, not just the button."""
        if event.input.id == "chat-input":
            self._handle_chat()

    def _handle_chat(self) -> None:
        # Calvin: get question from Input -> call self.app.ai.chat() -> show response in RichLog
        input_widget = self.query_one("#chat-input", Input)
        question = input_widget.value.strip()
        if not question:
            return

        input_widget.value = ""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[b]You:[/b] {question}")

        self._ask_ai(question)

    @work(thread=True, exclusive=True)
    def _ask_ai(self, question: str) -> None:
        """Calvin: send the question to Groq off the UI thread, then show the reply."""
        ai = self.app.ai
        if ai is None:
            self.app.call_from_thread(
                self.notify,
                "AI service is not available right now.",
                title="AI unavailable",
                severity="error",
            )
            return

        try:
            reply = ai.chat(self.chat_history, question)
        except APIError as exc:
            self.app.call_from_thread(
                self.notify,
                f"AI request failed: {exc}",
                title="AI error",
                severity="error",
            )
            return

        if not reply:
            reply = "*(The AI returned an empty response. Try rephrasing your question.)*"

        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": reply})

        self.app.call_from_thread(self._append_chat_reply, reply)

    def _append_chat_reply(self, reply: str) -> None:
        """Calvin: write the AI's reply into the RichLog (must run on the UI thread)."""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[b]AI:[/b] {reply}")
