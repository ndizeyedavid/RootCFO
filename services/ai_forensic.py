"""David: Groq LLM integration — forensic analysis and follow-up chat.

Changes 2026-07-27: chunked AI analysis to avoid Groq 413 / TPM errors.
- ``analyze`` now splits anomalies into token-budgeted chunks, calls Groq
  for each chunk, and returns the concatenated report.
- ``analyze_and_assign`` writes both the aggregate report AND a
  per-chunk "narrow" narrative onto each anomaly's ``ai_analysis`` field
  so individual rows still show relevant context rather than the giant
  whole-run report.
- Prompt payload per chunk is compressed (no per-txn full ``to_dict``;
  only id/date/amount/account/description) to stay under token budget.
- Default chunk size is 50 anomalies per call (≈2.5–3k context + system
  prompt ≈ well under llama-3.1-8b-instant 6k TPM window).
"""

import json
import math
import time
from typing import Iterable, Optional

from groq import Groq
from groq import (
    APIError as GroqAPIError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)

from models.anomaly import Anomaly
from models.transaction import Transaction
from utils.config import Config


class APIError(Exception):
    """David: raise when Groq API call fails."""
    pass


DEFAULT_MODEL = Config.GROQ_MODEL
DEFAULT_TEMPERATURE = 0.2

# Chunking knobs. Conservative defaults for llama-3.1-8b-instant on-demand
# tier (6 000 TPM): each chunk call ≈ system prompt (500) + context (2500) +
# response (1500) ≈ 4500 tokens, well under 6k window per minute.
DEFAULT_ANOMALIES_PER_CHUNK = 50
DEFAULT_INTER_CHUNK_DELAY_SECONDS = 2.0  # simple pacing to stay under TPM cap

SYSTEM_PROMPT = (
    "You are a senior forensic accountant auditing a batch of flagged financial "
    "transactions. Your job for THIS BATCH is to produce a concise, structured "
    "forensic narrative covering: (1) what each anomaly in this batch means in "
    "plain business language, (2) the level of risk (low/medium/high) and why, "
    "(3) recommended next steps for the auditor (verify receipt, contact vendor, "
    "cross-check ledger entries, etc.). Mention patterns you see within this "
    "batch. Do not invent data that is not provided. Be concise but thorough."
)


