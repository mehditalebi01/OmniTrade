import pytest

from omnitrade.calculations import (
    CalculationError,
    fundamental_ratios,
    relative_strength_index,
    simple_moving_average,
)


def test_formulas_handle_normal_and_zero_denominator_cases() -> None:
    assert simple_moving_average([1, 2, 3, 4], 2) == 3.5
    assert relative_strength_index(list(range(20))) == 100
    ratios = fundamental_ratios(100, 5, 20, 0, 10)
    assert ratios.price_to_earnings == 20
    assert ratios.debt_to_equity is None


def test_formula_rejects_short_series() -> None:
    with pytest.raises(CalculationError):
        simple_moving_average([1], 2)
