"""Network condition monitor — probes API latency and classifies tiers."""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from collections import deque

import httpx

from config import settings
from models.enums import NetworkTier
from models.schemas import NetworkSnapshot

logger = logging.getLogger(__name__)

_WINDOW_SIZE = 10
_PROBE_INTERVAL = 30  # seconds between background probes
_FAST_PROBE_TIMEOUT = 2.0  # seconds


class NetworkMonitor:
    """Continuously assess network quality to the Mistral API."""

    def __init__(self) -> None:
        self._api_url = settings.MISTRAL_API_BASE.rstrip("/") + "/models"
        self._latency_window: deque[float] = deque(maxlen=_WINDOW_SIZE)
        self._error_window: deque[bool] = deque(maxlen=_WINDOW_SIZE)
        self._bg_task: asyncio.Task | None = None
        self._headers = {"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"}

    # ── Public API ────────────────────────────────────────────────────

    async def probe(self) -> NetworkSnapshot:
        """Execute a single latency probe and return the current snapshot."""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_FAST_PROBE_TIMEOUT) as client:
                await client.head(self._api_url, headers=self._headers)
            latency_ms = (time.monotonic() - start) * 1000
            self._latency_window.append(latency_ms)
            self._error_window.append(False)
        except Exception as exc:
            logger.debug("Network probe failed: %s", exc)
            self._latency_window.append(5000.0)  # Penalty
            self._error_window.append(True)

        return self._compute_snapshot()

    def get_cached_snapshot(self) -> NetworkSnapshot:
        """Return the latest snapshot without probing (for fast access)."""
        if not self._latency_window:
            # No data yet — assume GOOD as a safe default
            return NetworkSnapshot(
                avg_latency_ms=500.0, jitter_ms=0.0, error_rate=0.0, tier=NetworkTier.GOOD
            )
        return self._compute_snapshot()

    # ── Background Probing ────────────────────────────────────────────

    def start_background(self) -> None:
        """Start periodic background probing."""
        if self._bg_task is None or self._bg_task.done():
            self._bg_task = asyncio.create_task(self._background_loop())
            logger.info("Network monitor background probing started.")

    def stop_background(self) -> None:
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()

    async def _background_loop(self) -> None:
        while True:
            try:
                await self.probe()
                await asyncio.sleep(_PROBE_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Background probe error: %s", exc)
                await asyncio.sleep(_PROBE_INTERVAL)

    # ── Internal ──────────────────────────────────────────────────────

    def _compute_snapshot(self) -> NetworkSnapshot:
        latencies = list(self._latency_window)
        avg = statistics.mean(latencies) if latencies else 500.0
        jitter = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        error_rate = (
            sum(self._error_window) / len(self._error_window)
            if self._error_window
            else 0.0
        )
        tier = self._classify(avg, jitter, error_rate)
        return NetworkSnapshot(
            avg_latency_ms=round(avg, 1),
            jitter_ms=round(jitter, 1),
            error_rate=round(error_rate, 3),
            tier=tier,
        )

    @staticmethod
    def _classify(avg_ms: float, jitter_ms: float, error_rate: float) -> NetworkTier:
        if error_rate > 0.3 or avg_ms > 2000:
            return NetworkTier.POOR
        if avg_ms > 800 or jitter_ms > 500:
            return NetworkTier.FAIR
        if avg_ms > 300 or jitter_ms > 150:
            return NetworkTier.GOOD
        return NetworkTier.EXCELLENT


# Singleton
_monitor: NetworkMonitor | None = None


def get_network_monitor() -> NetworkMonitor:
    global _monitor
    if _monitor is None:
        _monitor = NetworkMonitor()
    return _monitor
