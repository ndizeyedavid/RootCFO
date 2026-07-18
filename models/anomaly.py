"""Elyse: Anomaly dataclass + severity/type enums."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class Severity(Enum):
    # Elyse: add CRITICAL, WARNING, INFO
    pass


class AnomalyType(Enum):
    # Elyse: add DUPLICATE, OFF_HOURS, BENFORD, VENDOR_PATTERN, AMOUNT_THRESHOLD, AI_FLAGGED
    pass


@dataclass
class Anomaly:
    """Elyse: Add fields: id, company_id, transaction_id, anomaly_type, severity, description, ai_analysis, flagged_at

    Add properties:
        severity_enum -> Severity
        severity_color -> str  (returns CSS class name)
    """
    pass
