"""Elyse: File parsing — reads CSV/JSON, validates, returns Transaction list."""

import pandas as pd
from pathlib import Path
from models.transaction import Transaction


class ParserError(Exception):
    """Elyse: raise when file cannot be parsed."""
    pass


class FileParser:
    """Elyse: Implement all methods below."""

    REQUIRED_COLUMNS = ["Date", "Description", "Amount", "Account", "Person"]

    @staticmethod
    def detect_format(filepath: str) -> str:
        """Elyse: check extension, return 'csv' or 'json', raise ParserError otherwise."""
        pass

    @staticmethod
    def validate_columns(df: pd.DataFrame):
        """Elyse: case-insensitive check. Raise ParserError if any required column missing."""
        pass

    @staticmethod
    def parse(filepath: str) -> list[Transaction]:
        """Elyse: detect format → read file → validate cols → build Transaction list.

        Skip rows with bad data (log warning). Raise ParserError if no valid rows.
        """
        pass
