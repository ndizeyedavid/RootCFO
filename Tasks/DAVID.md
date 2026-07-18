# David => Team Lead & Core Integration

**Role:** You own the hardest pieces — Groq AI integration, the main app orchestrator, and the master dashboard screen. You are also the glue that connects everyone's work together.

---

## Your Files

| File                      | What it does                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| `services/ai_forensic.py` | Talks to Groq API — sends anomalies for analysis, handles follow-up chat                  |
| `app.py`                  | RootCFOApp class — registers all screens, holds global DB/AI instances, defines CSS theme |
| `screens/dashboard.py`    | Main dashboard with sidebar navigation + audit console                                    |

### Helper file (shared across team)

| `utils/logger.py` | Small utility for formatting audit log messages with timestamps and severity tags |

---

## What To Build

### 1. `utils/logger.py` (quick — do this first so everyone can use it)

A simple module with a `log(message, level="info")` function that returns a formatted string like:

```
[INFO] 2026-07-18 14:30:22 — Parsed 1,424 rows
[WARN] 2026-07-18 14:30:25 — 4 out-of-hours events detected
[CRIT] 2026-07-18 14:30:28 — Duplicate invoice INV-042 found
```

---

### 2. `services/ai_forensic.py` — AIForensic class

**Urgency:** HIGH — needs to be ready for Calvin's ReportScreen

**What it needs to do:**

- `analyze(anomalies: list[Anomaly], transactions: list[Transaction]) -> str`
  - Build a structured JSON payload with anomaly + transaction context
  - Send to Groq's chat completions endpoint
  - Return the AI's narrative response
- `chat(history: list[dict], question: str) -> str`
  - Append user message to history
  - Send to Groq, get response, return it
- Handle API errors gracefully

---

### 3. `screens/dashboard.py` — DashboardScreen

**Urgency:** MEDIUM — needs to be ready for integration phase

**What it needs to do:**

- `VerticalLayout` with sidebar (left, width=24) + main content (center) + audit console (bottom)
- Sidebar buttons: "Dashboard", "Ledger Ingestion", "Forensic Log", "Settings"
- Clicking a sidebar button switches the main content pane to the corresponding screen
- Bottom `RichLog` widget shows live audit messages (Priscilla's `log()` output)

---

### 4. `app.py` — RootCFOApp (most critical integration file)

**Urgency:** HIGH — everything plugs into this

**What it needs to do:**

- Extend Textual's `App` class
- Register all screen IDs and their classes in `SCREENS` dict
- `on_mount()`: connect DB, create AIForensic instance, push AuthScreen
- Store shared instances: `self.db = DatabaseManager()`, `self.ai = AIForensic()`
- Define global CSS for consistent dark theme across all screens

---

## How To Test Your Work

1. **AI Forensic:** Write a test with mock anomaly/transaction data (hardcoded dicts). Verify the prompt structure and that the Groq API returns a non-empty string.
2. **Dashboard:** Run `python main.py` and verify sidebar buttons switch content. Hard to fully test Textual UI without running it — so just run it.
3. **App integration:** Once all screens exist, run the app and walk through the full flow: login → onboard → ingest → view anomalies → open report.

---

## Dependencies

- You need Priscilla's `DatabaseManager` and `config.py` done before app.py fully works
- You need everyone's screens done before dashboard routing works
- You can build `ai_forensic.py` independently — no dependencies on anyone else
