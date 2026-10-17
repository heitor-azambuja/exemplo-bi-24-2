"""Regression tests for the pure investment calculation engine."""

from decimal import Decimal

import pytest

from backend.calculator import InvestmentInput, monthly_rate, simulate_base


def config(*, monthly="0", one_time="0", one_time_month=1, rate="0", months=12):
    return InvestmentInput(Decimal(monthly), Decimal(one_time), one_time_month, Decimal(rate), months)


def test_zero_rate_and_monthly_contributions() -> None:
    result = simulate_base(config(monthly="10"))
    assert result["summary"] == {
        "contributions_total": "120.00", "earnings_total": "0.00", "final_balance": "120.00"
    }
    assert len(result["months"]) == 12
    assert result["months"][0]["balance"] == "10.00"


def test_one_time_contribution_is_applied_in_selected_month() -> None:
    rows = simulate_base(config(monthly="10", one_time="50", one_time_month=3, months=4))["months"]
    assert [row["contribution"] for row in rows] == ["10.00", "10.00", "60.00", "10.00"]
    assert rows[-1]["balance"] == "90.00"


def test_effective_annual_rate_uses_monthly_equivalent_with_cent_rounding() -> None:
    result = simulate_base(config(one_time="100", rate="12"))
    # Crediting rounded interest every month differs by one cent from rounding only at year-end.
    assert result["summary"]["final_balance"] == "111.99"
    assert result["summary"]["earnings_total"] == "11.99"
    assert abs(monthly_rate(Decimal("12")) - Decimal("0.00948879293458")) < Decimal("0.00000000000001")


def test_interest_accrues_after_start_of_month_deposit() -> None:
    rows = simulate_base(config(monthly="100", rate="12", months=1))["months"]
    assert rows[0]["interest"] == "0.95"
    assert rows[0]["balance"] == "100.95"


def test_negative_return_is_allowed_without_negative_balance() -> None:
    result = simulate_base(config(one_time="100", rate="-50"))
    assert result["summary"]["final_balance"] == "50.00"


@pytest.mark.parametrize("kwargs", [
    {"months": 0}, {"months": 601}, {"months": True}, {"one_time_month": 13},
    {"monthly": "-1"}, {"monthly": "0.001"}, {"monthly": "NaN"},
    {"one_time": "1000000000000.01"}, {"rate": "-100"}, {"rate": "Infinity"},
])
def test_invalid_inputs_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        config(**kwargs)
