"""Exercise Streamlit controls without a live API server."""

from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from backend.main import app
from frontend.client import describe_error


def test_frontend_can_add_scenario_and_withdrawal() -> None:
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/app.py").run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert len(at.text_input) == 1
    assert "＋ Adicionar retirada" in [button.label for button in at.button]
    next(button for button in at.button if button.label == "＋ Adicionar retirada").click().run()
    assert not at.exception
    assert len(at.selectbox) == 1
    at.selectbox[0].set_value("Recorrente").run()
    assert not at.exception
    assert len(at.number_input) >= 9


def test_frontend_submits_to_api_and_displays_result() -> None:
    calls: list[dict] = []

    def fake_api(url: str, payload: dict) -> dict:
        calls.append(payload)
        response = TestClient(app).post("/api/simulate", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    with patch("frontend.client.simulate", side_effect=fake_api):
        at = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/app.py").run()
        next(button for button in at.button if button.label == "Simular projeção").click().run()
    assert not at.exception
    assert calls[0]["monthly_contribution"] == "500.00"
    assert calls[0]["one_time_contribution"] == "1000.00"
    assert calls[0]["scenarios"] == []
    assert at.metric[0].value.startswith("R$ ")


def test_frontend_submits_scenario_with_recurring_withdrawal() -> None:
    calls: list[dict] = []

    def fake_api(url: str, payload: dict) -> dict:
        calls.append(payload)
        response = TestClient(app).post("/api/simulate", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    with patch("frontend.client.simulate", side_effect=fake_api):
        at = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/app.py").run()
        next(button for button in at.button if button.label == "＋ Novo cenário").click().run()
        next(button for button in at.button if button.label == "＋ Adicionar retirada").click().run()
        at.selectbox[0].set_value("Recorrente").run()
        next(button for button in at.button if button.label == "Simular projeção").click().run()
    assert not at.exception
    event = calls[0]["scenarios"][0]["withdrawals"][0]
    assert event == {"kind": "recurring", "amount": "100.00", "start_month": 1,
                     "end_month": 120, "interval_months": 1}
    assert len(at.metric) == 3
    assert len(at.dataframe) == 2


def test_api_validation_message_is_shown_to_user() -> None:
    request = httpx.Request("POST", "http://localhost/api/simulate")
    response = httpx.Response(422, request=request, json={"detail": [
        {"loc": ["body", "months"], "msg": "fora do prazo"}
    ]})
    assert "body.months" in describe_error(httpx.HTTPStatusError("invalid", request=request, response=response))
