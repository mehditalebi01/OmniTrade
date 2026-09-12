from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from math import ceil


class MetricDirection(StrEnum):
    """Defines whether a quality target is a maximum or a minimum."""

    AT_MOST = "at_most"
    AT_LEAST = "at_least"


@dataclass(frozen=True)
class QualityTarget:
    requirement_id: str
    metric: str
    direction: MetricDirection
    threshold: float
    unit: str


@dataclass(frozen=True)
class QualityResult:
    requirement_id: str
    metric: str
    observed: float
    threshold: float
    unit: str
    passed: bool


def percentile(values: Iterable[float], quantile: float) -> float:
    """Return the nearest-rank percentile used by the NFR evidence script."""

    samples = sorted(float(value) for value in values)
    if not samples:
        raise ValueError("At least one measurement is required")
    if not 0 < quantile <= 1:
        raise ValueError("Quantile must be greater than 0 and at most 1")
    rank = max(1, ceil(quantile * len(samples)))
    return samples[rank - 1]


def evaluate_metric(target: QualityTarget, values: Iterable[float]) -> QualityResult:
    samples = list(values)
    observed = percentile(samples, 0.95) if len(samples) > 1 else percentile(samples, 1.0)
    passed = (
        observed <= target.threshold
        if target.direction == MetricDirection.AT_MOST
        else observed >= target.threshold
    )
    return QualityResult(
        requirement_id=target.requirement_id,
        metric=target.metric,
        observed=observed,
        threshold=target.threshold,
        unit=target.unit,
        passed=passed,
    )
