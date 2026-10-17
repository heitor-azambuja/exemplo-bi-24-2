"""Small HTTP client used by the Python frontend."""

import httpx


def simulate(api_url: str, payload: dict) -> dict:
    """Submit a simulation; HTTP failures remain explicit to the UI."""
    response = httpx.post(f"{api_url.rstrip('/')}/api/simulate", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def download_report(api_url: str, payload: dict) -> bytes:
    """Request the PDF for the same inputs used by the visible simulation."""
    response = httpx.post(f"{api_url.rstrip('/')}/api/report", json=payload, timeout=60)
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("application/pdf") or not response.content.startswith(b"%PDF-"):
        raise ValueError("A API não retornou um PDF válido.")
    return response.content


def describe_error(exc: httpx.HTTPError) -> str:
    """Turn API validation details into concise Portuguese feedback."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 422:
        try:
            details = exc.response.json().get("detail", [])
            if isinstance(details, list):
                return "Dados inválidos: " + "; ".join(
                    f"{'.'.join(map(str, item.get('loc', [])))}: {item.get('msg', 'valor inválido')}"
                    for item in details[:4]
                )
        except (ValueError, AttributeError, TypeError):
            pass
    return "Não foi possível concluir a simulação. Confira a API e tente novamente."
