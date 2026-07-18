"""David: RootCFOApp — main Textual application class.

Registers all screens, holds shared DB/AI instances, defines global CSS theme.
"""

from textual.app import App

from screens.auth_screen import AuthScreen
from screens.onboarding import OnboardingScreen
from screens.dashboard import DashboardScreen
from screens.ingestion import IngestionScreen
from screens.forensic_log import ForensicLogScreen
from screens.report import ReportScreen


class RootCFOApp(App):
    """David: Implement — register SCREENS dict, on_mount(), global CSS."""

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
        """David: init DatabaseManager + connect, init AIForensic, push auth screen."""
        pass
