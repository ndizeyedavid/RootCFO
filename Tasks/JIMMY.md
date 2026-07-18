# Jimmy => Anomaly Detection Engine

**Role:** You own the brain of RootCFO — the statistical engine that finds suspicious transactions. You also define the Transaction data model that everyone else depends on.

---

## Your Files

| File                    | What it does                                                                              |
| ----------------------- | ----------------------------------------------------------------------------------------- |
| `services/detector.py`  | AnomalyDetector class — duplicate detection, off-hours, Benford's Law, threshold breaking |
| `models/transaction.py` | Transaction dataclass — the core data model used by parser, detector, DB, and all screens |

---

## What To Build

### 1. `models/transaction.py` (do this first — Elyse and Jimmy need it)

**Urgency:** HIGH — everyone downstream depends on this

A simple dataclass that represents a single financial transaction:

---

### 2. `services/detector.py` — AnomalyDetector class

**Urgency:** HIGH — core feature, needed for demo

**What each method does:**

#### `find_duplicates(transactions)`

Group transactions by (description, amount). Any group with more than 1 transaction is a duplicate anomaly.

#### `find_off_hours(transactions, business_hours)`

Parse business hours string (e.g., "Mon-Fri 8:00-17:00") and flag transactions whose timestamps fall outside.

**Pro tip:** For a real prototype, you can assume transactions arrive with date only (no time). Weekend detection is the simplest off-hours check. If time data is available, check for hours outside 8:00-17:00 too.

#### `benfords_test(transactions)`

Benford's Law says the first digit of real-world numbers follows a predictable distribution (digit 1 appears ~30% of the time, digit 9 appears ~5%). Significant deviation suggests manipulated data.

#### `threshold_breaker(transactions, threshold=10000)`

Flag any transaction above the threshold amount.

---

## Dependencies

- You need `models/anomaly.py` from **Elyse** — wait for her to define the `Anomaly` dataclass first
- You can build `models/transaction.py` immediately — no dependencies
