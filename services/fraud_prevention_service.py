from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings


@dataclass(frozen=True)
class ScoreComparison:
    previous_score: int | None
    current_score: int
    score_delta: int | None
    trend: str
    flags: list[str]
    review_required: bool


class FraudPreventionService:
    """Detect suspicious score changes against a previous on-chain score.

    This is intentionally deterministic so multiple Chainlink nodes running the
    same adapter over the same inputs produce the same result.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def compare_scores(self, current_score: int, previous_score: int | None) -> ScoreComparison:
        if previous_score is None:
            return ScoreComparison(
                previous_score=None,
                current_score=current_score,
                score_delta=None,
                trend="no_baseline",
                flags=[],
                review_required=False,
            )

        delta = current_score - previous_score
        flags: list[str] = []
        review_required = False

        if delta < 0:
            flags.append("score_regression")
            review_required = True
            trend = "regressed"
        elif delta >= self.settings.drastic_improvement_threshold:
            flags.append("suspicious_score_improvement")
            review_required = True
            trend = "suspicious_improvement"
        elif delta > 0:
            trend = "improved"
        else:
            trend = "unchanged"

        return ScoreComparison(
            previous_score=previous_score,
            current_score=current_score,
            score_delta=delta,
            trend=trend,
            flags=flags,
            review_required=review_required,
        )
