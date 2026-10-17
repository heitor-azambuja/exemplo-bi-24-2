"""Chart datasets and tables must preserve the exact API series."""

from decimal import Decimal

from fastapi.testclient import TestClient

from backend.main import app
from frontend.visualizations import BASE_NAME, balance_chart, composition_chart, monthly_table, summary_table


def sample() -> dict:
    response = TestClient(app).post("/api/simulate", json={
        "monthly_contribution": "100.00", "one_time_contribution": "0.00",
        "one_time_month": 1, "annual_rate_pct": "0", "months": 3,
        "scenarios": [{"name": "Retirada", "withdrawals": [
            {"kind": "one_time", "amount": "150.00", "start_month": 1}
        ]}],
    })
    assert response.status_code == 200
    return response.json()


def test_balance_chart_contains_all_series_and_axis_units() -> None:
    chart = balance_chart(sample()).to_dict()
    dataset = next(iter(chart["datasets"].values()))
    assert len(dataset) == 6
    assert {row["Cenário"] for row in dataset} == {BASE_NAME, "Retirada"}
    assert chart["encoding"]["y"]["axis"]["title"] == "Saldo (R$)"
    assert "tooltip" in chart["encoding"]


def test_composition_tracks_net_contributions_and_yield() -> None:
    result = sample()["scenarios"][0]
    chart = composition_chart(result).to_dict()
    dataset = next(iter(chart["datasets"].values()))
    assert len(dataset) == 6
    first = [row for row in dataset if row["Mês"] == 1]
    assert {row["Parcela"]: row["Valor"] for row in first} == {
        "Aportes líquidos": 0.0, "Rendimento acumulado": 0.0,
    }
    assert Decimal(result["summary"]["net_contributions_total"]) + Decimal(result["summary"]["earnings_total"]) == Decimal(result["summary"]["final_balance"])


def test_comparison_and_monthly_tables_expose_withdrawals() -> None:
    data = sample()
    summary = summary_table(data)
    assert len(summary) == 2
    assert summary.iloc[1]["Retirada não atendida"] == "R$ 50,00"
    table = monthly_table(data["scenarios"][0])
    assert list(table["Mês"]) == [1, 2, 3]
    assert table.iloc[0]["Retirada solicitada"] == "R$ 150,00"
    assert table.iloc[0]["Retirada efetiva"] == "R$ 100,00"
    assert table.iloc[0]["Não atendida"] == "R$ 50,00"
