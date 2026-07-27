import threading

import mysql.connector
from mysql.connector import Error
from utils.config import Config


class DatabaseError(Exception):
    pass


class DatabaseManager:

    def __init__(self):
        self._local = threading.local()

    # ── Connection ──────────────────────────────────────────────
    @property
    def connection(self):
        return getattr(self._local, "connection", None)

    @connection.setter
    def connection(self, value):
        self._local.connection = value

    @property
    def cursor(self):
        return getattr(self._local, "cursor", None)

    @cursor.setter
    def cursor(self, value):
        self._local.cursor = value

    def connect(self):
       
        self._close_quietly()
        try:
            self.connection = mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                autocommit=True,
                connection_timeout=5,
            )
            self.cursor = self.connection.cursor(dictionary=True, buffered=True)
        except Error as e:
            raise DatabaseError(f"Database connection failed: {e}")

    def _close_quietly(self):
        try:
            if self.cursor:
                self.cursor.close()
        except Exception:
            pass
        try:
            if self.connection:
                self.connection.close()
        except Exception:
            pass
        self.cursor = None
        self.connection = None

    def disconnect(self):
        self._close_quietly()

    # ── Generic query helpers ───────────────────────────────────
    def _run(self, method: str, query: str, params: tuple = None):
        for attempt in range(2):
            self.connect()
            try:
                self.cursor.execute(query, params)
                if method == "execute":
                    return self.cursor.lastrowid
                if method == "fetch_one":
                    return self.cursor.fetchone()
                return self.cursor.fetchall()
            except Error as e:
                msg = str(e)
                is_lost = any(k in msg for k in ("2013", "2006", "Lost connection", "gone away"))
                if attempt == 0 and is_lost:
                    continue
                raise DatabaseError(f"{method} failed: {e}")

    def execute_query(self, query: str, params: tuple = None):
        return self._run("execute", query, params)

    def fetch_all(self, query: str, params: tuple = None) -> list:
        return self._run("fetch_all", query, params)

    def fetch_one(self, query: str, params: tuple = None) -> dict:
        return self._run("fetch_one", query, params)


    # ── Users ───────────────────────────────────────────────────
    def insert_user(self, username: str, password_hash: str, company_id: int, role: str = "admin") -> int:
        """Insert user, return user id."""
        query = """
        INSERT INTO users (username, password_hash, company_id, role)
        VALUES (%s, %s, %s, %s)
        """

        return self.execute_query(
            query,
            (username, password_hash, company_id, role)
        )

    def update_user(self, user_id: int, data: dict):
        fields = []
        values = []

        for key, value in data.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.append(user_id)

        query = f"""
        UPDATE users
        SET {', '.join(fields)}
        WHERE id = %s
        """

        return self.execute_query(query, tuple(values))

    def fetch_users_by_company(self, company_id: int) -> list:
        """Return all users for a company (excludes password_hash)."""
        query = """
        SELECT id, username, role, created_at
        FROM users
        WHERE company_id = %s
        ORDER BY created_at ASC
        """

        return self.fetch_all(query, (company_id,))

    def fetch_user_by_username(self, username: str) -> dict:
        """Return user dict or None."""
        query = """
        SELECT *
        FROM users
        WHERE username = %s
        """

        return self.fetch_one(query, (username,))


    # ── Companies ───────────────────────────────────────────────
    def insert_company(self, name: str) -> int:
        """Insert company, return company id."""
        query = """
        INSERT INTO companies (name)
        VALUES (%s)
        """

        return self.execute_query(query, (name,))


    def update_company(self, company_id: int, data: dict):
        """Update company fields from dict."""
        fields = []
        values = []

        for key, value in data.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.append(company_id)

        query = f"""
        UPDATE companies
        SET {', '.join(fields)}
        WHERE id = %s
        """

        return self.execute_query(query, tuple(values))

    def fetch_company(self, company_id: int) -> dict:
        """Return company dict or None."""
        query = """
        SELECT *
        FROM companies
        WHERE id = %s
        """

        return self.fetch_one(query, (company_id,))

    # ── Transactions ────────────────────────────────────────────
    def insert_transactions(self, company_id: int, transactions: list) -> list[int]:
        ids = []

        query = """
        INSERT INTO transactions
        (company_id, date, description, amount, account, person, source_file)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        def _pick(obj, key, default=None):
            val = getattr(obj, key, None)
            if val is not None:
                return val
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        for transaction in transactions:

            values = (
                company_id,
                _pick(transaction, "date"),
                _pick(transaction, "description"),
                _pick(transaction, "amount"),
                _pick(transaction, "account"),
                _pick(transaction, "person"),
                _pick(transaction, "source_file")
            )

            ids.append(
                self.execute_query(query, values)
            )

        return ids


    def fetch_transactions(self, company_id: int) -> list:
        """Return all transactions for a company."""

        query = """
        SELECT *
        FROM transactions
        WHERE company_id = %s
        """

        return self.fetch_all(query, (company_id,))

    def count_transactions_by_source(self, company_id: int, source_file: str) -> int:
        """Return how many transactions already exist for a source file."""
        result = self.fetch_one(
            "SELECT COUNT(*) AS cnt FROM transactions WHERE company_id = %s AND source_file = %s",
            (company_id, source_file),
        )
        return result["cnt"] if result else 0

    def fetch_transaction(self, transaction_id: int) -> dict:
        """Return single transaction dict."""

        query = """
        SELECT *
        FROM transactions
        WHERE id = %s
        """

        return self.fetch_one(query, (transaction_id,))



    # ── Anomalies ───────────────────────────────────────────────
    def insert_anomalies(self, anomalies: list) -> list[int]:
        """Batch insert, return list of inserted ids."""
        ids = []

        query = """
        INSERT INTO anomalies
        (company_id, transaction_id, anomaly_type, severity, description)
        VALUES (%s,%s,%s,%s,%s)
        """

        for anomaly in anomalies:

            values = (
                anomaly.company_id,
                anomaly.transaction_id,
                anomaly.anomaly_type,
                anomaly.severity,
                anomaly.description
            )

            ids.append(
                self.execute_query(query, values)
            )

        return ids


    def fetch_anomalies(self, company_id: int) -> list:
        """Return all anomalies for a company."""
        query = """
        SELECT *
        FROM anomalies
        WHERE company_id = %s
        """

        return self.fetch_all(query, (company_id,))

    def fetch_anomaly(self, anomaly_id: int) -> dict:
        """Return single anomaly dict."""
        query = """
        SELECT *
        FROM anomalies
        WHERE id = %s
        """

        return self.fetch_one(query, (anomaly_id,))

    def update_anomaly_analysis(self, anomaly_id: int, analysis: str):
        """Save AI analysis text to anomaly record."""
        query = """
        UPDATE anomalies
        SET ai_analysis = %s
        WHERE id = %s
        """

        return self.execute_query(
            query,
            (analysis, anomaly_id)
        )

    def update_anomaly_analyses(self, anomalies: list):
        """Batch update AI analysis for multiple anomalies.

        Accepts Anomaly dataclasses (reads .ai_analysis, .id) OR dicts
        (reads ["ai_analysis"], ["id"]) so both pipeline and ad-hoc callers work.
        """
        query = """
        UPDATE anomalies
        SET ai_analysis = %s
        WHERE id = %s
        """

        def _pick(obj, key, default=None):
            val = getattr(obj, key, None)
            if val is not None:
                return val
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        for anomaly in anomalies:
            aid = _pick(anomaly, "id")
            analysis = _pick(anomaly, "ai_analysis")
            if aid is None or analysis is None:
                continue
            self.execute_query(
                query,
                (analysis, aid)
            )
