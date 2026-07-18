# Elyse => File Parsing & Anomaly Model

**Role:** You own two things — the data model for anomalies and the file parser that turns raw CSV/JSON files into clean Transaction objects.

---

## Your Files

| File                 | What it does                                                                   |
| -------------------- | ------------------------------------------------------------------------------ |
| `services/parser.py` | FileParser class — reads CSV/JSON, validates columns, returns Transaction list |
| `models/anomaly.py`  | Anomaly dataclass — used by Jimmy's detector and Calvin's report screen        |

---

## What To Build

### 1. `models/anomaly.py` (do this first — Jimmy needs it)

**Urgency:** HIGH — Jimmy's detector depends on this

---

### 2. `services/parser.py` — FileParser

**Urgency:** HIGH — Juliana's IngestionScreen calls this, Jimmy's detector needs data

**What it does:**

- Detect if a file is CSV or JSON
- Validate that required columns exist: `Date`, `Description`, `Amount`, `Account`, `Person`
- Parse each row into a `Transaction` object
- Handle errors gracefully (missing columns, bad data types)

---

## How To Test Your Work

1. Create a sample `test.csv` file with valid columns and a few rows
2. Call `FileParser.parse("test.csv")` → verify you get a list of Transaction objects
3. Break the CSV (remove a column) → verify `ParserError` is raised
4. Create a sample `test.json` → verify it parses correctly
5. Test with empty file → verify proper error

**Sample test data (save as `testing/sample.csv`):**

```csv
Date      , Description       , Amount  , Account              , Person
2026-01-15, Office Supplies   ,   150.00, Operating            , John Doe
2026-01-15, Consulting Fee    ,  5000.00, Professional Services, Jane Smith
2026-01-16, Office Supplies   ,   150.00, Operating            , John Doe
2026-01-17, Equipment Purchase, 25000.00, Capital Expenditure  , Jimmy
2026-01-18, Weekend Transfer  ,  3000.00, Operating            , Mary
2026-01-19, Consulting Fee    ,  5000.00, Professional Services, Jane Smith
```

---

## Dependencies

- You need **Jimmy's** `models/transaction.py` for the `Transaction.from_csv_row()` method
- Juliana's IngestionScreen will call your `FileParser.parse()` — coordinate with her on the interface
