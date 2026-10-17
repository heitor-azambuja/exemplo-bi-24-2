"""Deterministic monthly compound-interest calculations.

Amounts are Decimal and rounded to cents after each month's interest accrual.
The input rate is an effective annual percentage, not a nominal APR.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000000000")


def money(value: Decimal) -> Decimal:
    """Round a monetary amount to cents using commercial half-up rounding."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class InvestmentInput:
    monthly_contribution: Decimal
    one_time_contribution: Decimal
    one_time_month: int
    annual_rate_pct: Decimal
    months: int

    def __post_init__(self) -> None:
        if isinstance(self.months, bool) or not isinstance(self.months, int) or not 1 <= self.months <= 600:
            raise ValueError("O prazo deve ser de 1 a 600 meses.")
        if isinstance(self.one_time_month, bool) or not isinstance(self.one_time_month, int) or not 1 <= self.one_time_month <= self.months:
            raise ValueError("O mês do aporte pontual deve estar dentro do prazo.")
        for label, value in (("Aporte mensal", self.monthly_contribution), ("Aporte pontual", self.one_time_contribution)):
            if not isinstance(value, Decimal) or not value.is_finite() or not 0 <= value <= MAX_AMOUNT or value != money(value):
                raise ValueError(f"{label} deve ser um valor monetário entre 0 e 1 trilhão, com até 2 casas decimais.")
        if not isinstance(self.annual_rate_pct, Decimal) or not self.annual_rate_pct.is_finite() or not Decimal("-100") < self.annual_rate_pct <= Decimal("1000"):
            raise ValueError("A taxa anual deve ser maior que -100% e no máximo 1000%.")


def monthly_rate(annual_rate_pct: Decimal) -> Decimal:
    """Convert an effective annual percentage into an equivalent monthly rate."""
    with localcontext() as context:
        context.prec = 40
        return (Decimal(1) + annual_rate_pct / Decimal(100)) ** (Decimal(1) / Decimal(12)) - Decimal(1)


def simulate_base(config: InvestmentInput) -> dict:
    """Produce a monthly time series, adding deposits before monthly interest."""
    rate = monthly_rate(config.annual_rate_pct)
    balance = Decimal(0)
    contributions = Decimal(0)
    earnings = Decimal(0)
    rows = []
    for month in range(1, config.months + 1):
        contribution = config.monthly_contribution
        if month == config.one_time_month:
            contribution += config.one_time_contribution
        contributions += contribution
        interest = money((balance + contribution) * rate)
        earnings += interest
        balance = balance + contribution + interest
        rows.append({
            "month": month,
            "contribution": str(money(contribution)),
            "contributions_total": str(money(contributions)),
            "interest": str(interest),
            "earnings_total": str(money(earnings)),
            "balance": str(money(balance)),
        })
    return {
        "months": rows,
        "summary": {
            "contributions_total": str(money(contributions)),
            "earnings_total": str(money(earnings)),
            "final_balance": str(money(balance)),
        },
    }
