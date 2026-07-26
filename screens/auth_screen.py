import bcrypt
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, TabbedContent, TabPane
from textual.containers import Vertical


class AuthScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Login", id="login-tab"):
                yield Vertical(
                    Label("Username"),
                    Input(placeholder="Username", id="login-username"),
                    Label("Password"),
                    Input(placeholder="Password", password=True, id="login-password"),
                    Button("Sign In", id="login-button", variant="primary"),
                    Label("", id="login-error"),
                )
            with TabPane("Sign Up", id="signup-tab"):
                yield Vertical(
                    Label("Company Name"),
                    Input(placeholder="Company Name", id="signup-company"),
                    Label("Username"),
                    Input(placeholder="Username", id="signup-username"),
                    Label("Password"),
                    Input(placeholder="Password", password=True, id="signup-password"),
                    Button("Create Account", id="signup-button", variant="primary"),
                    Label("", id="signup-error"),
                )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-button":
            self._handle_login()
        elif event.button.id == "signup-button":
            self._handle_signup()

    def _handle_login(self) -> None:
        username = self.query_one("#login-username", Input).value.strip()
        password = self.query_one("#login-password", Input).value
        error_label = self.query_one("#login-error", Label)

        if not username or not password:
            error_label.update("Please enter both username and password.")
            return

        user = self.app.db.fetch_user_by_username(username)
        if user is None:
            error_label.update("Invalid username or password.")
            return

        stored_hash = user["password_hash"]
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")

        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            error_label.update("Invalid username or password.")
            return

        error_label.update("")
        self.app.set_current_user(user)
        self.app.push_screen("dashboard")

    def _handle_signup(self) -> None:
        company_name = self.query_one("#signup-company", Input).value.strip()
        username = self.query_one("#signup-username", Input).value.strip()
        password = self.query_one("#signup-password", Input).value
        error_label = self.query_one("#signup-error", Label)

        if not company_name or not username or not password:
            error_label.update("Please fill in all fields.")
            return

        existing_user = self.app.db.fetch_user_by_username(username)
        if existing_user is not None:
            error_label.update("Username already taken.")
            return

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        company_id = self.app.db.insert_company(name=company_name)
        user_id = self.app.db.insert_user(
            username=username,
            password_hash=password_hash,
            company_id=company_id,
        )

        user = self.app.db.fetch_user_by_username(username)

        error_label.update("")
        self.app.current_company_name = company_name
        self.app.set_current_user(user)
        self.app.push_screen("onboarding")