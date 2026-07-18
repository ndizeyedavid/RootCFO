# Juliana => File Ingestion & Database Schema

**Role:** You own the data entry point — the screen where users upload their financial files. You also own the SQL schema that defines the entire database structure.

---

## Your Files

| File                   | What it does                                                   |
| ---------------------- | -------------------------------------------------------------- |
| `screens/ingestion.py` | File input screen — user provides CSV/JSON path, clicks Import |
| `sql/schema.sql`       | CREATE TABLE SQL scripts for the entire database               |

---

## What To Build

### 1. `sql/schema.sql` (do this first — everyone needs the DB)

**Urgency:** HIGH — must run before anyone can test their code

```sql
CREATE DATABASE IF NOT EXISTS rootcfo;
USE rootcfo;

CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    address TEXT,
    business_hours VARCHAR(100) DEFAULT 'Mon-Fri 8:00-17:00',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'viewer') DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    date DATE NOT NULL,
    description VARCHAR(500),
    amount DECIMAL(15,2) NOT NULL,
    account VARCHAR(100),
    person VARCHAR(100),
    source_file VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anomalies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    transaction_id INT,
    anomaly_type ENUM(
        'duplicate', 'off_hours', 'benford_deviation',
        'vendor_pattern', 'amount_threshold', 'ai_flagged'
    ) NOT NULL,
    severity ENUM('critical', 'warning', 'info') DEFAULT 'warning',
    description TEXT NOT NULL,
    ai_analysis TEXT,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
);
```

---

### 2. `screens/ingestion.py` — IngestionScreen

**Urgency:** HIGH — core demo feature, shows the LEDGER INGESTION step

**What it does:**

- Input field for file path + "Import" button
- On import: calls Elyse's `FileParser.parse()` → Priscilla's `DatabaseManager.insert_many()` → Jimmy's `AnomalyDetector.analyze_all()`
- Shows progress in the bottom audit console
- Color-coded status messages: `[OK] Success`, `[WARN] Warning`, `[ERR] Error`
- After import, shows summary: "X transactions imported, Y anomalies detected"

---

## Dependencies

- You need **Elyse's** `services/parser.py` (FileParser class) — the actual parsing logic
- You need **Priscilla's** `services/db.py` for `insert_transactions()`, `insert_anomalies()`, `fetch_company()`
- You need **Jimmy's** `services/detector.py` for `AnomalyDetector.analyze_all()`
- You need **David's** `services/ai_forensic.py` for AI analysis
- You need **David's** `app.py` to register this screen

**You are the integration point for the entire data pipeline.** Your screen connects Parser → DB → Detector → AI in sequence. This means you should coordinate with everyone to make sure their interfaces are compatible.
