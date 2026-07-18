# RootCFO — Design Specification

**Date:** 2026-07-18
**Project:** RootCFO — Terminal-based Financial Fraud Detection for SMEs
**Team:** David Ndizeye, Jimmy Shimwa, Bruce Mupenzi, Elyse Gianne Ruhigira, Calvin Rugwiro, Juliana Fule, Priscilla Yar Mabior Madit

---

## 1. Overview

RootCFO is an interactive terminal-based financial intelligence application built in Python using the Textual framework. It detects internal fraud, suspicious transactions, and ledger inconsistencies for SMEs. The system accepts CSV/JSON financial records, validates them, stores them in MySQL (Aiven), runs deterministic statistical anomaly detection (duplicate detection, off-hours analysis, Benford's Law), then ships flagged data to the Groq LLM API for forensic narrative analysis. Results are displayed in a color-coded TUI with follow-up chat capability.

This is a group project prototype for ALU's Peer Learning Project 2 (PLP-2), counting for 25% of total grade.

---

## 2. Project Structure

```
rootcfo/
├── main.py                      # Entry point
├── app.py                       # RootCFOApp (Textual App subclass)
├── .env                         # DB creds, API keys (gitignored)
├── .env.example                 # Template for teammates
├── requirements.txt             # Dependencies
├── pyproject.toml               # Project metadata
├── README.md                    # Setup & usage instructions
├── sql/
│   └── schema.sql               # Table creation scripts (Juliana)
├── screens/
│   ├── __init__.py
│   ├── auth_screen.py           # Login/Signup tabs (Bruce)
│   ├── onboarding.py            # Business profile form (Bruce)
│   ├── dashboard.py             # Master dashboard + sidebar (David)
│   ├── ingestion.py             # CSV/JSON file import (Juliana)
│   ├── forensic_log.py          # Color-coded anomaly table (Calvin)
│   └── report.py                # AI report + follow-up chat (Calvin)
├── models/
│   ├── __init__.py
│   ├── user.py                  # User, Company dataclasses (Bruce)
│   ├── transaction.py           # Transaction dataclass (Jimmy)
│   └── anomaly.py               # Anomaly dataclass (Elyse)
├── services/
│   ├── __init__.py
│   ├── db.py                    # MySQL CRUD wrapper (Priscilla)
│   ├── parser.py                # CSV/JSON ingestion & validation (Elyse)
│   ├── detector.py              # Statistical anomaly engine (Jimmy)
│   └── ai_forensic.py           # Groq API client (David)
└── utils/
    ├── __init__.py
    ├── config.py                # Env var loading (Priscilla)
    └── logger.py                # Audit log formatter
```

---

## 3. Dependencies

- `textual` — TUI framework
- `mysql-connector-python` — MySQL driver
- `groq` — Groq API client
- `python-dotenv` — Environment variable loading
- `pandas` — CSV/JSON parsing helpers
- `bcrypt` — Password hashing
- `pytest` — Unit testing

---

## 4. Database Schema

```sql
CREATE TABLE companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    address TEXT,
    business_hours VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'viewer') DEFAULT 'admin',
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    date DATE NOT NULL,
    description VARCHAR(500),
    amount DECIMAL(15,2) NOT NULL,
    account VARCHAR(100),
    person VARCHAR(100),
    source_file VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE anomalies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    transaction_id INT,
    anomaly_type ENUM('duplicate','off_hours','benford_deviation','vendor_pattern','amount_threshold','ai_flagged'),
    severity ENUM('critical','warning','info') DEFAULT 'warning',
    description TEXT NOT NULL,
    ai_analysis TEXT,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);
```

---

## 5. Services Architecture

### 5.1 `services/db.py` — DatabaseManager
- `connect()` / `disconnect()` — MySQL connection lifecycle
- `execute_query(sql, params)` — Parameterized query execution
- `insert_many(table, records)` — Bulk insert for parsed transactions
- `fetch_companies()`, `fetch_transactions(company_id)`, `fetch_anomalies(company_id)`

### 5.2 `services/parser.py` — FileParser
- `detect_format(filepath)` — CSV vs JSON detection
- `validate_columns(df)` — Ensure required columns exist
- `parse(filepath)` → `list[Transaction]` — Full pipeline
- Raises `ParserError` for malformed files (caught by screen, shown as notification)

### 5.3 `services/detector.py` — AnomalyDetector
- `find_duplicates(transactions)` — Same description + amount pairs
- `find_off_hours(transactions, business_hours)` — Out-of-window timestamps
- `benfords_test(transactions)` — First-digit distribution analysis
- `threshold_breaker(transactions, threshold=10000)` — Amounts exceeding configurable limit (default from `config.py`)
- Returns `list[Anomaly]`

### 5.4 `services/ai_forensic.py` — AIForensic
- `analyze(anomalies, transactions)` — Batch flagged data, send to Groq, return narrative
- `chat(history, question)` — Follow-up Q&A on a report
- Handles timeout/rate-limit errors gracefully
- Structured JSON prompt engineering for consistent forensic output

---

## 6. UI Screens (Textual)

### 6.1 AuthScreen (Bruce)
- `TabbedContent` with Login / Signup tabs
- Username + Password inputs; signup adds company name
- Push `OnboardingScreen` (new user) or `DashboardScreen` (existing)

### 6.2 OnboardingScreen (Bruce)
- Form: company name, email, address, business hours
- Creates Company + User in DB → push DashboardScreen

### 6.3 DashboardScreen (David)
- `VerticalLayout`: sidebar (fixed width) + main content + bottom audit console
- Sidebar buttons: Dashboard, Ledger Ingestion, Forensic Log, Settings
- Bottom `RichLog` for live audit stream
- Main pane switches per sidebar selection (default: summary stats)

### 6.4 IngestionScreen (Juliana)
- `Input` for file path + "Import" button
- Calls parser → inserts to DB → shows result in audit pane
- Color-coded status messages (`[OK]`, `[WARN]`, `[ERR]`)

### 6.5 ForensicLogScreen (Calvin)
- `DataTable` with sortable columns
- Rows: red=critical, yellow=warning, blue=info
- Click → push ReportScreen with anomaly details

### 6.6 ReportScreen (Calvin)
- Left: scrollable AI report (`MarkdownViewer`)
- Bottom chat bar: `Input` + "Ask" button for follow-up questions to Groq

---

## 7. Error Handling Strategy

| Layer | Mechanism |
|---|---|
| UI | Textual `Notification` toast for user-facing messages |
| Service | Custom exceptions (`ParserError`, `DatabaseError`, `APIError`) |
| DB | Wrapped `mysql.connector` errors → audit pane log |

---

## 8. Testing

- `pytest` with per-service test files in `tests/`
- `test_detector.py` — known anomalies verified
- `test_parser.py` — malformed/valid CSV, missing columns
- `test_db.py` — query building (mocked connection)
- Each team member writes tests for their own modules

---

## 9. Team Assignments

| Member | Responsibility | Difficulty |
|---|---|---|
| David | `services/ai_forensic.py`, `app.py`, `screens/dashboard.py` | Hardest |
| Jimmy | `services/detector.py`, `models/transaction.py` | Hard |
| Bruce | `screens/auth_screen.py`, `screens/onboarding.py`, `models/user.py` | Medium-Hard |
| Elyse | `services/parser.py`, `models/anomaly.py` | Medium |
| Calvin | `screens/report.py`, `screens/forensic_log.py` | Medium |
| Juliana | `screens/ingestion.py`, `sql/schema.sql` | Medium |
| Priscilla | `services/db.py`, `utils/config.py` | Medium-Easy |

---

## 10. Success Criteria

- New user can sign up, onboard, and upload a CSV ledger
- Deterministic engine detects duplicates, off-hours, Benford deviations
- Groq AI returns forensic narrative for flagged anomalies
- Color-coded report with clickable rows and follow-up chat
- All 7 members have commits in the GitHub repo
- `README.md` documents setup, usage, and team
