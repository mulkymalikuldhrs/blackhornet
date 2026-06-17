"""Cost/Usage Tracker — sub-agent 1.7.

Tracks token usage, latency, and estimated cost per LLM provider.
Persists usage history to a JSON state file for cross-session continuity.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

import logging

logger = logging.getLogger(__name__)

# Default per-provider cost in USD per 1K tokens (input / output).
# All free-tier providers default to $0.  Override via the dict below.
_PROVIDER_COSTS: dict[str, dict[str, float]] = {}


@dataclass
class UsageRecord:
    """A single LLM API call record.

    Attributes:
        provider: Provider name (e.g. ``"opencode_zen"``).
        model: Model identifier used for the call.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Sum of prompt and completion tokens.
        latency_ms: Round-trip latency in milliseconds.
        timestamp: ISO-8601 timestamp of when the call occurred.
        complexity: Complexity tier label for this request.
    """

    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    timestamp: str = ""
    complexity: str = ""


@dataclass
class ProviderStats:
    """Aggregated statistics for a single provider.

    Attributes:
        provider: Provider name.
        total_requests: Total number of recorded API calls.
        total_tokens: Sum of all tokens (prompt + completion).
        prompt_tokens: Sum of all prompt tokens.
        completion_tokens: Sum of all completion tokens.
        average_latency_ms: Mean latency across all requests.
        error_count: Number of failed requests.
        last_used: ISO-8601 timestamp of the most recent request.
        estimated_cost: Total estimated cost in USD (free tiers = $0).
    """

    provider: str
    total_requests: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    average_latency_ms: float = 0.0
    error_count: int = 0
    last_used: str = ""
    estimated_cost: float = 0.0


class CostTracker:
    """Tracks LLM usage and estimated cost across all providers.

    Usage records are accumulated in memory and persisted to a JSON file
    so that statistics survive process restarts.

    Args:
        state_file: Path to the JSON file for persisting usage data.
            The tilde character is expanded to the user's home directory.
    """

    def __init__(self, state_file: str = "~/.bh/data/cost_tracker.json") -> None:
        self._state_file = os.path.expanduser(state_file)
        self._history: list[UsageRecord] = []
        self._stats: dict[str, ProviderStats] = {}
        self._last_reset: str = ""
        self._load()

    # ── Public API ───────────────────────────────────────────────────────

    def record_usage(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        complexity: str = "",
    ) -> UsageRecord:
        """Record a single LLM API call.

        Computes total tokens and a UTC timestamp, updates in-memory
        statistics, and persists the state to disk.

        Args:
            provider: Provider name.
            model: Model identifier.
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            latency_ms: Request latency in milliseconds.
            complexity: Complexity tier label (optional).

        Returns:
            The created :class:`UsageRecord`.
        """
        total = prompt_tokens + completion_tokens
        now = datetime.now(timezone.utc).isoformat()

        record = UsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            latency_ms=latency_ms,
            timestamp=now,
            complexity=complexity,
        )

        self._history.append(record)
        self._update_stats(record)
        self._save()

        logger.debug(
            "usage_recorded",
            provider=provider,
            model=model,
            total_tokens=total,
            latency_ms=round(latency_ms, 1),
        )

        return record

    def get_provider_stats(self, name: str) -> Optional[ProviderStats]:
        """Get aggregated statistics for a specific provider.

        Args:
            name: Provider name.

        Returns:
            The :class:`ProviderStats` for the provider, or ``None`` if
            no usage has been recorded for it.
        """
        return self._stats.get(name)

    def get_all_stats(self) -> dict[str, ProviderStats]:
        """Get aggregated statistics for all providers.

        Returns:
            Dict mapping provider name to its :class:`ProviderStats`.
        """
        return dict(self._stats)

    def get_total_tokens(self) -> int:
        """Get the total token count across all providers and requests.

        Returns:
            Sum of all tokens recorded.
        """
        return sum(s.total_tokens for s in self._stats.values())

    def get_total_estimated_cost(self) -> float:
        """Get the total estimated cost across all providers.

        Uses the ``_PROVIDER_COSTS`` dict for per-model pricing when
        available; returns $0 for unlisted providers (free tier).

        Returns:
            Total estimated cost in USD.
        """
        return sum(s.estimated_cost for s in self._stats.values())

    def reset(self) -> None:
        """Clear all usage history and statistics.

        Resets in-memory state and overwrites the persisted file with an
        empty state.  The ``last_reset`` timestamp is updated to the
        current UTC time.
        """
        self._history.clear()
        self._stats.clear()
        self._last_reset = datetime.now(timezone.utc).isoformat()
        self._save()
        logger.info("cost_tracker_reset", timestamp=self._last_reset)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate the token count of a text string.

        Uses a simple heuristic: approximately 1 token per 4 characters
        for English text.  This is a rough estimate; actual tokenization
        depends on the specific model's tokenizer.

        Args:
            text: The input text string.

        Returns:
            Estimated number of tokens (always at least 1).
        """
        return max(1, len(text) // 4)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _update_stats(self, record: UsageRecord) -> None:
        """Update aggregated statistics with a new usage record.

        Args:
            record: The newly recorded usage.
        """
        stats = self._stats.get(record.provider)
        if stats is None:
            stats = ProviderStats(provider=record.provider)
            self._stats[record.provider] = stats

        prev_total = stats.total_requests
        stats.total_requests += 1
        stats.total_tokens += record.total_tokens
        stats.prompt_tokens += record.prompt_tokens
        stats.completion_tokens += record.completion_tokens
        stats.last_used = record.timestamp

        # Running average
        stats.average_latency_ms = (
            (stats.average_latency_ms * prev_total) + record.latency_ms
        ) / stats.total_requests

        # Cost estimation
        cost = self._estimate_call_cost(record)
        stats.estimated_cost += cost

    def _estimate_call_cost(self, record: UsageRecord) -> float:
        """Estimate the USD cost of a single API call.

        Looks up the provider in ``_PROVIDER_COSTS``.  If no pricing is
        configured, returns $0 (free tier assumption).

        Args:
            record: The usage record to estimate cost for.

        Returns:
            Estimated cost in USD.
        """
        rates = _PROVIDER_COSTS.get(record.provider)
        if rates is None:
            return 0.0
        input_cost = (record.prompt_tokens / 1000.0) * rates.get("input", 0.0)
        output_cost = (record.completion_tokens / 1000.0) * rates.get("output", 0.0)
        return input_cost + output_cost

    def _load(self) -> None:
        """Load persisted usage state from the JSON file.

        If the file does not exist or cannot be parsed, starts with an
        empty state.
        """
        if not os.path.isfile(self._state_file):
            logger.debug("cost_tracker_no_state_file", path=self._state_file)
            return

        try:
            with open(self._state_file) as f:
                data: dict[str, Any] = json.load(f)

            self._history = [UsageRecord(**r) for r in data.get("usage_history", [])]

            raw_stats: dict[str, dict[str, Any]] = data.get("provider_stats", {})
            self._stats = {
                name: ProviderStats(**s)
                for name, s in raw_stats.items()
            }

            self._last_reset = data.get("last_reset", "")

            logger.info(
                "cost_tracker_state_loaded",
                path=self._state_file,
                records=len(self._history),
                providers=len(self._stats),
            )

        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            logger.warning(
                "cost_tracker_state_load_failed",
                path=self._state_file,
                error=str(exc),
            )

    def _save(self) -> None:
        """Persist current usage state to the JSON file.

        Creates the parent directory if it does not exist.
        """
        state_dir = os.path.dirname(self._state_file)
        os.makedirs(state_dir, exist_ok=True)

        data: dict[str, Any] = {
            "usage_history": [asdict(r) for r in self._history],
            "provider_stats": {
                name: asdict(s)
                for name, s in self._stats.items()
            },
            "last_reset": self._last_reset or datetime.now(timezone.utc).isoformat(),
        }

        try:
            with open(self._state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("cost_tracker_state_saved", path=self._state_file)
        except OSError as exc:
            logger.error(
                "cost_tracker_state_save_failed",
                path=self._state_file,
                error=str(exc),
            )
