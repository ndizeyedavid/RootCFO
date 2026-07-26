"""Settings pane — basic preferences placeholder."""

from textual.app import ComposeResult
from textual.widgets import Input, Switch, Button, Label, Static
from textual.containers import Vertical, Horizontal


class SettingsPane(Vertical):
    """App-wide preferences.

    Current fields (placeholder):
      • Business hours start/end
      • Auto-detect anomalies (Switch)
      • Theme selection (Text Select)
    Saves values via toast notification — backend not wired.
    """

    DEFAULT_CSS = """
    SettingsPane {
        height: 1fr;
    }
    SettingsPane .settings-row {
        height: auto;
        margin: 0 2;
    }
    SettingsPane .settings-row Label {
        width: 28;
        padding: 0 1;
    }
    SettingsPane .settings-title {
        padding: 1 2 0 2;
        text-style: bold;
    }
    SettingsPane #business-hours-wrap {
        align-horizontal: left;
    }
    SettingsPane #settings-actions {
        margin: 1 2;
    }
    SettingsPane #settings-status {
        margin: 1 2;
    }
    SettingsPane #settings-hint {
        padding: 2;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Settings", classes="settings-title")

        with Horizontal(classes="settings-row", id="business-hours-wrap"):
            yield Label("Business Hours Start:")
            yield Input(placeholder="09:00", id="biz-start", value="09:00")
            yield Label("End:")
            yield Input(placeholder="17:00", id="biz-end", value="17:00")

        with Horizontal(classes="settings-row"):
            yield Label("Auto-Detect Anomalies:")
            yield Switch(value=True, id="auto-detect-switch")

        with Horizontal(classes="settings-row"):
            yield Label("Theme:")
            yield Input(placeholder="default", id="theme-input", value="default")

        with Horizontal(id="settings-actions"):
            yield Button("Save Settings", id="settings-save", variant="primary")
            yield Button("Reset to Defaults", id="settings-reset", variant="default")

        yield Static("", id="settings-status")
        yield Static(
            "Values are not persisted yet — wire to a config store (INI/TOML/DB) when ready.",
            id="settings-hint",
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "settings-save":
            self._save_settings()
        elif event.button.id == "settings-reset":
            self._reset_settings()

    def _save_settings(self):
        try:
            start = self.query_one("#biz-start", Input).value.strip()
            end = self.query_one("#biz-end", Input).value.strip()
            switch = self.query_one("#auto-detect-switch", Switch)
            theme = self.query_one("#theme-input", Input).value.strip()
        except Exception as e:
            self.notify(f"Could not read fields: {e}", severity="error")
            return
        msg = f"Saved: hours {start}–{end}, auto-detect={switch.value}, theme={theme!r}"
        self.notify(msg, title="Settings saved", severity="information")
        self.query_one("#settings-status", Static).update("Preferences saved.")

    def _reset_settings(self):
        try:
            self.query_one("#biz-start", Input).value = "09:00"
            self.query_one("#biz-end", Input).value = "17:00"
            self.query_one("#auto-detect-switch", Switch).value = True
            self.query_one("#theme-input", Input).value = "default"
        except Exception as e:
            self.notify(f"Could not reset fields: {e}", severity="error")
            return
        self.query_one("#settings-status", Static).update("")
        self.notify("Settings reset to defaults.", title="Reset complete", severity="information")