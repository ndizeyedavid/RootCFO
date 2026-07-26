"""David: RootCFOApp — main Textual application class.

Registers all screens, holds shared DB/AI instances, defines global CSS theme.
"""

from typing import Optional

from textual.app import App

from screens.auth_screen import AuthScreen
from screens.onboarding import OnboardingScreen
from screens.dashboard import DashboardScreen
from screens.ingestion import IngestionScreen
from screens.forensic_log import ForensicLogScreen
from screens.report import ReportScreen

from services.db import DatabaseManager, DatabaseError
from services.ai_forensic import AIForensic, APIError
from utils.logger import log


class RootCFOApp(App):
    """David: Orchestrator — owns DB/AI, registers screens, pushes auth on mount."""

    CSS_PATH = "styles.tcss"

    TITLE = "RootCFO — Terminal Financial Forensics"
    SUB_TITLE = "Anomaly Detection & AI Audit"

    SCREENS = {
        "auth": AuthScreen,
        "onboarding": OnboardingScreen,
        "dashboard": DashboardScreen,
        "ingestion": IngestionScreen,
        "forensic_log": ForensicLogScreen,
        "report": ReportScreen,
    }

    VALID_THEME_MODES = ("dark", "light")

    def __init__(self, theme_mode: str = "dark"):
        super().__init__()
        self.db: Optional[DatabaseManager] = None
        self.ai: Optional[AIForensic] = None
        self.current_user: Optional[dict] = None
        self.current_company_id: Optional[int] = None
        self._theme_mode = theme_mode if theme_mode in self.VALID_THEME_MODES else "dark"

    def on_mount(self) -> None:
        """David: init DatabaseManager + connect, init AIForensic, push auth screen.

        Uses log() for audit messages. If either service fails, the user still lands
        on the auth screen with a visible audit note — we don't crash the whole app.
        """
        if self._theme_mode == "dark":
            self.theme = self.dark_theme
        else:
            self.theme = self.light_theme

        self.db = DatabaseManager()
        try:
            self.db.connect()
            self._audit("Database connection established", "info")
        except DatabaseError as exc:
            self._audit(f"Database connection failed: {exc}", "error")
        except Exception as exc:
            self._audit(f"Unexpected DB init failure: {exc}", "critical")

        try:
            self.ai = AIForensic()
            if self.ai.client is None:
                self._audit(
                    "AIForensic initialized without API key — AI calls will error at runtime",
                    "warn",
                )
            else:
                self._audit("AIForensic client initialized", "info")
        except APIError as exc:
            self._audit(f"AIForensic init failed: {exc}", "error")
            self.ai = None
        except Exception as exc:
            self._audit(f"Unexpected AI init failure: {exc}", "critical")
            self.ai = None

        self.push_screen("auth")
        self._audit("Application mounted — pushed auth screen", "info")

    # ── Helpers ──────────────────────────────────────────────────────────
    def _audit(self, message: str, level: str = "info") -> None:
        """Write to the audit console of the currently-active screen if it supports one.

        Falls back to the dashboard screen's audit console if mounted, otherwise no-op.
        Never raises.
        """
        formatted = log(message, level=level)
        try:
            active = self.screen
        except Exception:
            return
        try:
            writer = getattr(active, "write_audit", None)
            if callable(writer):
                writer(formatted)
                return
        except Exception:
            pass
        # Try dashboard screen if that's not the active one but is installed
        try:
            if "dashboard" in self._installed_screens:
                dash = self._installed_screens["dashboard"]
                writer = getattr(dash, "write_audit", None)
                if callable(writer):
                    writer(formatted)
        except Exception:
            pass

    def set_current_user(self, user: dict) -> None:
        """Convenience setter for AuthScreen / OnboardingScreen to stash the user."""
        self.current_user = user
        self.current_company_id = user.get("company_id") if isinstance(user, dict) else None
        self._audit(
            f"Current user set: {(user or {}).get('username', '?')}",
            "info",
        )