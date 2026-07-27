"""Jimmy: Statistical anomaly detection engine."""

from collections import defaultdict
from datetime import time

from models.anomaly import Anomaly
from models.transaction import Transaction


class AnomalyDetector:
    """Detect suspicious transactions using simple statistical checks."""

    DEFAULT_BUSINESS_HOURS = "Mon-Fri 09:00-17:00"
    DEFAULT_AMOUNT_THRESHOLD = 10000.0

    def analyze_all(
        self,
        transactions: list[Transaction],
        business_hours: str | None = None,
        amount_threshold: float | None = None,
    ) -> list[Anomaly]:
        """Run all detectors and return combined deduplicated anomaly list.

        Args:
            transactions: list of Transaction objects (MUST have .id populated).
            business_hours: "Mon-Fri 09:00-17:00" style string or None for default.
            amount_threshold: RWF threshold above which to flag, or None for default.
        """
        bh = business_hours or self.DEFAULT_BUSINESS_HOURS
        threshold = amount_threshold if amount_threshold is not None else self.DEFAULT_AMOUNT_THRESHOLD

        seen: set[tuple[int, str]] = set()
        combined: list[Anomaly] = []
        sources = [
            self.find_duplicates(transactions),
            self.find_off_hours(transactions, bh),
            self.threshold_breaker(transactions, threshold),
            self.benfords_test(transactions),
        ]
        for bucket in sources:
            for anomaly in bucket:
                key = (anomaly.transaction_id, anomaly.anomaly_type)
                if key in seen:
                    continue
                seen.add(key)
                combined.append(anomaly)
        return combined

    def find_duplicates(self, transactions: list[Transaction]) -> list[Anomaly]:
        """Flag transactions that share the same description and amount."""
        anomalies = []
        grouped_transactions = defaultdict(list)

        for transaction in transactions:
            key = (transaction.description.strip().lower(), transaction.amount)
            grouped_transactions[key].append(transaction)

        for (description, amount), group in grouped_transactions.items():
            if len(group) < 2:
                continue

            for transaction in group:
                anomalies.append(
                    Anomaly(
                        company_id=transaction.company_id,
                        transaction_id=transaction.id,
                        anomaly_type="duplicate",
                        severity="warning",
                        description=(
                            f"Duplicate transaction: {description} for RWF {amount:.2f}"
                        ),
                    )
                )

        return anomalies

    def find_off_hours(
        self,
        transactions: list[Transaction],
        business_hours: str,
    ) -> list[Anomaly]:
        """Flag weekend transactions and transactions outside business hours."""
        anomalies = []

        try:
            day_part, time_part = business_hours.split()
            start_day_text, end_day_text = day_part.split("-")
            start_time_text, end_time_text = time_part.split("-")

            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            business_days = set(range(day_names.index(start_day_text), day_names.index(end_day_text) + 1))
            start_hour, start_minute = map(int, start_time_text.split(":"))
            end_hour, end_minute = map(int, end_time_text.split(":"))
            start_time = time(start_hour, start_minute)
            end_time = time(end_hour, end_minute)
        except ValueError:
            return anomalies

        for transaction in transactions:
            transaction_day = transaction.timestamp.weekday()
            transaction_time = transaction.timestamp.time()

            if transaction_day not in business_days:
                anomalies.append(
                    Anomaly(
                        company_id=transaction.company_id,
                        transaction_id=transaction.id,
                        anomaly_type="off_hours",
                        severity="info",
                        description="Transaction happened outside business days.",
                    )
                )
                continue

            if transaction_time < start_time or transaction_time > end_time:
                anomalies.append(
                    Anomaly(
                        company_id=transaction.company_id,
                        transaction_id=transaction.id,
                        anomaly_type="off_hours",
                        severity="info",
                        description="Transaction happened outside business hours.",
                    )
                )

        return anomalies

    def benfords_test(self, transactions: list[Transaction]) -> list[Anomaly]:
        """Check whether first-digit distribution follows Benford's Law.

        Returns at most ONE anomaly — Benford's Law is a dataset-level test,
        not a per-transaction flag. If the distribution deviates significantly,
        a single summary anomaly is produced.
        """
        if len(transactions) < 50:
            return []

        digits: dict[int, int] = defaultdict(int)

        for transaction in transactions:
            amount = abs(int(transaction.amount))
            if amount == 0:
                continue
            first_digit = int(str(amount)[0])
            if 1 <= first_digit <= 9:
                digits[first_digit] += 1

        total = sum(digits.values())
        if total < 50:
            return []

        expected_distribution = {
            1: 0.301,
            2: 0.176,
            3: 0.125,
            4: 0.097,
            5: 0.079,
            6: 0.067,
            7: 0.058,
            8: 0.051,
            9: 0.046,
        }

        chi_square = 0.0
        for digit, expected_ratio in expected_distribution.items():
            expected_count = expected_ratio * total
            observed_count = digits.get(digit, 0)
            if expected_count > 0:
                chi_square += (observed_count - expected_count) ** 2 / expected_count

        if chi_square < 15.51:
            return []

        observed_pct = {
            d: round(digits.get(d, 0) / total * 100, 1) for d in range(1, 10)
        }
        expected_pct = {
            d: round(expected_distribution[d] * 100, 1) for d in range(1, 10)
        }
        biggest_digit = max(range(1, 10), key=lambda d: abs(digits.get(d, 0) / total - expected_distribution[d]))

        first = transactions[0]
        return [
            Anomaly(
                company_id=first.company_id,
                transaction_id=first.id,
                anomaly_type="benford",
                severity="warning",
                description=(
                    f"Benford's Law deviation detected (χ²={chi_square:.1f}). "
                    f"Most skewed digit: {biggest_digit} "
                    f"(observed {observed_pct[biggest_digit]}% vs expected {expected_pct[biggest_digit]}%). "
                    f"First-digit distribution does not match the expected Benford pattern "
                    f"across {total} transactions."
                ),
            )
        ]

    def threshold_breaker(
        self,
        transactions: list[Transaction],
        threshold: float = 10000.0,
    ) -> list[Anomaly]:
        """Flag transactions that go over the amount threshold."""
        anomalies = []

        for transaction in transactions:
            if transaction.amount > threshold:
                anomalies.append(
                    Anomaly(
                        company_id=transaction.company_id,
                        transaction_id=transaction.id,
                        anomaly_type="amount_threshold",
                        severity="warning",
                        description=f"Transaction amount RWF {transaction.amount:.2f} is above the threshold.",
                    )
                )

        return anomalies
