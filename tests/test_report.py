"""The PDF must reflect the same engine and figures as the JSON API."""

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.main import app

client = TestClient(app)


def request_data(months=3) -> dict:
    return {
        "monthly_contribution": "100.00", "one_time_contribution": "50.00",
        "one_time_month": 1, "annual_rate_pct": "0", "months": months,
        "scenarios": [{"name": "Resgate planejado", "withdrawals": [
            {"kind": "one_time", "amount": "200.00", "start_month": 1}
        ]}],
    }


def pdf_text(content: bytes) -> tuple[str, int]:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() for page in reader.pages), len(reader.pages)


def test_report_matches_json_results_and_declares_assumptions() -> None:
    payload = request_data()
    simulation = client.post("/api/simulate", json=payload).json()
    response = client.post("/api/report", json=payload)
    assert response.status_code == 200, response.text[:200]
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF-")
    text, page_count = pdf_text(response.content)
    assert page_count >= 3
    for expected in ("Relatório de investimento", "Premissas", "Evolução do saldo por cenário",
                     "Composição da projeção-base", "Evolução mensal: Resgate planejado",
                     "sem impostos nem inflação", "não atendido"):
        assert expected in text
    assert "R$ 350,00" in text  # baseline from exactly the JSON result
    assert simulation["base"]["summary"]["final_balance"] == "350.00"
    assert "R$ 200,00" in text  # alternative capped at the available first-month balance
    assert simulation["scenarios"][0]["summary"]["final_balance"] == "200.00"
    assert "R$ 50,00" in text  # unmet part of the requested withdrawal


def test_report_rejects_invalid_request() -> None:
    payload = request_data()
    payload["months"] = 0
    assert client.post("/api/report", json=payload).status_code == 422


def test_report_handles_a_long_table_and_a_single_month() -> None:
    payload = request_data(months=60)
    response = client.post("/api/report", json=payload)
    assert response.status_code == 200
    text, page_count = pdf_text(response.content)
    assert page_count >= 4
    assert "Mês 60" in text
    payload = request_data(months=1)
    response = client.post("/api/report", json=payload)
    assert response.status_code == 200
    assert "Mês 1" in pdf_text(response.content)[0]
