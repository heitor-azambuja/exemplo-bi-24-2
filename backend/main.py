"""HTTP entry point for investment simulations."""

from fastapi import FastAPI
from fastapi.responses import Response

from backend.calculator import monthly_rate, simulate_scenarios
from backend.report import create_pdf
from backend.schemas import SimulationRequest

app = FastAPI(title="Simulador de investimentos", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Expose a small readiness probe without requiring external services."""
    return {"status": "ok"}


@app.post("/api/simulate", summary="Simular investimentos e cenários de retirada")
def simulate(request: SimulationRequest) -> dict:
    """Return decimal monetary strings and one-indexed monthly series."""
    config, scenarios = request.to_domain()
    return {
        "parameters": request.model_dump(mode="json"),
        "assumptions": {
            "rate_unit": "effective_annual_percent",
            "monthly_rate": str(monthly_rate(config.annual_rate_pct)),
            "month_index_starts_at": 1,
            "event_order": "start_of_month_contributions_then_interest_then_end_of_month_withdrawals",
            "rounding": "monthly_interest_to_cents_half_up",
            "taxes_and_inflation": "excluded",
        },
        **simulate_scenarios(config, scenarios),
    }


@app.post(
    "/api/report", summary="Gerar relatório PDF da simulação", response_class=Response,
    responses={200: {"description": "PDF do investimento", "content": {"application/pdf": {}}}},
)
def report(request: SimulationRequest) -> Response:
    """Render the same calculations as /api/simulate into a downloadable PDF."""
    data = simulate(request)
    return Response(
        content=create_pdf(data),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="relatorio-investimento.pdf"',
                 "Cache-Control": "no-store"},
    )
