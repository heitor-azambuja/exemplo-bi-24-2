# exemplo-bi-24-2

Live demonstration of asynchronous agent-assisted development.

## Compound-interest simulator

A Python-only application with a FastAPI backend and a Streamlit frontend. No database or external service is required. The interface is in Portuguese and starts in dark mode.

### Setup (Python 3.11+)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

### Run locally

In two terminals with the virtual environment active:

```bash
uvicorn backend.main:app --reload --port 8000
```

```bash
streamlit run frontend/app.py --server.port 8501
```

Open `http://localhost:8501`. The API exposes `/health` and interactive OpenAPI documentation at `http://localhost:8000/docs`. The Streamlit Python process calls FastAPI over HTTP; set `API_URL=http://localhost:9000` before starting Streamlit if the API runs elsewhere.

### Simulation contract

`POST /api/simulate` accepts monetary decimal strings in reais, an effective annual rate in percent, and a duration in months. For example:

```json
{
  "monthly_contribution": "500.00",
  "one_time_contribution": "1000.00",
  "one_time_month": 1,
  "annual_rate_pct": "10.00",
  "months": 120,
  "scenarios": [
    {
      "name": "Regular withdrawals",
      "withdrawals": [
        {"kind": "recurring", "amount": "100.00", "start_month": 25, "end_month": 60, "interval_months": 1},
        {"kind": "one_time", "amount": "500.00", "start_month": 80}
      ]
    }
  ]
}
```

The response contains `parameters`, `assumptions`, a no-withdrawal `base`, and independent `scenarios`. Each monthly row includes contributions, interest, requested and effective withdrawals, unfulfilled withdrawals, and balance; monetary results are decimal strings. The simulation accepts 1–600 months, up to 10 scenarios and 30 withdrawal events per scenario. Amounts have at most two decimal places. Validation errors return HTTP 422.

The annual effective percentage is converted to an equivalent monthly rate using `(1 + annual_rate_pct / 100) ** (1 / 12) - 1`. Each month starts with contributions; interest is then credited and rounded to cents (half up); withdrawals occur at month end. A request exceeding available balance withdraws only that balance and records the shortfall. This is a nominal projection: taxes and inflation are not modeled.

`POST /api/report` accepts the same request body and returns an `application/pdf` attachment. The report includes the assumptions, comparative totals, vector charts, and month-by-month tables. In Streamlit, simulate first, then select “Gerar relatório PDF” and “Baixar relatório PDF”. The report uses the inputs of the last displayed simulation even if form fields are edited afterward.

### Tests

```bash
python -m pytest -q
```

Tests cover the pure financial engine, API validation, Streamlit interactions, chart/table data, and PDF content. Run the suite locally with the command above.
