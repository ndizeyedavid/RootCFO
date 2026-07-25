"""Priscilla: MySQL database connection and CRUD operations."""

import mysql.connector
from mysql.connector import Error
from utils.config import Config


class DatabaseError(Exception):
    pass


class DatabaseManager:
    """Priscilla: Implements all methods below."""

    def __init__(self):
        self.connection = None
        self.cursor = None

    # ── Connection ──────────────────────────────────────────────
    def connect(self):
        """Establish MySQL connection using Config values."""
        try:
            self.connection = mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )

            self.cursor = self.connection.cursor(dictionary=True)

        except Error as e:
            raise DatabaseError(f"Database connection failed: {e}")



    def disconnect(self):
        """Close cursor and connection."""
        if self.cursor:
            self.cursor.close()

        if self.connection:
            self.connection.close()


    # ── Generic query helpers ───────────────────────────────────
    def execute_query(self, query: str, params: tuple = None):
        """Execute INSERT/UPDATE/DELETE with params, commit."""
        try:
            if not self.connection:
                self.connect()

            self.cursor.execute(query, params)
            self.connection.commit()

            return self.cursor.lastrowid

        except Error as e:
            if self.connection:
                self.connection.rollback()
            raise DatabaseError(f"Query failed: {e}")


    def fetch_all(self, query: str, params: tuple = None) -> list:
        """Return all rows as list of dicts."""
        try:
            if not self.connection:
                self.connect()

            self.cursor.execute(query, params)

            return self.cursor.fetchall()

        except Error as e:
            raise DatabaseError(f"Fetch failed: {e}")

    def fetch_one(self, query: str, params: tuple = None) -> dict:
        """Return single row as dict."""
        try:
            if not self.connection:
                self.connect()

            self.cursor.execute(query, params)

            return self.cursor.fetchone()

        except Error as e:
            raise DatabaseError(f"Fetch failed: {e}")


    # ── Users ───────────────────────────────────────────────────
    def insert_user(self, username: str, password_hash: str, company_id: int) -> int:
        """Insert user, return user id."""
        query = """
        INSERT INTO users (username, password_hash, company_id)
        VALUES (%s, %s, %s)
        """

        return self.execute_query(
            query,
            (username, password_hash, company_id)
        )

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
        """Batch insert, return list of inserted ids."""
        ids = []

        query = """
        INSERT INTO transactions
        (company_id, date, description, amount, account, person, source_file)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        for transaction in transactions:

            values = (
                company_id,
                transaction.get("date"),
                transaction.get("description"),
                transaction.get("amount"),
                transaction.get("account"),
                transaction.get("person"),
                transaction.get("source_file")
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
        """Batch update AI analysis for multiple anomalies."""
        query = """
        UPDATE anomalies
        SET ai_analysis = %s
        WHERE id = %s
        """

        for anomaly in anomalies:
            self.execute_query(
                query,
                (
                    anomaly["ai_analysis"],
                    anomaly["id"]
                )
            )
