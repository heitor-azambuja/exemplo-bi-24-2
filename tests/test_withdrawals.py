"""Withdrawals must remain independent and auditable month by month."""

from decimal import Decimal

import pytest

from backend.calculator import InvestmentInput, Scenario, Withdrawal, simulate_scenarios


def setup(months=6, monthly="100", rate="0") -> InvestmentInput:
    return InvestmentInput(Decimal(monthly), Decimal(0), 1, Decimal(rate), months)


def withdrawal(amount="10", start=1, end=None, interval=1) -> Withdrawal:
    return Withdrawal(Decimal(amount), start, end, interval)


def test_one_off_and_recurring_withdrawals_can_overlap() -> None:
    scenario = Scenario("Plano A", (withdrawal("40", 2), withdrawal("10", 2, 6, 2)))
    result = simulate_scenarios(setup(), (scenario,))
    rows = result["scenarios"][0]["months"]
    assert [r["withdrawal_requested"] for r in rows] == ["0.00", "50.00", "0.00", "10.00", "0.00", "10.00"]
    assert result["base"]["summary"]["final_balance"] == "600.00"
    assert result["scenarios"][0]["summary"]["final_balance"] == "530.00"
    assert result["scenarios"][0]["summary"]["difference_from_base"] == "-70.00"
    assert rows[-1]["net_contributions_total"] == "530.00"


def test_insufficient_balance_caps_withdrawal_and_reports_shortfall() -> None:
    scenario = Scenario("Resgate", (withdrawal("150", 1, 3),))
    result = simulate_scenarios(setup(months=3), (scenario,))["scenarios"][0]
    assert [r["withdrawal"] for r in result["months"]] == ["100.00", "100.00", "100.00"]
    assert result["summary"]["withdrawals_requested_total"] == "450.00"
    assert result["summary"]["withdrawals_total"] == "300.00"
    assert result["summary"]["unmet_withdrawal_total"] == "150.00"
    assert result["summary"]["final_balance"] == "0.00"


def test_scenarios_do_not_contaminate_each_other() -> None:
    a = Scenario("A", (withdrawal("10", 1),))
    b = Scenario("B", (withdrawal("20", 1),))
    result = simulate_scenarios(setup(months=2), (a, b))
    assert [s["summary"]["final_balance"] for s in result["scenarios"]] == ["190.00", "180.00"]
    assert result["base"]["summary"]["final_balance"] == "200.00"


def test_withdrawals_after_interest() -> None:
    result = simulate_scenarios(setup(months=1, rate="12"), (Scenario("A", (withdrawal("100", 1),)),))
    row = result["scenarios"][0]["months"][0]
    assert row["interest"] == "0.95"
    assert row["balance"] == "0.95"


@pytest.mark.parametrize("event", [
    lambda: withdrawal("0"), lambda: withdrawal("0.001"),
    lambda: withdrawal("10", 0), lambda: withdrawal("10", 1, 0),
    lambda: withdrawal("10", 1, None, 2), lambda: withdrawal("10", 1, 2, 0),
])
def test_invalid_withdrawal(event) -> None:
    with pytest.raises(ValueError):
        event()


def test_invalid_scenario_names_and_out_of_horizon() -> None:
    with pytest.raises(ValueError):
        simulate_scenarios(setup(), (Scenario("a", ()), Scenario(" A ", ())))
    with pytest.raises(ValueError):
        simulate_scenarios(setup(), (Scenario("A", (withdrawal("1", 7),)),))
    with pytest.raises(ValueError):
        simulate_scenarios(setup(), (Scenario("A", (withdrawal("1", 1, 7),)),))
    with pytest.raises(ValueError):
        Scenario("  ", ())
    with pytest.raises(ValueError):
        simulate_scenarios(setup(), tuple(Scenario(str(i), ()) for i in range(11)))
