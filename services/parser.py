"""Elyse: File parsing — reads CSV/JSON, validates, returns Transaction list."""

import logging
import pandas as pd
from pathlib import Path
from typing import Optional

from models.transaction import Transaction

logger = logging.getLogger(__name__)


class ParserError(Exception):
    def __init__(self, message: str, row_errors: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.row_errors = row_errors or []


class FileParser:

    REQUIRED_COLUMNS = ["Date", "Description", "Amount", "Account", "Person"]

    @staticmethod
    def detect_format(filepath: str) -> str:
        ext = Path(filepath).suffix.lower()
        if ext == ".csv":
            return "csv"
        if ext == ".json":
            return "json"
        raise ParserError(f"Unsupported file format '{ext}'. Use .csv or .json.")

    @staticmethod
    def validate_columns(df: pd.DataFrame):
        normalized = {str(col).strip().lower(): col for col in df.columns}
        missing = [
            col for col in FileParser.REQUIRED_COLUMNS
            if col.lower() not in normalized
        ]
        if missing:
            raise ParserError(
                f"Missing required column(s): {', '.join(missing)}. "
                f"Found columns: {', '.join(str(c) for c in df.columns)}"
            )
        rename_map = {
            normalized[col.lower()]: col for col in FileParser.REQUIRED_COLUMNS
        }
        df.rename(columns=rename_map, inplace=True)

    @staticmethod
    def parse(filepath: str, company_id: int = 0,
              source_file: Optional[str] = None) -> list[Transaction]:
        path = Path(filepath)
        if not path.exists():
            raise ParserError(f"File not found: {filepath}")

        if path.stat().st_size == 0:
            raise ParserError(f"File is empty: {filepath}")

        file_format = FileParser.detect_format(filepath)
        source_name = source_file or path.name

        try:
            if file_format == "csv":
                df = pd.read_csv(path, skipinitialspace=True)
                for col in df.select_dtypes(include="object").columns:
                    df[col] = df[col].astype(str).str.strip()
            else:
                df = pd.read_json(path)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as e:
            raise ParserError(f"Could not read '{filepath}': {e}")

        if df.empty:
            raise ParserError(f"File contains no rows: {filepath}")

        FileParser.validate_columns(df)

        transactions: list[Transaction] = []
        for idx, row in df.iterrows():
            try:
                normalized = {str(k).strip().lower(): v for k, v in row.to_dict().items()}
                transactions.append(
                    Transaction.from_csv_row(normalized, company_id=company_id,
                                             source_file=source_name)
                )
            except (ValueError, KeyError, TypeError) as e:
                logger.warning("Skipping row %d in '%s': %s", idx + 2, filepath, e)

        if not transactions:
            raise ParserError(f"No valid rows could be parsed from '{filepath}'.")

        return transactions
