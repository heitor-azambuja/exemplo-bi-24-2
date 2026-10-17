"""Validated public request contract for the simulation API."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.calculator import InvestmentInput, Scenario, Withdrawal, money

Money = Annotated[Decimal, Field(ge=0, le=Decimal("1000000000000"))]
PositiveMoney = Annotated[Decimal, Field(gt=0, le=Decimal("1000000000000"))]


class WithdrawalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["one_time", "recurring"]
    amount: PositiveMoney
    start_month: int = Field(ge=1, le=600)
    end_month: int | None = Field(default=None, ge=1, le=600)
    interval_months: int = Field(default=1, ge=1, le=600)

    @field_validator("amount")
    @classmethod
    def check_cents(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value != money(value):
            raise ValueError("Informe um valor monetário com até 2 casas decimais.")
        return value

    @model_validator(mode="after")
    def check_recurrence(self) -> "WithdrawalPayload":
        if self.kind == "one_time" and (self.end_month is not None or self.interval_months != 1):
            raise ValueError("Retirada pontual não aceita mês final nem intervalo.")
        if self.kind == "recurring" and (self.end_month is None or self.end_month < self.start_month):
            raise ValueError("Retirada recorrente exige mês final igual ou posterior ao inicial.")
        return self

    def to_domain(self) -> Withdrawal:
        return Withdrawal(self.amount, self.start_month, self.end_month, self.interval_months)


class ScenarioPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    withdrawals: list[WithdrawalPayload] = Field(default_factory=list, max_length=30)

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O nome do cenário não pode estar vazio.")
        return value.strip()

    def to_domain(self) -> Scenario:
        return Scenario(self.name, tuple(item.to_domain() for item in self.withdrawals))


class SimulationRequest(BaseModel):
    """All monetary values are decimal strings in reais; rate is annual percent."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "examples": [{
            "monthly_contribution": "500.00", "one_time_contribution": "1000.00",
            "one_time_month": 1, "annual_rate_pct": "10.00", "months": 120,
            "scenarios": [{"name": "Resgates", "withdrawals": [
                {"kind": "recurring", "amount": "100.00", "start_month": 25,
                 "end_month": 60, "interval_months": 1}
            ]}],
        }]
    })

    monthly_contribution: Money = Field(description="Aporte mensal em reais, no início de cada mês; até 2 casas decimais.")
    one_time_contribution: Money = Field(description="Aporte pontual em reais; até 2 casas decimais.")
    one_time_month: int = Field(ge=1, le=600, description="Mês do aporte pontual, começando em 1.")
    annual_rate_pct: Decimal = Field(gt=Decimal("-100"), le=Decimal("1000"), description="Taxa de juros anual efetiva em percentual (10 = 10% a.a.).")
    months: int = Field(ge=1, le=600, description="Horizonte da projeção em meses.")
    scenarios: list[ScenarioPayload] = Field(default_factory=list, max_length=10, description="Cenários alternativos; a projeção-base não tem retiradas.")

    @field_validator("monthly_contribution", "one_time_contribution")
    @classmethod
    def check_cents(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value != money(value):
            raise ValueError("Informe um valor monetário com até 2 casas decimais.")
        return value

    @model_validator(mode="after")
    def check_horizon(self) -> "SimulationRequest":
        if self.one_time_month > self.months:
            raise ValueError("O mês do aporte pontual deve estar dentro do prazo.")
        seen: set[str] = set()
        for scenario in self.scenarios:
            name = scenario.name.casefold()
            if name in seen:
                raise ValueError("Os nomes dos cenários devem ser diferentes.")
            seen.add(name)
            for item in scenario.withdrawals:
                if item.start_month > self.months or (item.end_month is not None and item.end_month > self.months):
                    raise ValueError(f"Retirada de '{scenario.name}' fora do prazo.")
        return self

    def to_domain(self) -> tuple[InvestmentInput, tuple[Scenario, ...]]:
        config = InvestmentInput(
            self.monthly_contribution, self.one_time_contribution, self.one_time_month,
            self.annual_rate_pct, self.months,
        )
        return config, tuple(item.to_domain() for item in self.scenarios)
