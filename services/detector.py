"""Jimmy: Statistical anomaly detection engine."""

from models.transaction import Transaction
from models.anomaly import Anomaly


class AnomalyDetector:
    """Jimmy: Implement all methods below."""

    def find_duplicates(self, transactions: list[Transaction]) -> list[Anomaly]:
        """Jimmy: group by (description, amount), flag groups with count > 1."""
        pass

    def find_off_hours(self, transactions: list[Transaction],
                       business_hours: str) -> list[Anomaly]:
        """Jimmy: flag weekend transactions + transactions outside business hours."""
        pass

    def benfords_test(self, transactions: list[Transaction]) -> list[Anomaly]:
        """Jimmy: compute first-digit frequencies, compare vs Benford distribution.

        Flag digits where deviation > 10%.
        """
        pass

    def threshold_breaker(self, transactions: list[Transaction],
                          threshold: float = 10000.0) -> list[Anomaly]:
        """Jimmy: flag transactions where amount > threshold."""
        pass

    def analyze_all(self, transactions: list[Transaction],
                    business_hours: str = "Mon-Fri 8:00-17:00",
                    threshold: float = 10000.0) -> list[Anomaly]:
        """Jimmy: run all checks, return aggregated anomaly list."""
        pass
