"""Calvin: Color-coded anomaly table with clickable rows."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label
from textual.containers import Vertical


class ForensicLogScreen(Screen):
    """Calvin: Shows all anomalies in sortable DataTable.

    Columns: Date, Description, Amount, Type, Severity
    Color coding via CSS classes: critical (red), warning (yellow), info (blue)
    Click a row → push "report" with anomaly_id

    Use: self.app.db.fetch_anomalies(company_id)
    """

    def compose(self) -> ComposeResult:
        # Calvin: Header + Label + DataTable + Footer
        pass

    def on_mount(self):
        # Calvin: add columns to DataTable, fetch anomalies from DB, populate rows with style classes
        pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        # Calvin: extract anomaly_id from row key, push "report" screen with it
        pass
