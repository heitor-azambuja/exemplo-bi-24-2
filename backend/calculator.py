"""Deterministic monthly compound-interest and withdrawal calculations.

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


@dataclass(frozen=True)
class Withdrawal:
    """One-off if end_month is None; otherwise recurring through end_month."""

    amount: Decimal
    start_month: int
    end_month: int | None = None
    interval_months: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite() or not 0 < self.amount <= MAX_AMOUNT or self.amount != money(self.amount):
            raise ValueError("A retirada deve ser positiva, ter até 2 casas decimais e não exceder 1 trilhão.")
        if isinstance(self.start_month, bool) or not isinstance(self.start_month, int) or self.start_month < 1:
            raise ValueError("O mês inicial da retirada deve ser positivo.")
        if isinstance(self.interval_months, bool) or not isinstance(self.interval_months, int) or self.interval_months < 1:
            raise ValueError("O intervalo entre retiradas deve ser positivo.")
        if self.end_month is None:
            if self.interval_months != 1:
                raise ValueError("Retirada pontual não possui intervalo.")
        elif isinstance(self.end_month, bool) or not isinstance(self.end_month, int) or self.end_month < self.start_month:
            raise ValueError("O mês final deve ser igual ou posterior ao inicial.")

    def requested_in(self, month: int) -> Decimal:
        end = self.end_month if self.end_month is not None else self.start_month
        if self.start_month <= month <= end and (month - self.start_month) % self.interval_months == 0:
            return self.amount
        return Decimal(0)


@dataclass(frozen=True)
class Scenario:
    name: str
    withdrawals: tuple[Withdrawal, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not 1 <= len(self.name.strip()) <= 80:
            raise ValueError("O nome do cenário deve ter entre 1 e 80 caracteres.")
        if len(self.withdrawals) > 30 or not all(isinstance(item, Withdrawal) for item in self.withdrawals):
            raise ValueError("Cada cenário aceita até 30 retiradas válidas.")


def monthly_rate(annual_rate_pct: Decimal) -> Decimal:
    """Convert an effective annual percentage into an equivalent monthly rate."""
    with localcontext() as context:
        context.prec = 40
        return (Decimal(1) + annual_rate_pct / Decimal(100)) ** (Decimal(1) / Decimal(12)) - Decimal(1)


def _run(config: InvestmentInput, withdrawals: tuple[Withdrawal, ...] = ()) -> dict:
    # Large but valid horizons/rates can exceed Decimal's default 28-digit context.
    with localcontext() as context:
        context.prec = 100
        return _run_precise(config, withdrawals)


def _run_precise(config: InvestmentInput, withdrawals: tuple[Withdrawal, ...]) -> dict:
    rate = monthly_rate(config.annual_rate_pct)
    balance = Decimal(0)
    contributions = Decimal(0)
    earnings = Decimal(0)
    withdrawn_total = Decimal(0)
    requested_total = Decimal(0)
    rows = []
    for month in range(1, config.months + 1):
        contribution = config.monthly_contribution
        if month == config.one_time_month:
            contribution += config.one_time_contribution
        contributions += contribution
        interest = money((balance + contribution) * rate)
        earnings += interest
        balance += contribution + interest
        requested = sum((item.requested_in(month) for item in withdrawals), Decimal(0))
        withdrawn = min(balance, requested)
        balance -= withdrawn
        withdrawn_total += withdrawn
        requested_total += requested
        rows.append({
            "month": month,
            "contribution": str(money(contribution)),
            "contributions_total": str(money(contributions)),
            "interest": str(interest),
            "earnings_total": str(money(earnings)),
            "withdrawal_requested": str(money(requested)),
            "withdrawal": str(money(withdrawn)),
            "unmet_withdrawal": str(money(requested - withdrawn)),
            "withdrawals_total": str(money(withdrawn_total)),
            "net_contributions_total": str(money(contributions - withdrawn_total)),
            "balance": str(money(balance)),
        })
    return {
        "months": rows,
        "summary": {
            "contributions_total": str(money(contributions)),
            "earnings_total": str(money(earnings)),
            "withdrawals_requested_total": str(money(requested_total)),
            "withdrawals_total": str(money(withdrawn_total)),
            "unmet_withdrawal_total": str(money(requested_total - withdrawn_total)),
            "net_contributions_total": str(money(contributions - withdrawn_total)),
            "final_balance": str(money(balance)),
        },
    }


def simulate_base(config: InvestmentInput) -> dict:
    """Produce a monthly series with deposits before interest and no withdrawals."""
    return _run(config)


def simulate_scenarios(config: InvestmentInput, scenarios: tuple[Scenario, ...] = ()) -> dict:
    """Run independent alternatives against one shared no-withdrawal baseline."""
    if len(scenarios) > 10:
        raise ValueError("São permitidos até 10 cenários.")
    names = [scenario.name.strip().casefold() for scenario in scenarios]
    if len(names) != len(set(names)):
        raise ValueError("Os nomes dos cenários devem ser diferentes.")
    base = simulate_base(config)
    base_balance = Decimal(base["summary"]["final_balance"])
    results = []
    for scenario in scenarios:
        if any(item.start_month > config.months or (item.end_month is not None and item.end_month > config.months) for item in scenario.withdrawals):
            raise ValueError(f"As retiradas de '{scenario.name}' devem estar dentro do prazo.")
        result = _run(config, scenario.withdrawals)
        result["name"] = scenario.name.strip()
        result["summary"]["difference_from_base"] = str(money(Decimal(result["summary"]["final_balance"]) - base_balance))
        results.append(result)
    return {"base": base, "scenarios": results}
