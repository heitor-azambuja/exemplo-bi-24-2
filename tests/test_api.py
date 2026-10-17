"""HTTP contract tests for the simulation endpoint."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def payload() -> dict:
    return {
        "monthly_contribution": "100.00", "one_time_contribution": "50.00",
        "one_time_month": 1, "annual_rate_pct": "0", "months": 3,
        "scenarios": [{"name": "Plano", "withdrawals": [
            {"kind": "recurring", "amount": "20.00", "start_month": 2,
             "end_month": 3, "interval_months": 1}
        ]}],
    }


def test_full_simulation_returns_baseline_and_alternative() -> None:
    response = client.post("/api/simulate", json=payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["parameters"]["monthly_contribution"] == "100.00"
    assert data["base"]["summary"]["final_balance"] == "350.00"
    assert data["scenarios"][0]["summary"]["final_balance"] == "310.00"
    assert data["scenarios"][0]["months"][1]["withdrawal"] == "20.00"
    assert data["assumptions"]["rate_unit"] == "effective_annual_percent"
    assert len(data["base"]["months"]) == 3


def test_no_scenarios_is_valid() -> None:
    request = payload()
    request.pop("scenarios")
    response = client.post("/api/simulate", json=request)
    assert response.status_code == 200
    assert response.json()["scenarios"] == []


@pytest.mark.parametrize("change", [
    {"monthly_contribution": "-1"}, {"one_time_contribution": "0.001"},
    {"one_time_month": 4}, {"annual_rate_pct": "-100"}, {"months": 0},
    {"extra": "not allowed"},
])
def test_invalid_parameters_receive_field_aware_errors(change: dict) -> None:
    response = client.post("/api/simulate", json={**payload(), **change})
    assert response.status_code == 422
    assert response.json()["detail"]


def test_invalid_scenario_and_duplicate_name() -> None:
    request = payload()
    request["scenarios"][0]["withdrawals"][0]["end_month"] = 4
    assert client.post("/api/simulate", json=request).status_code == 422
    request = payload()
    request["scenarios"].append({"name": " plano ", "withdrawals": []})
    assert client.post("/api/simulate", json=request).status_code == 422
    request = payload()
    request["scenarios"][0]["withdrawals"][0]["kind"] = "one_time"
    assert client.post("/api/simulate", json=request).status_code == 422


def test_openapi_exposes_request_schema_and_example() -> None:
    document = client.get("/openapi.json").json()
    assert "/api/simulate" in document["paths"]
    schema = document["components"]["schemas"]["SimulationRequest"]
    assert schema["examples"][0]["monthly_contribution"] == "500.00"


def test_valid_extreme_rate_and_horizon_do_not_crash() -> None:
    request = payload()
    request.update(months=600, monthly_contribution="1000000000000.00", annual_rate_pct="1000")
    request["scenarios"] = []
    response = client.post("/api/simulate", json=request)
    assert response.status_code == 200, response.text
    assert len(response.json()["base"]["months"]) == 600
