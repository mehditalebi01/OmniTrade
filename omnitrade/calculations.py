from dataclasses import dataclass
from math import sqrt


class CalculationError(ValueError):
    pass


def simple_moving_average(values: list[float], period: int) -> float:
    if period < 1 or len(values) < period:
        raise CalculationError("Not enough observations for moving average")
    return sum(values[-period:]) / period


def relative_strength_index(closes: list[float], period: int = 14) -> float:
    if len(closes) <= period:
        raise CalculationError("Not enough observations for RSI")
    changes = [
        right - left for left, right in zip(closes[-period - 1 : -1], closes[-period:], strict=True)
    ]
    gains = sum(max(change, 0) for change in changes) / period
    losses = sum(max(-change, 0) for change in changes) / period
    if losses == 0:
        return 100.0
    return 100 - (100 / (1 + gains / losses))


def volatility(returns: list[float]) -> float:
    if len(returns) < 2:
        raise CalculationError("At least two returns are required")
    mean = sum(returns) / len(returns)
    return sqrt(sum((value - mean) ** 2 for value in returns) / (len(returns) - 1))


@dataclass(frozen=True)
class FundamentalRatios:
    price_to_earnings: float | None
    debt_to_equity: float | None
    return_on_equity: float | None


def fundamental_ratios(
    price: float, earnings_per_share: float, debt: float, equity: float, net_income: float
) -> FundamentalRatios:
    return FundamentalRatios(
        price / earnings_per_share if earnings_per_share else None,
        debt / equity if equity else None,
        net_income / equity if equity else None,
    )
