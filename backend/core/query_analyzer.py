"""Query complexity analyzer — heuristic-based, no LLM call needed."""

from __future__ import annotations

import re

from models.enums import ComplexityTier
from models.schemas import ComplexityResult

# Keywords that signal analytical / complex queries
ANALYTICAL_KEYWORDS = [
    "compare",
    "contrast",
    "analyze",
    "evaluate",
    "explain why",
    "trade-off",
    "trade-offs",
    "pros and cons",
    "advantages and disadvantages",
    "step by step",
    "in detail",
    "comprehensive",
    "implications",
    "relationship between",
    "how does",
    "what are the differences",
    "critically",
    "discuss",
    "elaborate",
]

# Weights for each signal (must sum to 1.0)
WEIGHTS = {
    "length": 0.20,
    "questions": 0.10,
    "analytical": 0.25,
    "domain": 0.15,
    "instruction": 0.15,
    "doc_reference": 0.15,
}

# Instruction verbs that indicate chain-of-actions
COMPLEX_INSTRUCTION_PATTERNS = [
    r"\b(first|then|after that|finally|next|also|additionally)\b",
    r"\b(if|unless|otherwise|depending)\b",
    r"\b(create|generate|write|build|make)\b.*\b(and|then|also)\b",
]

# Words that hint the user is referencing uploaded documents
DOC_REFERENCE_PATTERNS = [
    r"\b(document|file|pdf|uploaded|attachment|my file|the doc)\b",
    r"\b(based on|according to|from the|in the)\b.*\b(document|file|pdf|text)\b",
]


class QueryComplexityAnalyzer:
    """Classify a user query into LOW / MEDIUM / HIGH complexity using local heuristics."""

    def analyze(self, query: str) -> ComplexityResult:
        query_lower = query.lower().strip()
        signals = {
            "length": self._score_length(query_lower),
            "questions": self._score_question_count(query_lower),
            "analytical": self._score_analytical(query_lower),
            "domain": self._score_domain(query_lower),
            "instruction": self._score_instruction(query_lower),
            "doc_reference": self._score_doc_reference(query_lower),
        }
        weighted = sum(signals[k] * WEIGHTS[k] for k in signals)
        # Clamp to [0, 1]
        weighted = max(0.0, min(1.0, weighted))

        if weighted < 0.33:
            tier = ComplexityTier.LOW
        elif weighted < 0.66:
            tier = ComplexityTier.MEDIUM
        else:
            tier = ComplexityTier.HIGH

        return ComplexityResult(
            tier=tier,
            score=round(weighted, 3),
            signals={k: round(v, 3) for k, v in signals.items()},
        )

    # ── Individual signal scorers (each return 0.0 – 1.0) ────────────

    @staticmethod
    def _score_length(q: str) -> float:
        words = len(q.split())
        if words < 8:
            return 0.0
        if words < 20:
            return 0.4
        if words < 40:
            return 0.7
        return 1.0

    @staticmethod
    def _score_question_count(q: str) -> float:
        count = q.count("?")
        if count <= 1:
            return 0.0
        if count == 2:
            return 0.5
        return 1.0

    @staticmethod
    def _score_analytical(q: str) -> float:
        hits = sum(1 for kw in ANALYTICAL_KEYWORDS if kw in q)
        if hits == 0:
            return 0.0
        if hits <= 2:
            return 0.5
        return 1.0

    @staticmethod
    def _score_domain(q: str) -> float:
        """Rough: if the query has many uncommon / long words, it's more domain-specific."""
        words = q.split()
        long_words = [w for w in words if len(w) > 8]
        ratio = len(long_words) / max(len(words), 1)
        if ratio < 0.1:
            return 0.0
        if ratio < 0.25:
            return 0.4
        return 0.8

    @staticmethod
    def _score_instruction(q: str) -> float:
        hits = sum(
            1 for pat in COMPLEX_INSTRUCTION_PATTERNS if re.search(pat, q)
        )
        if hits == 0:
            return 0.0
        if hits == 1:
            return 0.4
        return 0.9

    @staticmethod
    def _score_doc_reference(q: str) -> float:
        hits = sum(
            1 for pat in DOC_REFERENCE_PATTERNS if re.search(pat, q)
        )
        if hits == 0:
            return 0.0
        if hits == 1:
            return 0.6
        return 1.0


# Singleton
_analyzer: QueryComplexityAnalyzer | None = None


def get_query_analyzer() -> QueryComplexityAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = QueryComplexityAnalyzer()
    return _analyzer
