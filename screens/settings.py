"""NEW: SettingsPane component — business hours, anomaly auto-detect, theme.

Two classes:

* ``SettingsPane(Vertical)`` — reusable, embeddable in the dashboard
  ContentSwitcher. Mount with ``SettingsPane(id="settings")``.
* ``SettingsScreen(Screen)`` — thin standalone wrapper (Header + Pane + Footer)
  kept for future ``push_screen("settings")`` usage if needed.

NOTE (as per handover §3.2): values are NOT yet persisted anywhere — this pane
writes them in-memory onto ``self.app.business_hours_start / _end``,
``self.app.auto_detect_anomalies``, and ``self.app.theme`` so downstream
screens (IngestionPane, ForensicLogPane, DashboardScreen) can read them.
Future work: add a TOML config or DB user_preferences table and wire loads/saves.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Static,
    Switch,
)


_DEFAULT_BH_START = "09:00"
_DEFAULT_BH_END = "17:00"
_DEFAULT_THEME = "default"
_DEFAULT_AUTO_DETECT = True


class SettingsPane(Vertical):
    """User-facing preferences editor.

    Field list:
    - Business Hours Start (Input, default "09:00")
    - Business Hours End (Input, default "17:00")
    - Auto-Detect Anomalies (Switch, default ON)
    - Theme (Input, default "default")
    - Save Settings Button → toast summary + write app state
    - Reset to Defaults Button → reset fields + toast
    """

    DEFAULT_CSS = """
    SettingsPane {
        height: 1fr;
        padding: 1 2;
    }
    SettingsPane #settings-title {
        text-style: bold;
        color: $primary;
        padding: 0 0 1 0;
    }
    SettingsPane .settings-row {
        height: auto;
        margin-bottom: 1;
        align: left middle;
    }
    SettingsPane .settings-row Label {
        width: 26;
    }
    SettingsPane .settings-row Input {
        width: 1fr;
    }
    SettingsPane #settings-notice {
        padding: 0 1 1 1;
        color: $text-muted;
    }
    SettingsPane #settings-status {
        padding: 1;
        color: $text-muted;
        min-height: 3;
    }
    SettingsPane #settings-actions {
        margin-top: 1;
    }
    SettingsPane #settings-actions Button {
        margin-right: 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bh_start = _DEFAULT_BH_START
        self._bh_end = _DEFAULT_BH_END
        self._auto_detect = _DEFAULT_AUTO_DETECT
        self._theme = _DEFAULT_THEME

    # ── Compose ───────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Label("Settings", id="settings-title")
        yield Static(
            "⚠  Values are stored in-memory only for this session. "
            "Persistence (config file or DB preferences table) is not yet wired up.",
            id="settings-notice",
        )
        with Horizontal(classes="settings-row"):
            yield Label("Business Hours Start:")
            yield Input(value=self._bh_start, id="bh-start")
        with Horizontal(classes="settings-row"):
            yield Label("Business Hours End:")
            yield Input(value=self._bh_end, id="bh-end")
        with Horizontal(classes="settings-row"):
            yield Label("Auto-Detect Anomalies:")
            sw = Switch(value=self._auto_detect, id="auto-detect")
            yield sw
        with Horizontal(classes="settings-row"):
            yield Label("Theme:")
            yield Input(value=self._theme, id="theme-name")
        with Horizontal(id="settings-actions"):
            yield Button("Save Settings", id="save-settings", variant="primary")
            yield Button("Reset to Defaults", id="reset-settings", variant="default")
        yield Static("", id="settings-status")

    def on_mount(self) -> None:
        # Seed initial app-level defaults so downstream reads are non-None
        # even before the user clicks "Save".
        self._write_app_state(
            bh_start=self._bh_start,
            bh_end=self._bh_end,
            auto_detect=self._auto_detect,
            theme=self._theme,
        )

    # ── Event handlers ─────────────────────────────────────────────────
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings":
            self._save()
        elif event.button.id == "reset-settings":
            self._reset()

    # ── Save / Reset ──────────────────────────────────────────────────
    def _collect_fields(self) -> dict:
        bh_start = self.query_one("#bh-start", Input).value.strip() or _DEFAULT_BH_START
        bh_end = self.query_one("#bh-end", Input).value.strip() or _DEFAULT_BH_END
        auto_detect = bool(self.query_one("#auto-detect", Switch).value)
        theme = self.query_one("#theme-name", Input).value.strip() or _DEFAULT_THEME
        return {
            "bh_start": bh_start,
            "bh_end": bh_end,
            "auto_detect": auto_detect,
            "theme": theme,
        }

    def _save(self) -> None:
        values = self._collect_fields()
        self._write_app_state(**values)
        self._bh_start = values["bh_start"]
        self._bh_end = values["bh_end"]
        self._auto_detect = values["auto_detect"]
        self._theme = values["theme"]

        summary = (
            f"Saved: hours={values['bh_start']}–{values['bh_end']}  "
            f"auto_detect={'ON' if values['auto_detect'] else 'OFF'}  "
            f"theme='{values['theme']}'"
        )
        self.notify(summary, severity="information")
        self.query_one("#settings-status", Static).update(f"✓ {summary}")

    def _reset(self) -> None:
        self.query_one("#bh-start", Input).value = _DEFAULT_BH_START
        self.query_one("#bh-end", Input).value = _DEFAULT_BH_END
        self.query_one("#auto-detect", Switch).value = _DEFAULT_AUTO_DETECT
        self.query_one("#theme-name", Input).value = _DEFAULT_THEME
        self._write_app_state(
            bh_start=_DEFAULT_BH_START,
            bh_end=_DEFAULT_BH_END,
            auto_detect=_DEFAULT_AUTO_DETECT,
            theme=_DEFAULT_THEME,
        )
        self._bh_start = _DEFAULT_BH_START
        self._bh_end = _DEFAULT_BH_END
        self._auto_detect = _DEFAULT_AUTO_DETECT
        self._theme = _DEFAULT_THEME
        self.notify("Settings reset to defaults.", severity="information")
        self.query_one("#settings-status", Static).update(
            "Reset to defaults: hours=09:00–17:00  auto_detect=ON  theme='default'"
        )

    # ── App-level state write-through ─────────────────────────────────
    def _write_app_state(
        self,
        *,
        bh_start: str,
        bh_end: str,
        auto_detect: bool,
        theme: str,
    ) -> None:
        try:
            app = self.app
        except Exception:
            return
        app.business_hours_start = bh_start
        app.business_hours_end = bh_end
        app.auto_detect_anomalies = auto_detect
        if getattr(app, "theme", None) != theme:
            # NOTE: live Textual theme switching only works for themes that
            # are registered. "default" is not special; if a theme string is
            # unknown, Textual will no-op / warn. We always attempt the set.
            try:
                setattr(app, "theme", theme)
            except Exception:
                pass


class SettingsScreen(Screen):
    """Thin standalone wrapper for future push_screen("settings") usage."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pane: Optional[SettingsPane] = None

    def compose(self) -> ComposeResult:
        yield Header()
        self._pane = SettingsPane(id="settings")
        yield self._pane
        yield Footer()

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