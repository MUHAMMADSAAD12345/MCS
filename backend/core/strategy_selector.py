"""Reasoning strategy selector — decision matrix combining network tier + query complexity."""

from __future__ import annotations

import logging

from models.enums import ComplexityTier, NetworkTier, ReasoningMode
from models.schemas import ComplexityResult, NetworkSnapshot

logger = logging.getLogger(__name__)

# Decision matrix: (NetworkTier, ComplexityTier) → ReasoningMode
_DECISION_MATRIX: dict[tuple[NetworkTier, ComplexityTier], ReasoningMode] = {
    (NetworkTier.POOR, ComplexityTier.LOW): ReasoningMode.FAST,
    (NetworkTier.POOR, ComplexityTier.MEDIUM): ReasoningMode.FAST,
    (NetworkTier.POOR, ComplexityTier.HIGH): ReasoningMode.FAST,
    (NetworkTier.FAIR, ComplexityTier.LOW): ReasoningMode.FAST,
    (NetworkTier.FAIR, ComplexityTier.MEDIUM): ReasoningMode.STANDARD,
    (NetworkTier.FAIR, ComplexityTier.HIGH): ReasoningMode.STANDARD,
    (NetworkTier.GOOD, ComplexityTier.LOW): ReasoningMode.STANDARD,
    (NetworkTier.GOOD, ComplexityTier.MEDIUM): ReasoningMode.STANDARD,
    (NetworkTier.GOOD, ComplexityTier.HIGH): ReasoningMode.DEEP,
    (NetworkTier.EXCELLENT, ComplexityTier.LOW): ReasoningMode.STANDARD,
    (NetworkTier.EXCELLENT, ComplexityTier.MEDIUM): ReasoningMode.DEEP,
    (NetworkTier.EXCELLENT, ComplexityTier.HIGH): ReasoningMode.DEEP,
}


class StrategySelector:
    """Select reasoning mode based on network conditions and query complexity."""

    def select(
        self,
        network: NetworkSnapshot,
        complexity: ComplexityResult,
        user_override: ReasoningMode | None = None,
    ) -> ReasoningMode:
        # User can force a specific mode
        if user_override and user_override != ReasoningMode.AUTO:
            logger.info("Mode override by user: %s", user_override.value)
            return user_override

        key = (network.tier, complexity.tier)
        mode = _DECISION_MATRIX.get(key, ReasoningMode.STANDARD)

        logger.info(
            "Strategy selected: network=%s complexity=%s(%.2f) → mode=%s",
            network.tier.value,
            complexity.tier.value,
            complexity.score,
            mode.value,
        )
        return mode


# Singleton
_selector: StrategySelector | None = None


def get_strategy_selector() -> StrategySelector:
    global _selector
    if _selector is None:
        _selector = StrategySelector()
    return _selector
