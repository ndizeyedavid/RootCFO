"""David: Groq LLM integration — forensic analysis and follow-up chat."""

import json
from typing import Optional

from groq import Groq
from groq import APIError as GroqAPIError, APIConnectionError, RateLimitError, InternalServerError

from models.anomaly import Anomaly
from models.transaction import Transaction
from utils.config import Config


class APIError(Exception):
    """David: raise when Groq API call fails."""
    pass


DEFAULT_MODEL = Config.GROQ_MODEL
DEFAULT_TEMPERATURE = 0.2

SYSTEM_PROMPT = (
    "You are a senior forensic accountant auditing a set of financial transactions "
    "that have been flagged as anomalous. Your job is to produce a clear, structured "
    "narrative describing: (1) what each anomaly means in plain business language, "
    "(2) the level of risk (low / medium / high) and why, (3) recommended next steps "
    "for the auditor (e.g., verify receipt, contact vendor, cross-check ledger entries). "
    "Be concise but thorough. Address each anomaly explicitly. Mention any patterns you "
    "see across the flagged set. Use professional but accessible language — no jargon "
    "walls. Do not invent data that is not provided."
)


class AIForensic:
    """David: Groq-powered forensic analysis and follow-up chat."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """David: init Groq client with api_key (falls back to Config.GROQ_API_KEY).

        If no key is available, client is set to None and calls will raise APIError.
        """
        resolved_key = api_key if api_key is not None else Config.GROQ_API_KEY
        self.model = model
        self.temperature = DEFAULT_TEMPERATURE
        self.client: Optional[Groq] = None
        if resolved_key:
            try:
                self.client = Groq(api_key=resolved_key)
            except Exception as exc:
                raise APIError(f"Failed to initialize Groq client: {exc}") from exc

    def analyze(self, anomalies: list[Anomaly],
                transactions: list[Transaction]) -> str:
        """David: build structured prompt → call Groq → return narrative string.

        Handle connection errors, rate limits, API errors — wrap in APIError.
        """
        if not anomalies:
            return "No anomalies provided for analysis."

        if self.client is None:
            raise APIError("Groq client not initialized. Missing API key.")

        prompt = self._build_prompt(anomalies, transactions)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
        except APIConnectionError as exc:
            raise APIError(f"Groq connection failed: {exc}") from exc
        except RateLimitError as exc:
            raise APIError(f"Groq rate limit exceeded: {exc}") from exc
        except InternalServerError as exc:
            raise APIError(f"Groq server error: {exc}") from exc
        except GroqAPIError as exc:
            raise APIError(f"Groq API error: {exc}") from exc
        except Exception as exc:
            raise APIError(f"Unexpected Groq error: {exc}") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as exc:
            raise APIError(f"Malformed Groq response: {exc}") from exc

        if not content:
            raise APIError("Groq returned empty response.")

        return content

    def chat(self, history: list[dict], question: str) -> str:
        """David: append question to history → call Groq → return response.

        Args:
            history: list of message dicts with keys "role" and "content".
                     Assumes caller already included any system prompt.
            question: the next user question to send.

        Returns:
            Assistant reply text.
        """
        if not question.strip():
            return ""

        if self.client is None:
            raise APIError("Groq client not initialized. Missing API key.")

        messages = list(history) if history else []
        messages.append({"role": "user", "content": question})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
        except APIConnectionError as exc:
            raise APIError(f"Groq connection failed: {exc}") from exc
        except RateLimitError as exc:
            raise APIError(f"Groq rate limit exceeded: {exc}") from exc
        except InternalServerError as exc:
            raise APIError(f"Groq server error: {exc}") from exc
        except GroqAPIError as exc:
            raise APIError(f"Groq API error: {exc}") from exc
        except Exception as exc:
            raise APIError(f"Unexpected Groq error: {exc}") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as exc:
            raise APIError(f"Malformed Groq response: {exc}") from exc

        if not content:
            raise APIError("Groq returned empty response.")

        return content

    def _build_prompt(self, anomalies: list[Anomaly],
                      transactions: list[Transaction]) -> str:
        """David: construct forensic accountant prompt from anomaly + transaction data."""
        tx_by_id = {tx.id: tx for tx in transactions}

        anomaly_payload = []
        for anomaly in anomalies:
            related_tx = tx_by_id.get(anomaly.transaction_id)
            entry = {
                "anomaly_id": getattr(anomaly, "id", None),
                "anomaly_type": anomaly.anomaly_type,
                "severity": anomaly.severity,
                "description": anomaly.description,
                "flagged_at": anomaly.flagged_at.isoformat() if anomaly.flagged_at else None,
                "related_transaction": (
                    related_tx.to_dict() if related_tx is not None else None
                ),
            }
            anomaly_payload.append(entry)

        summary = {
            "total_transactions": len(transactions),
            "total_anomalies": len(anomalies),
            "anomaly_type_breakdown": self._type_breakdown(anomalies),
            "severity_breakdown": self._severity_breakdown(anomalies),
        }

        sections = []
        sections.append("=== AUDIT CONTEXT SUMMARY ===")
        sections.append(json.dumps(summary, indent=2, default=str))
        sections.append("")
        sections.append("=== FLAGGED ANOMALIES WITH RELATED TRANSACTIONS ===")
        sections.append(json.dumps(anomaly_payload, indent=2, default=str))
        sections.append("")
        sections.append(
            "Please produce your forensic audit report for the anomalies above."
        )
        return "\n".join(sections)

    @staticmethod
    def _type_breakdown(anomalies: list[Anomaly]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in anomalies:
            counts[a.anomaly_type] = counts.get(a.anomaly_type, 0) + 1
        return counts

    @staticmethod
    def _severity_breakdown(anomalies: list[Anomaly]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in anomalies:
            counts[a.severity] = counts.get(a.severity, 0) + 1
        return counts