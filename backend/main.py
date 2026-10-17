"""HTTP entry point for investment simulations."""

from fastapi import FastAPI

app = FastAPI(title="Simulador de investimentos", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Expose a small readiness probe without requiring external services."""
    return {"status": "ok"}
