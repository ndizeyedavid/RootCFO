# Priscilla => Database & Configuration

**Role:** You own the foundation — database connection, CRUD operations, and configuration management. Every other team member depends on your code to store and retrieve data.

---

## Your Files

| File              | What it does                                                                 |
| ----------------- | ---------------------------------------------------------------------------- |
| `services/db.py`  | DatabaseManager class — connects to MySQL, runs queries, CRUD for all tables |
| `utils/config.py` | Loads environment variables (DB credentials, Groq API key) from `.env`       |

---

## What To Build

### 1. `utils/config.py` (quick — do this first)

**Urgency:** HIGH — every module that connects to DB or API needs this

### 2. `services/db.py` — DatabaseManager

**Urgency:** HIGH — everyone needs to store/retrieve data

This is the biggest file you'll write. It needs methods for every table and also:

**1. Connection management:**

**2. CRUD methods you need to implement:**

---

## How Your Code Gets Used

Here's how other team members call your code:

- **Bruce** calls: `db.insert_user()`, `db.insert_company()`, `db.update_company()`, `db.fetch_user_by_username()`
- **Juliana** calls: `db.insert_transactions()`, `db.insert_anomalies()`, `db.fetch_company()`
- **Calvin** calls: `db.fetch_anomalies()`, `db.fetch_anomaly()`, `db.fetch_transaction()`, `db.update_anomaly_analysis()`
- **David** might call: `db.fetch_company()` for dashboard stats

---

## Dependencies

- You need **Juliana's** `sql/schema.sql` to have created the tables first
- No one else's code is needed — you can build and test independently
- Your `.env` file must have valid Aiven credentials (David will provide these)
