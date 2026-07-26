from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, RichLog, Static
from textual.containers import Vertical, Horizontal

from services.parser import FileParser, ParserError
from services.detector import AnomalyDetector
from services.db import DatabaseError


class IngestionScreen(Screen):
    """Juliana: Import financial files and run anomaly detection."""

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            yield Static(
                "Transaction Ingestion",
                id="title",
            )

            with Horizontal():
                yield Input(
                    placeholder="Enter CSV/JSON file path",
                    id="filepath",
                )

                yield Button(
                    "Import",
                    id="import",
                )

            yield Label(
                "Waiting for file...",
                id="status",
            )

            yield RichLog(
                id="log",
                highlight=True,
            )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "import":
            self._handle_import()

    def _handle_import(self):
        status = self.query_one("#status", Label)
        log = self.query_one("#log", RichLog)

        try:
            filepath = self.query_one(
                "#filepath",
                Input,
            ).value

            if not filepath:
                status.update("Please enter a file path.")
                return

            company_id = getattr(
                self.app.current_user,
                "company_id",
                None,
            )

            if company_id is None:
                status.update(
                    "No company found for current user."
                )
                return

            log.write("Step 1: Parsing file...")

            transactions = FileParser.parse(
                filepath,
                company_id,
            )

            log.write(
                f"Loaded {len(transactions)} transactions."
            )

            log.write(
                "Step 2: Saving transactions..."
            )

            transaction_data = [
                transaction.to_dict()
                for transaction in transactions
            ]

            self.app.db.insert_transactions(
                company_id,
                transaction_data,
            )

            log.write(
                "Transactions saved."
            )

            log.write(
                "Step 3: Detecting anomalies..."
            )

            detector = AnomalyDetector()

            anomalies = []

            anomalies.extend(
                detector.find_duplicates(
                    transactions
                )
            )

            company = self.app.db.fetch_company(
                company_id
            )

            if company:
                anomalies.extend(
                    detector.find_off_hours(
                        transactions,
                        company["business_hours"],
                    )
                )

            anomalies.extend(
                detector.benfords_test(
                    transactions
                )
            )

            anomalies.extend(
                detector.threshold_breaker(
                    transactions
                )
            )

            log.write(
                f"Found {len(anomalies)} anomalies."
            )

            log.write(
                "Step 4: Saving anomalies..."
            )

            if anomalies:
                self.app.db.insert_anomalies(
                    anomalies
                )

            log.write(
                "Anomalies saved."
            )

            status.update(
                f"Import complete: "
                f"{len(transactions)} transactions, "
                f"{len(anomalies)} anomalies."
            )

        except ParserError as error:
            status.update(
                f"Parser error: {error}"
            )
            log.write(str(error))

        except DatabaseError as error:
            status.update(
                f"Database error: {error}"
            )
            log.write(str(error))

        except Exception as error:
            status.update(
                f"Error: {error}"
            )
            log.write(str(error))