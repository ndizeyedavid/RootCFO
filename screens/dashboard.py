from collections import Counter
from functools import partial
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    DataTable,
    Footer,
    Header,
    Label,
    RichLog,
    Static,
)
from textual.containers import Container, Horizontal, Vertical, VerticalScroll

from models.anomaly import Anomaly
from models.transaction import Transaction
from services.db import DatabaseManager
from screens.forensic_log import ForensicLogPane
from screens.ingestion import IngestionPane
from screens.settings import SettingsPane

SIDEBAR_BUTTONS = [
    ("dashboard", "Dashboard"),
    ("ingestion", "Ledger Ingestion"),
    ("forensic_log", "Forensic Log"),
    ("settings", "Settings"),
]

_ADMIN_ONLY = {"ingestion"}


def _role(app) -> str:
    user = getattr(app, "current_user", None)
    if isinstance(user, dict):
        return user.get("role", "viewer")
    return getattr(user, "role", "viewer")

_SEP = "\u2500" * 50


class DashboardPane(Vertical):

    DEFAULT_CSS = """
    DashboardPane {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }

    DashboardPane #kpi-row {
        height: auto;
        margin-bottom: 1;
    }

    DashboardPane .kpi-card {
        width: 1fr;
        height: 7;
        border: solid $primary;
        margin: 0 1 0 0;
        padding: 0 1;
        text-align: center;
        content-align: center middle;
    }
    DashboardPane .kpi-card:last-child {
        margin-right: 0;
    }
    DashboardPane .kpi-card .kpi-icon {
        text-style: bold;
        text-align: center;
        width: 100%;
        height: 1;
    }
    DashboardPane .kpi-card .kpi-value {
        text-style: bold;
        text-align: center;
        width: 100%;
        height: 1;
    }
    DashboardPane .kpi-card .kpi-label {
        text-align: center;
        width: 100%;
        height: 1;
    }
    DashboardPane .kpi-card .kpi-desc {
        color: $text-muted;
        text-align: center;
        width: 100%;
        height: 1;
    }
    DashboardPane .kpi-card.kpi-txns {
        border: solid $primary;
    }
    DashboardPane .kpi-card.kpi-txns .kpi-value {
        color: $primary;
    }
    DashboardPane .kpi-card.kpi-anomalies {
        border: solid $warning;
    }
    DashboardPane .kpi-card.kpi-anomalies .kpi-value {
        color: $warning;
    }
    DashboardPane .kpi-card.kpi-critical {
        border: solid $error;
    }
    DashboardPane .kpi-card.kpi-critical .kpi-value {
        color: $error;
    }
    DashboardPane .kpi-card.kpi-clean {
        border: solid $success;
    }
    DashboardPane .kpi-card.kpi-clean .kpi-value {
        color: $success;
    }

    DashboardPane #txn-section-title {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }

    DashboardPane #txn-table {
        height: auto;
        max-height: 13;
        margin-bottom: 1;
    }

    DashboardPane #pagination {
        height: auto;
        margin-bottom: 1;
        align: center middle;
    }
    DashboardPane #pagination #page-prev {
        width: 10;
        margin-right: 1;
    }
    DashboardPane #pagination #page-info {
        width: 16;
        text-align: center;
        content-align: center middle;
        color: $text-muted;
    }
    DashboardPane #pagination #page-next {
        width: 10;
        margin-left: 1;
    }

    DashboardPane #chart-title {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }

    DashboardPane #chart-box {
        height: auto;
        padding: 1 2;
        border: solid $panel-lighten-2;
    }

    DashboardPane #chart-box .chart-bar-row {
        height: 3;
        align: left middle;
    }
    DashboardPane #chart-box .chart-bar-row .chart-label {
        width: 18;
        color: $text;
    }
    DashboardPane #chart-box .chart-bar-row .chart-bar {
        width: 1fr;
        height: 1;
    }
    DashboardPane #chart-box .chart-bar-row .chart-count {
        width: 8;
        text-align: right;
        color: $text-muted;
    }

    DashboardPane #loading-msg {
        color: $text-muted;
        padding: 2 0;
        text-align: center;
    }

    DashboardPane #dashboard-header {
        height: auto;
        margin-bottom: 1;
    }
    DashboardPane #dashboard-title {
        text-style: bold;
        color: $accent;
        width: 1fr;
    }
    DashboardPane #refresh-btn {
        width: 18;
    }
    """

    PAGE_SIZE = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page = 0
        self._transactions: list[dict] = []
        self._anomalies: list[dict] = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="dashboard-header"):
            yield Label("Dashboard Overview", id="dashboard-title")
            yield Button("Refresh Data", id="refresh-btn", variant="default")
        with Horizontal(id="kpi-row"):
            yield Static("", id="kpi-txns")
            yield Static("", id="kpi-anomalies")
            yield Static("", id="kpi-critical")
            yield Static("", id="kpi-clean")

        yield Label("Recent Transactions", id="txn-section-title")
        yield DataTable(id="txn-table")
        with Horizontal(id="pagination"):
            yield Button("\u25c0 Prev", id="page-prev", variant="default")
            yield Label("Page 1 of 1", id="page-info")
            yield Button("Next \u25b6", id="page-next", variant="default")

        yield Label("Anomaly Distribution", id="chart-title")
        yield Static("", id="chart-box")

    def on_mount(self) -> None:
        self._load_data()

    @work(thread=True, exclusive=True)
    def _load_data(self) -> None:
        db: Optional[DatabaseManager] = getattr(self.app, "db", None)
        if db is None:
            return

        company_id = _resolve_company_id(self.app)
        if company_id is None:
            return

        try:
            txns = db.fetch_transactions(company_id)
            anomalies = db.fetch_anomalies(company_id)
        except Exception:
            txns = []
            anomalies = []

        self._call_thread(self._on_data_loaded, txns, anomalies)

    def _on_data_loaded(self, txns: list[dict], anomalies: list[dict]) -> None:
        self._transactions = txns
        self._anomalies = anomalies

        total_txns = len(txns)
        total_anomalies = len(anomalies)
        critical = sum(1 for a in anomalies if (a.get("severity") or "").lower() in ("critical", "crit", "high"))
        anomaly_txn_ids = {a["transaction_id"] for a in anomalies if a.get("transaction_id")}
        clean_count = total_txns - len(anomaly_txn_ids)
        clean_rate = (clean_count / total_txns * 100) if total_txns > 0 else 100.0

        self._render_kpi("kpi-txns", f"{total_txns:,}", "Total Transactions", "All ledger entries in system", "", "kpi-txns")
        self._render_kpi("kpi-anomalies", f"{total_anomalies:,}", "Anomalies Flagged", "Suspicious entries detected", "", "kpi-anomalies")
        self._render_kpi("kpi-critical", f"{critical:,}", "Critical Severity", "Requires immediate review", "", "kpi-critical")
        self._render_kpi("kpi-clean", f"{clean_rate:.1f}%", "Clean Rate", "Transactions with no flags", "", "kpi-clean")

        sorted_txns = sorted(txns, key=lambda t: t.get("date") or "", reverse=True)
        self._transactions = sorted_txns
        self._page = 0
        self._render_table()

        self._render_chart(anomalies)

    def _render_kpi(self, widget_id: str, value: str, label: str, desc: str, icon: str, css_class: str) -> None:
        try:
            container = self.query_one(f"#{widget_id}", Static)
            container.set_classes(f"kpi-card {css_class}")
            container.update(f"{icon}\n[bold]{value}[/bold]\n{label}\n{desc}")
        except Exception:
            pass

    def _render_table(self) -> None:
        table = self.query_one("#txn-table", DataTable)
        table.clear()
        table.cursor_type = "row"
        columns_added = getattr(self, "_table_columns_added", False)
        if not columns_added:
            table.add_columns("Date", "Description", "Amount", "Account", "Person")
            self._table_columns_added = True

        total_pages = max(1, (len(self._transactions) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._page = max(0, min(self._page, total_pages - 1))
        start = self._page * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, len(self._transactions))
        page_txns = self._transactions[start:end]

        for t in page_txns:
            date = t.get("date") or "\u2014"
            if hasattr(date, "isoformat"):
                date = date.isoformat()
            desc = (t.get("description") or "\u2014")[:40]
            amount = t.get("amount")
            if amount is not None:
                try:
                    amount = f"RWF {float(amount):,.2f}"
                except (TypeError, ValueError):
                    amount = str(amount)
            else:
                amount = "\u2014"
            account = (t.get("account") or "\u2014")[:20]
            person = t.get("person") or "\u2014"
            table.add_row(date, desc, amount, account, person)

        self.query_one("#page-info", Label).update(f"Page {self._page + 1} of {total_pages}")

    def _render_chart(self, anomalies: list[dict]) -> None:
        type_counts: Counter = Counter(a.get("anomaly_type", "unknown") for a in anomalies)
        if not type_counts:
            try:
                self.query_one("#chart-box", Static).update("No anomalies to chart.")
            except Exception:
                pass
            return

        max_count = max(type_counts.values())
        bars: list[str] = []
        chart_title = "Anomaly Distribution"
        bars.append(f"[bold]{chart_title}[/bold]")
        bars.append(_SEP)
        for atype in sorted(type_counts, key=type_counts.get, reverse=True):
            count = type_counts[atype]
            ratio = count / max_count if max_count > 0 else 0
            bar_len = int(ratio * 25)
            bar = "\u2588" * bar_len
            label = atype.replace("_", " ").title()
            bars.append(f"  {label:<18} {bar:<25} {count}")
        bars.append(_SEP)
        bars.append(f"  Total: {sum(type_counts.values())} anomalies across {len(type_counts)} types")

        try:
            self.query_one("#chart-box", Static).update("\n".join(bars))
        except Exception:
            pass

    def refresh_data(self) -> None:
        self._load_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            self.refresh_data()
        elif event.button.id == "page-prev":
            if self._page > 0:
                self._page -= 1
                self._render_table()
        elif event.button.id == "page-next":
            total = len(self._transactions)
            total_pages = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
            if self._page < total_pages - 1:
                self._page += 1
                self._render_table()

    def _call_thread(self, fn, *args, **kwargs) -> None:
        try:
            self.app.call_from_thread(fn, *args, **kwargs)
        except Exception:
            pass


def _resolve_company_id(app) -> Optional[int]:
    user = getattr(app, "current_user", None)
    if user is None:
        return None
    if isinstance(user, dict):
        return user.get("company_id")
    return getattr(user, "company_id", None)


class DashboardScreen(Screen):
    """Main navigation hub."""

    def __init__(self, initial_tab: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_tab = initial_tab or "dashboard"
        self._current_tab: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="dashboard-body"):
            with VerticalScroll(id="sidebar") as sidebar:
                sidebar.border_title = "RootCFO"
                yield Label("NAVIGATION", id="sidebar-title")
                for button_id, label in SIDEBAR_BUTTONS:
                    yield Button(label, id=f"nav-{button_id}", classes="nav-btn")
                yield Button("Logout", id="nav-logout", classes="nav-btn logout-btn")

            with Container(id="content-pane"):
                with ContentSwitcher(initial=self._initial_tab, id="content-switcher"):
                    yield DashboardPane(id="dashboard")
                    yield IngestionPane(id="ingestion")
                    yield ForensicLogPane(id="forensic_log")
                    yield SettingsPane(id="settings")

        with Container(id="audit-console"):
            yield Label("Audit Console", id="audit-label")
            yield RichLog(
                id="audit-log",
                auto_scroll=True,
                markup=True,
                wrap=True,
            )

        yield Footer()

    def on_mount(self) -> None:
        self._current_tab = self._initial_tab
        self._update_active_button(self._initial_tab)
        self._apply_role_visibility()

    def _apply_role_visibility(self) -> None:
        role = _role(self.app)
        for btn_id in _ADMIN_ONLY:
            try:
                btn = self.query_one(f"#nav-{btn_id}", Button)
                btn.display = role == "admin"
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "nav-logout":
            self.app.current_user = None
            self.app.current_company_id = None
            from screens.auth_screen import AuthScreen
            self.app.switch_screen(AuthScreen())
            return
        if not btn_id.startswith("nav-"):
            return
        target = btn_id[len("nav-"):]
        switcher = self.query_one("#content-switcher", ContentSwitcher)
        child_ids = {getattr(child, "id", None) for child in switcher.children}
        if target in child_ids:
            switcher.current = target
            self._update_active_button(target)
            self._current_tab = target
            self.write_audit(f"Switched to [b]{event.button.label}[/b]")

            if target == "forensic_log":
                try:
                    pane = self.query_one("#forensic_log", ForensicLogPane)
                    pane.refresh_data()
                except Exception:
                    pass
            if target == "dashboard":
                try:
                    pane = self.query_one("#dashboard", DashboardPane)
                    pane.refresh_data()
                except Exception:
                    pass

    def _update_active_button(self, active_id: str) -> None:
        all_buttons = self.query(".nav-btn")
        for node in all_buttons:
            if isinstance(node, Button):
                node.remove_class("-active")
        if active_id:
            try:
                target = self.query_one(f"#nav-{active_id}", Button)
            except Exception:
                target = None
            if target is not None:
                target.add_class("-active")

    def write_audit(self, message: str) -> None:
        try:
            audit_log = self.query_one("#audit-log", RichLog)
        except Exception:
            return
        audit_log.write(message)
