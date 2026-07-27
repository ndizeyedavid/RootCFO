
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label
from textual.containers import Vertical


class OnboardingScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
 
        company_name = getattr(self.app, "current_company_name", "")
 
        yield Vertical(
            Label("Company Name"),
            Input(value=company_name, placeholder="Company Name", id="onboarding-company-name"),
            Label("Contact Email"),
            Input(placeholder="Contact Email", id="onboarding-contact-email"),
            Label("Address"),
            Input(placeholder="Address", id="onboarding-address"),
            Label("Business Hours"),
            Input(value="Mon-Fri 8:00-17:00", placeholder="Business Hours", id="onboarding-business-hours"),
            Button("Save", id="onboarding-save-button", variant="primary"),
            Label("", id="onboarding-error"),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "onboarding-save-button":
            return
 
        error_label = self.query_one("#onboarding-error", Label)
 
        company_name = self.query_one("#onboarding-company-name", Input).value.strip()
        contact_email = self.query_one("#onboarding-contact-email", Input).value.strip()
        address = self.query_one("#onboarding-address", Input).value.strip()
        business_hours = self.query_one("#onboarding-business-hours", Input).value.strip()
 
        if not company_name or not contact_email or not address or not business_hours:
            error_label.update("Please fill in all fields.")
            return
 
        company_id = getattr(self.app, "current_company_id", None)
        if company_id is None:
            error_label.update("No company found for this session.")
            return
 
        data_dict = {
            "name": company_name,
            "contact_email": contact_email,
            "address": address,
            "business_hours": business_hours,
        }
 
        self.app.db.update_company(company_id, data_dict)
 
        error_label.update("")
        from screens.dashboard import DashboardScreen
        self.app.switch_screen(DashboardScreen())
