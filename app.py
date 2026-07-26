"""David: RootCFOApp — main Textual application class."""

from textual.app import App

from screens.auth_screen import AuthScreen
from screens.onboarding import OnboardingScreen
from screens.dashboard import DashboardScreen
from screens.ingestion import IngestionScreen
from screens.forensic_log import ForensicLogScreen
from screens.report import ReportScreen


class RootCFOApp(App):
    """Main RootCFO application."""

    CSS_PATH = "styles.tcss"

    SCREENS = {
        "auth": AuthScreen,
        "onboarding": OnboardingScreen,
        "dashboard": DashboardScreen,
        "ingestion": IngestionScreen,
        "forensic_log": ForensicLogScreen,
        "report": ReportScreen,
    }

    def __init__(self):
        super().__init__()
        self.db = None
        self.ai = None
        self.current_user = None

    def on_mount(self):
        """Initialize services and open authentication screen."""
        from services.db import DatabaseManager

        self.db = DatabaseManager()

        try:
            self.db.connect()
        except Exception as error:
            self.notify(
                f"Database connection failed: {error}",
                severity="error",
            )

        self.push_screen("auth")


if __name__ == "__main__":
    RootCFOApp().run()
