# Calvin => Reports & Forensics Log

**Role:** You own the screens where users see results — the color-coded anomaly table and the detailed AI report with follow-up chat.

---

## Your Files

| File                      | What it does                                              |
| ------------------------- | --------------------------------------------------------- |
| `screens/forensic_log.py` | DataTable showing all anomalies with color-coded severity |
| `screens/report.py`       | Detailed AI report view with follow-up chat input         |

---

## What To Build

### 1. `screens/forensic_log.py` — ForensicLogScreen

**Urgency:** HIGH — core demo feature, shows the results of detection

**What it does:**

- `DataTable` with sortable columns: Date, Description, Amount, Type, Severity
- Loads anomalies + related transactions from DB on mount
- Color-coded rows: red (critical), yellow (warning), blue (info)
- Click a row → push `ReportScreen` with that anomaly's details

---

### 2. `screens/report.py` — ReportScreen

**Urgency:** MEDIUM-HIGH — needs David's AI service to work, but can be built with mock data

**What it does:**

- Receives an anomaly ID when pushed
- Loads full anomaly + related transactions from DB
- Left/top pane: `MarkdownViewer` showing AI analysis text
- Bottom: `Input` + "Ask" button for follow-up questions to Groq
- Chat history shown in a `RichLog` widget

---

## How To Test Your Work

1. **Forensic Log:** Push some fake anomalies into the DB manually or via a test script → run the app → navigate to Forensic Log → verify they appear colored correctly
2. **Report Screen:** Click an anomaly row → verify report screen opens → verify AI analysis text appears
3. **Chat:** Type a question → verify AI responds and the response appears in the chat log

---

## Dependencies

- You need **David's** `services/ai_forensic.py` for the AI analysis and chat methods
- You need **Priscilla's** `services/db.py` with methods: `fetch_anomalies()`, `fetch_anomaly()`, `fetch_transaction()`, `update_anomaly_analysis()`
- You need **David's** `app.py` to register your screens
- You can build the screens with hardcoded test data before their modules are ready
