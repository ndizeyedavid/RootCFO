"""Jimmy: Transaction dataclass — core financial record model."""

from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime, date


@dataclass
class Transaction:
    """Represents a single financial transaction in the system.
    
    This is the core data model used throughout RootCFO by parser, detector,
    database, and all UI screens. All financial data flows through this structure.
    
    Attributes:
        id: Unique transaction identifier
        company_id: Foreign key to the Company that owns this transaction
        description: Transaction memo, narrative, or description
        amount: Transaction amount in base currency (float)
        date: Transaction date only (for off-hours detection, weekend checks)
        timestamp: Full datetime of transaction (for precise off-hours checking)
        category: Transaction type (e.g., "expense", "revenue", "transfer")
        account: Source or destination account name/code
        person: Person/vendor associated with transaction (optional)
        source_file: Original file name this transaction was ingested from
        ingested_at: Timestamp when transaction was parsed and stored
    """
    id: int
    company_id: int
    description: str
    amount: float
    date: date
    timestamp: datetime
    category: str
    account: str
    person: Optional[str] = None
    source_file: Optional[str] = None
    ingested_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate and normalize transaction data."""
        if self.amount < 0:
            raise ValueError(f"Transaction amount must be non-negative, got {self.amount}")
        if self.company_id <= 0:
            raise ValueError(f"Company ID must be positive, got {self.company_id}")
        if self.ingested_at is None:
            self.ingested_at = datetime.now()

    @classmethod
    def from_csv_row(cls, row: dict, company_id: int, source_file: str = None) -> "Transaction":
        """Create a Transaction from a CSV/dict row.
        
        Args:
            row: Dictionary with keys: description, amount, date, category, account, person
            company_id: Which company this transaction belongs to
            source_file: Name of the source CSV/JSON file
            
        Returns:
            Transaction instance
        """
        # Parse date and create timestamp
        if isinstance(row.get("date"), str):
            parsed_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        else:
            parsed_date = row.get("date")
        
        # If timestamp not provided, use date with midnight time
        if "timestamp" in row and row["timestamp"]:
            if isinstance(row["timestamp"], str):
                timestamp = datetime.fromisoformat(row["timestamp"])
            else:
                timestamp = row["timestamp"]
        else:
            timestamp = datetime.combine(parsed_date, datetime.min.time())
        
        return cls(
            id=row.get("id", 0),  # Will be assigned by DB
            company_id=company_id,
            description=str(row.get("description", "")).strip(),
            amount=float(row.get("amount", 0)),
            date=parsed_date,
            timestamp=timestamp,
            category=str(row.get("category", "other")).strip().lower(),
            account=str(row.get("account", "")).strip(),
            person=row.get("person"),
            source_file=source_file,
        )

    def to_dict(self) -> dict:
        """Convert Transaction to dictionary (JSON-serializable).
        
        Returns:
            Dictionary representation of transaction
        """
        data = asdict(self)
        # Convert date/datetime objects to ISO format strings
        if isinstance(data["date"], date):
            data["date"] = data["date"].isoformat()
        if isinstance(data["timestamp"], datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        if isinstance(data["ingested_at"], datetime):
            data["ingested_at"] = data["ingested_at"].isoformat()
        return data

    def __str__(self) -> str:
        """Human-readable transaction summary."""
        return (f"Transaction(id={self.id}, company={self.company_id}, "
                f"desc='{self.description}', amt=RWF {self.amount:.2f}, date={self.date})")
