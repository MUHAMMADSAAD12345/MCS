"""Circuit breaker to protect against cascading failures from external services."""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"           # Normal operation
    OPEN = "open"               # Blocking calls
    HALF_OPEN = "half_open"     # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when the circuit is open and calls are blocked."""


class CircuitBreaker:
    """
    Prevents cascading failures by tracking error counts and opening
    the circuit when a threshold is exceeded.

    Usage:
        breaker = CircuitBreaker("mistral")
        result = await breaker.call(some_async_function, arg1, arg2)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed → transition to half-open
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit breaker."""
        async with self._lock:
            current = self.state
            if current == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit '{self.name}' is OPEN — calls blocked for "
                    f"{self.recovery_timeout}s after {self.failure_threshold} failures."
                )

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            await self._record_failure()
            raise exc
        else:
            await self._record_success()
            return result

    async def _record_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' OPENED after %d failures.",
                    self.name,
                    self._failure_count,
                )

    async def _record_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit '%s' recovered → CLOSED.", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0


# Shared instances per service
_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name)
    return _breakers[name]