class AIForensic:
    """David: Groq-powered forensic analysis and follow-up chat."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL,
                 anomalies_per_chunk: int = DEFAULT_ANOMALIES_PER_CHUNK,
                 inter_chunk_delay: float = DEFAULT_INTER_CHUNK_DELAY_SECONDS):
        """David: init Groq client with api_key (falls back to Config.GROQ_API_KEY).

        If no key is available, client is set to None and calls will raise APIError.
        """
        resolved_key = api_key if api_key is not None else Config.GROQ_API_KEY
        self.model = model
        self.temperature = DEFAULT_TEMPERATURE
        self.anomalies_per_chunk = int(anomalies_per_chunk or DEFAULT_ANOMALIES_PER_CHUNK)
        self.inter_chunk_delay = float(inter_chunk_delay or 0.0)
        self.client: Optional[Groq] = None
        if resolved_key:
            try:
                self.client = Groq(api_key=resolved_key)
            except Exception as exc:
                raise APIError(f"Failed to initialize Groq client: {exc}") from exc

    # ── Public API ────────────────────────────────────────────────────
    def analyze(self, anomalies: list[Anomaly],
                transactions: list[Transaction]) -> str:
        """Run chunked Groq analysis and return the concatenated report."""
        if not anomalies:
            return "No anomalies provided for analysis."

        if self.client is None:
            raise APIError("Groq client not initialized. Missing API key.")

        chunks = list(self._chunk_anomalies(anomalies, self.anomalies_per_chunk))
        parts: list[str] = []
        any_skipped = False
        for idx, batch in enumerate(chunks, start=1):
            header = (
                f"----- BATCH {idx}/{len(chunks)} "
                f"({len(batch)} anomalies of {len(anomalies)} total) -----"
            )
            prompt = self._build_chunk_prompt(batch, transactions,
                                              batch_index=idx,
                                              total_batches=len(chunks),
                                              total_anomalies=len(anomalies))
            try:
                content = self._call_groq(prompt)
            except APIError as exc:
                # If a single chunk fails we don't want to lose the whole
                # analysis — note the error inline and keep going with the
                # rest. The caller can decide how to react via the summary.
                any_skipped = True
                parts.append(header)
                parts.append(f"⚠ Analysis of this chunk skipped — {exc}")
                parts.append("")
                # Don't sleep after the LAST chunk (no subsequent call to pace)
                if self.inter_chunk_delay > 0 and idx < len(chunks):
                    time.sleep(self.inter_chunk_delay)
                continue
            parts.append(header)
            parts.append(content.strip())
            parts.append("")
            # Pace: don't hammer TPM across multiple chunks.
            if self.inter_chunk_delay > 0 and idx < len(chunks):
                time.sleep(self.inter_chunk_delay)

        if any_skipped and len(parts) >= 3 and len(chunks) > 1:
            # Put a top-of-report notice so auditors know this is partial.
            parts.insert(0, f"⚠ NOTICE: Some chunk(s) were skipped due to API errors. Report is partial — {len(chunks)} total chunks were processed.\n")

        return "\n".join(parts).strip()

    def analyze_and_assign(
        self,
        anomalies: list[Anomaly],
        transactions: list[Transaction],
    ) -> tuple[bool, str]:
        """Chunked analysis + writes per-anomaly + aggregate narratives.

        Returns:
            ``(success, summary)``. Success is True if **all** chunks
            returned non-empty content; False if any chunk was skipped or
            the client isn't configured. Summary is the aggregate report.
        """
        if not anomalies:
            return True, "No anomalies to analyze."

        if self.client is None:
            fallback = (
                "AI forensic analysis not available — Groq API key not configured. "
                "Set GROQ_API_KEY in your .env file to enable AI audit narratives."
            )
            for a in anomalies:
                a.ai_analysis = fallback
            return False, fallback

        chunks = list(self._chunk_anomalies(anomalies, self.anomalies_per_chunk))
        aggregate_parts: list[str] = []
        all_ok = True
        per_chunk_narratives: dict[int, str] = {}

        for idx, batch in enumerate(chunks, start=1):
            prompt = self._build_chunk_prompt(batch, transactions,
                                              batch_index=idx,
                                              total_batches=len(chunks),
                                              total_anomalies=len(anomalies))
            header = (
                f"----- BATCH {idx}/{len(chunks)} "
                f"({len(batch)} anomalies of {len(anomalies)} total) -----"
            )
            try:
                content = self._call_groq(prompt)
            except APIError as exc:
                all_ok = False
                fallback_chunk = f"⚠ Chunk {idx} analysis skipped — {exc}"
                per_chunk_narratives[idx] = fallback_chunk
                aggregate_parts.append(header)
                aggregate_parts.append(fallback_chunk)
                aggregate_parts.append("")
                if self.inter_chunk_delay > 0 and idx < len(chunks):
                    time.sleep(self.inter_chunk_delay)
                continue

            content_stripped = content.strip()
            per_chunk_narratives[idx] = content_stripped
            aggregate_parts.append(header)
            aggregate_parts.append(content_stripped)
            aggregate_parts.append("")
            if self.inter_chunk_delay > 0 and idx < len(chunks):
                time.sleep(self.inter_chunk_delay)

        aggregate_report = "\n".join(aggregate_parts).strip() or \
            "(Empty aggregate report)."

        # ── Assign narratives per anomaly ──────────────────────────────
        # Strategy: for each anomaly, pick the chunk-narrative of its
        # containing chunk as its narrow ai_analysis, then prepend a small
        # "chunk header" line so the user knows this analysis covers the
        # whole batch the row lived in. If we ever upgrade to per-anomaly
        # calls we can tighten this further, but this is safe and avoids
        # O(n) API calls while still being much more useful than dumping
        # the giant aggregate report on every row.
        for idx, batch in enumerate(chunks, start=1):
            chunk_header = (
                f"[AI analysis — batch {idx}/{len(chunks)}, "
                f"covers anomalies: "
                f"{self._anomaly_ids_preview(batch)}]\n\n"
            )
            chunk_narrative = per_chunk_narratives.get(idx, "")
            per_anomaly_text = chunk_header + chunk_narrative
            for a in batch:
                a.ai_analysis = per_anomaly_text or aggregate_report

        return all_ok, aggregate_report

    def chat(self, history: list[dict], question: str) -> str:
        """Append question to history → call Groq → return response text."""
        if not question.strip():
            return ""

        if self.client is None:
            raise APIError("Groq client not initialized. Missing API key.")

        messages = list(history) if history else []
        messages.append({"role": "user", "content": question})
        return self._call_groq_messages(messages)

    # ── Internals: Groq transport ────────────────────────────────────
    def _call_groq(self, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return self._call_groq_messages(messages)

    def _call_groq_messages(self, messages: list[dict]) -> str:
        if self.client is None:
            raise APIError("Groq client not initialized. Missing API key.")
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

    # ── Internals: chunking + payload compression ────────────────────
    @staticmethod
    def _chunk_anomalies(anomalies: list[Anomaly],
                         per_chunk: int) -> Iterable[list[Anomaly]]:
        if per_chunk <= 0:
            per_chunk = DEFAULT_ANOMALIES_PER_CHUNK
        n = len(anomalies)
        total_chunks = max(1, math.ceil(n / per_chunk))
        for i in range(total_chunks):
            start = i * per_chunk
            yield anomalies[start:start + per_chunk]

    @staticmethod
    def _anomaly_ids_preview(batch: list[Anomaly], limit: int = 6) -> str:
        ids = [str(getattr(a, "id", None) or "?") for a in batch]
        if len(ids) <= limit:
            return ", ".join(ids)
        return ", ".join(ids[:limit]) + f", ... ({len(ids)} total)"

    def _build_chunk_prompt(self,
                            batch: list[Anomaly],
                            transactions: list[Transaction],
                            *,
                            batch_index: int,
                            total_batches: int,
                            total_anomalies: int) -> str:
        """Per-chunk prompt: global summary once + compressed anomaly list."""
        tx_by_id = {tx.id: tx for tx in transactions}

        # Global summary: same every chunk so LLM has run-wide context.
        summary = {
            "total_transactions": len(transactions),
            "total_anomalies": total_anomalies,
            "total_batches": total_batches,
            "this_batch_index": batch_index,
            "this_batch_anomaly_count": len(batch),
            "anomaly_type_breakdown_overall": self._type_breakdown(
                # overall — call with batch? No — batch only, caller would have
                # to pass all anomalies. To keep the prompt small we only
                # send BATCH-LOCAL breakdown; LLM still gets aggregate counts.
                batch
            ),
            "severity_breakdown_this_batch": self._severity_breakdown(batch),
        }

        anomaly_payload = []
        for anomaly in batch:
            related_tx = tx_by_id.get(anomaly.transaction_id)
            tx_compact = None
            if related_tx is not None:
                tx_compact = {
                    "tx_id": getattr(related_tx, "id", None),
                    "date": str(getattr(related_tx, "date", "")),
                    "amount": float(getattr(related_tx, "amount", 0.0) or 0.0),
                    "account": str(getattr(related_tx, "account", "")),
                    "person": str(getattr(related_tx, "person", "")),
                    "description": str(getattr(related_tx, "description", "")),
                    "source_file": str(getattr(related_tx, "source_file", "")),
                }
            entry = {
                "anomaly_id": getattr(anomaly, "id", None),
                "tx_id": anomaly.transaction_id,
                "anomaly_type": anomaly.anomaly_type,
                "severity": anomaly.severity,
                "description": anomaly.description,
                "related_transaction": tx_compact,
            }
            anomaly_payload.append(entry)

        sections = []
        sections.append("=== GLOBAL AUDIT CONTEXT (run-wide) ===")
        sections.append(json.dumps(summary, separators=(",", ":"), default=str))
        sections.append("")
        sections.append(
            f"=== FLAGGED ANOMALIES — BATCH {batch_index}/{total_batches} "
            f"({len(batch)} records in this batch) ==="
        )
        sections.append(
            json.dumps(anomaly_payload, separators=(",", ":"), default=str)
        )
        sections.append("")
        sections.append(
            "Please produce a forensic audit report ONLY for the anomalies in "
            "this batch. Refer to anomalies by their anomaly_id. Start with a "
            "1-2 sentence pattern summary for this batch, then address each "
            "anomaly_id individually with meaning/risk/next-steps bullets."
        )
        return "\n".join(sections)

    # ── Helpers ───────────────────────────────────────────────────────
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
