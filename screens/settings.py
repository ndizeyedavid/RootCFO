"""Settings screen — profile editor + viewer user management."""

from typing import Optional

import bcrypt

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label, ListView, ListItem, Static


class SettingsPane(Vertical):
    """Embeddable settings pane with Profile + Viewer Users sections."""

    DEFAULT_CSS = """
    SettingsPane {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }

    SettingsPane #settings-title {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }

    SettingsPane .section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0 0 0;
    }

    SettingsPane .section-divider {
        color: $text-muted;
        padding: 0 0 1 0;
    }

    SettingsPane .field-row {
        height: auto;
        margin-bottom: 1;
        align: left middle;
    }
    SettingsPane .field-row Label {
        width: 20;
    }
    SettingsPane .field-row Input {
        width: 1fr;
    }

    SettingsPane #profile-username {
        color: $text-muted;
    }

    SettingsPane .save-btn {
        margin: 0 0 1 0;
    }

    SettingsPane #viewer-list {
        height: auto;
        max-height: 10;
        margin: 1 0;
        border: solid $panel-lighten-2;
    }
    SettingsPane #viewer-list ListItem {
        padding: 0 1;
    }
    SettingsPane #viewer-list ListItem > Horizontal {
        height: 3;
        align: left middle;
    }
    SettingsPane #viewer-list .viewer-name {
        width: 1fr;
    }
    SettingsPane #viewer-list .viewer-role {
        width: 10;
        color: $text-muted;
    }
    SettingsPane #viewer-list .viewer-delete {
        width: 10;
    }

    SettingsPane .status-msg {
        padding: 0 1;
        color: $text-muted;
        min-height: 3;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._company_id: Optional[int] = None
        self._user_id: Optional[int] = None

    def compose(self) -> ComposeResult:
        yield Label("Settings", id="settings-title")

        # ── Profile Section ──
        yield Label("Profile", classes="section-title")
        yield Label("\u2500" * 50, classes="section-divider")
        with Horizontal(classes="field-row"):
            yield Label("Company Name:")
            yield Input(id="profile-company-name")
        with Horizontal(classes="field-row"):
            yield Label("Contact Email:")
            yield Input(id="profile-email")
        with Horizontal(classes="field-row"):
            yield Label("Address:")
            yield Input(id="profile-address")
        with Horizontal(classes="field-row"):
            yield Label("Username:")
            yield Label("", id="profile-username")
        yield Button("Save Profile", id="save-profile", variant="primary", classes="save-btn")

        # ── Viewer Users Section ──
        yield Label("Viewer Users", classes="section-title")
        yield Label("\u2500" * 50, classes="section-divider")
        yield Label(
            "Create read-only users who can view reports but cannot modify data.",
            id="viewer-desc",
        )
        with Horizontal(classes="field-row"):
            yield Label("Username:")
            yield Input(placeholder="Choose a username", id="viewer-username")
        with Horizontal(classes="field-row"):
            yield Label("Password:")
            yield Input(placeholder="Password", password=True, id="viewer-password")
        with Horizontal(classes="field-row"):
            yield Label("Confirm:")
            yield Input(placeholder="Confirm password", password=True, id="viewer-confirm")
        yield Button("Create Viewer", id="create-viewer", variant="primary", classes="save-btn")

        yield Label("Existing Viewers:", id="viewer-list-label")
        yield ListView(id="viewer-list")

        yield Static("", id="settings-status")

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
        app = self.app
        db = getattr(app, "db", None)
        if db is None:
            return

        user = getattr(app, "current_user", None)
        if not user:
            return

        self._company_id = user.get("company_id")
        self._user_id = user.get("id")

        company = db.fetch_company(self._company_id)
        if company:
            self._set_field("profile-company-name", company.get("name", ""))
            self._set_field("profile-email", company.get("contact_email", ""))
            self._set_field("profile-address", company.get("address", ""))

        self._set_label("profile-username", user.get("username", ""))

        self._refresh_viewer_list()

    def _set_field(self, field_id: str, value: str) -> None:
        try:
            self.query_one(f"#{field_id}", Input).value = value
        except Exception:
            pass

    def _set_label(self, label_id: str, value: str) -> None:
        try:
            self.query_one(f"#{label_id}", Label).update(value)
        except Exception:
            pass

    def _set_status(self, msg: str) -> None:
        try:
            self.query_one("#settings-status", Static).update(msg)
        except Exception:
            pass

    def _refresh_viewer_list(self) -> None:
        db = getattr(self.app, "db", None)
        if db is None or self._company_id is None:
            return

        try:
            users = db.fetch_users_by_company(self._company_id)
        except Exception:
            self._set_status("Could not load user list.")
            return

        viewer_list = self.query_one("#viewer-list", ListView)
        viewer_list.clear()

        viewers = [u for u in users if u.get("role") == "viewer"]
        if not viewers:
            viewer_list.append(ListItem(Label("(no viewer users yet)")))
            return

        for v in viewers:
            row = Horizontal(
                Label(v.get("username", "?"), classes="viewer-name"),
                Label("viewer", classes="viewer-role"),
                Button("Delete", id=f"del-viewer-{v['id']}", classes="viewer-delete"),
            )
            viewer_list.append(ListItem(row))

    # ── Events ──────────────────────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "save-profile":
            self._save_profile()
        elif btn_id == "create-viewer":
            self._create_viewer()
        elif btn_id.startswith("del-viewer-"):
            user_id = int(btn_id.split("-")[-1])
            self._delete_viewer(user_id)

    # ── Profile ─────────────────────────────────────────────────────
    def _save_profile(self) -> None:
        db = getattr(self.app, "db", None)
        if db is None or self._company_id is None:
            self._set_status("Database not available.")
            return

        company_data = {
            "name": self._get_field("profile-company-name"),
            "contact_email": self._get_field("profile-email"),
            "address": self._get_field("profile-address"),
        }

        try:
            db.update_company(self._company_id, company_data)
            self.notify("Profile saved.", severity="information")
            self._set_status("Profile updated successfully.")
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")
            self._set_status(f"Error: {exc}")

    def _get_field(self, field_id: str) -> str:
        try:
            return self.query_one(f"#{field_id}", Input).value.strip()
        except Exception:
            return ""

    # ── Viewer CRUD ─────────────────────────────────────────────────
    def _create_viewer(self) -> None:
        db = getattr(self.app, "db", None)
        if db is None or self._company_id is None:
            self._set_status("Database not available.")
            return

        username = self._get_field("viewer-username")
        password = self._get_field("viewer-password")
        confirm = self._get_field("viewer-confirm")

        if not username or not password or not confirm:
            self.notify("Please fill in all viewer fields.", severity="error")
            return

        if password != confirm:
            self.notify("Passwords do not match.", severity="error")
            return

        if len(password) < 4:
            self.notify("Password must be at least 4 characters.", severity="error")
            return

        existing = db.fetch_user_by_username(username)
        if existing:
            self.notify("Username already taken.", severity="error")
            return

        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        try:
            db.insert_user(
                username=username,
                password_hash=pw_hash,
                company_id=self._company_id,
                role="viewer",
            )
            self.notify(f"Viewer '{username}' created.", severity="information")
            self._set_field("viewer-username", "")
            self._set_field("viewer-password", "")
            self._set_field("viewer-confirm", "")
            self._refresh_viewer_list()
            self._set_status(f"Viewer '{username}' created successfully.")
        except Exception as exc:
            self.notify(f"Creation failed: {exc}", severity="error")
            self._set_status(f"Error: {exc}")

    def _delete_viewer(self, user_id: int) -> None:
        db = getattr(self.app, "db", None)
        if db is None:
            return

        if user_id == self._user_id:
            self.notify("You cannot delete yourself.", severity="error")
            return

        try:
            db.execute_query("DELETE FROM users WHERE id = %s AND role = 'viewer'", (user_id,))
            self.notify("Viewer deleted.", severity="information")
            self._refresh_viewer_list()
            self._set_status("Viewer removed.")
        except Exception as exc:
            self.notify(f"Delete failed: {exc}", severity="error")
            self._set_status(f"Error: {exc}")


class SettingsScreen(Screen):
    """Standalone wrapper for push_screen usage."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pane: Optional[SettingsPane] = None

    def compose(self) -> ComposeResult:
        yield Header()
        self._pane = SettingsPane(id="settings")
        yield self._pane
