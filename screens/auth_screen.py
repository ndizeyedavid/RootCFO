import bcrypt
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, TabbedContent, TabPane, Markdown
from textual.containers import Vertical, Horizontal


_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.txt"


def _load_logo_markdown() -> str:
    try:
        raw = _LOGO_PATH.read_text(encoding="utf-8").rstrip()
    except OSError:
        raw = "RootCFO"
    return "```\n" + raw + "\n```"


class AuthScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Markdown(_load_logo_markdown(), id="auth-logo"),
            id="auth-logo-wrap",
        )
        with TabbedContent():
            with TabPane("Login", id="login-tab"):
                yield Vertical(
                    Label("Username"),
                    Input(placeholder="Username", id="login-username"),
                    Label("Password"),
                    Input(placeholder="Password", password=True, id="login-password"),
                    Button("Sign In", id="login-button", variant="primary"),
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

        if not username or not password:
            self.notify("Please enter both username and password.", severity="error")
            return

        user = self.app.db.fetch_user_by_username(username)
        if user is None:
            self.notify("Invalid username or password.", severity="error")
            return

        stored_hash = user["password_hash"]
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")

        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            self.notify("Invalid username or password.", severity="error")
            return

        self.notify(f"Welcome back, {username}!", severity="information")
        self.app.set_current_user(user)
        self.app.push_screen("dashboard")

    def _handle_signup(self) -> None:
        company_name = self.query_one("#signup-company", Input).value.strip()
        username = self.query_one("#signup-username", Input).value.strip()
        password = self.query_one("#signup-password", Input).value

        if not company_name or not username or not password:
            self.notify("Please fill in all fields.", severity="error")
            return

        existing_user = self.app.db.fetch_user_by_username(username)
        if existing_user is not None:
            self.notify("Username already taken.", severity="error")
            return

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        try:
            company_id = self.app.db.insert_company(name=company_name)
            self.app.db.insert_user(
                username=username,
                password_hash=password_hash,
                company_id=company_id,
            )
        except Exception as e:
            self.notify(f"Signup failed: {e}", severity="error")
            return

        user = self.app.db.fetch_user_by_username(username)

        self.notify("Account created successfully!", severity="information")
        self.app.current_company_name = company_name
        self.app.set_current_user(user)
        self.app.push_screen("onboarding")