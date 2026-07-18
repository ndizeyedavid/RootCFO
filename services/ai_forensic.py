"""David: Groq LLM integration — forensic analysis and follow-up chat."""

import os
from groq import Groq

from models.anomaly import Anomaly
from models.transaction import Transaction


class APIError(Exception):
    """David: raise when Groq API call fails."""
    pass


class AIForensic:
    """David: Implement all methods below."""

    def __init__(self, api_key: str = None):
        """David: init Groq client with api_key (falls back to Config.GROQ_API_KEY)."""
        pass

    def analyze(self, anomalies: list[Anomaly],
                transactions: list[Transaction]) -> str:
        """David: build structured prompt → call Groq → return narrative string.

        Handle connection errors, rate limits, API errors — wrap in APIError.
        """
        pass

    def chat(self, history: list[dict], question: str) -> str:
        """David: append question to history → call Groq → return response."""
        pass

    def _build_prompt(self, anomalies: list[Anomaly],
                      transactions: list[Transaction]) -> str:
        """David: construct forensic accountant prompt from anomaly + transaction data."""
        pass
