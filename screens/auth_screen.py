"""Bruce: Login and Signup screen with TabbedContent."""

import bcrypt
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, TabbedContent, TabPane
from textual.containers import Vertical


class AuthScreen(Screen):
    """Bruce: Tabbed login/signup screen.

    - Login tab: username + password + Sign In button → verify with bcrypt → push "dashboard"
    - Signup tab: username + password + company name + Create Account button → hash pw → DB insert → push "onboarding"

    Use:  self.app.db.insert_user(), self.app.db.fetch_user_by_username(), self.app.db.insert_company()
    """


def compose(self) -> ComposeResult:
    yield Header()

    with Vertical():
        yield Label("RootCFO Login")
        yield Input(placeholder="Username", id="username")
        yield Input(placeholder="Password", password=True, id="password")
        yield Button("Sign In", id="login")

    yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        # Bruce: route to _handle_login or _handle_signup
        pass

    def _handle_login(self):
        # Bruce: get username/password from inputs → verify bcrypt → push "dashboard"
        pass

    def _handle_signup(self):
        # Bruce: get fields → hash password → insert company → insert user → push "onboarding"
        pass
