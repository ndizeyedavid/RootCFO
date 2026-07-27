"""Elyse: Anomaly dataclass + severity/type enums."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    

class AnomalyType(Enum):
    DUPLICATE = "duplicate"
    OFF_HOURS = "off_hours"
    BENFORD = "benford"
    VENDOR_PATTERN = "vendor_pattern"
    AMOUNT_THRESHOLD = "amount_threshold"
    AI_FLAGGED = "ai_flagged"
    


@dataclass
class Anomaly:
    id: Optional[int] = None
    company_id: int = 0
    transaction_id: int = 0
    anomaly_type: str = "unknown"
    severity: str = "info"
    description: str = ""
    ai_analysis: Optional[str] = None
    flagged_at: Optional[datetime] = None
 
    def __post_init__(self):
        if self.flagged_at is None:
            self.flagged_at = datetime.now()

    @property
    def severity_enum(self) -> Severity:
        return Severity(self.severity)
    @property
    def severity_color(self) -> str:
        return {
            Severity.CRITICAL: "critical",
            Severity.WARNING: "warning",   
            Severity.INFO: "info",     
        }[self.severity_enum]
