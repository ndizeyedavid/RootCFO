"""Bruce: Business profile onboarding for new users."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label
from textual.containers import Vertical


class OnboardingScreen(Screen):
    """Bruce: Company details form after signup.

    Fields: company name (prefilled), contact email, address, business hours (default "Mon-Fri 8:00-17:00")
    On submit → self.app.db.update_company() → push "dashboard"

    Use: self.app.db.update_company(company_id, data_dict)
    """

    def compose(self) -> ComposeResult:
        # Bruce: build form with Input widgets for each field + Save button
        pass

    def on_button_pressed(self, event: Button.Pressed):
        # Bruce: collect field values → update company in DB → push "dashboard"
        pass
