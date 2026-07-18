"""Jimmy: Transaction dataclass — core financial record model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:
    """Jimmy: Add fields: id, company_id, date, description, amount, account, person, source_file, ingested_at

    Add classmethod:
        from_csv_row(row: dict) -> Transaction
    Add method:
        to_dict() -> dict
    """
    pass
