"""Accessible charts and audit tables built entirely from API results."""

from decimal import Decimal

import altair as alt
import pandas as pd

BASE_NAME = "Sem retiradas"
COLORS = ["#5EEAD4", "#F8C96B", "#82B6FF", "#F59ABB", "#B9A2FF", "#9DD77A",
          "#FFAF87", "#A5D8E8", "#E9BBEC", "#FFE187", "#D0C5FF"]


def currency(value: str) -> str:
    formatted = f"{Decimal(value):,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def balance_chart(data: dict) -> alt.Chart:
    """Each scenario is an independent line; the baseline stays solid."""
    names = [BASE_NAME] + [scenario["name"] for scenario in data["scenarios"]]
    rows = []
    for name, result in zip(names, [data["base"], *data["scenarios"]]):
        rows.extend({"Mês": row["month"], "Saldo": float(row["balance"]),
                     "Cenário": name, "Tipo": "Base" if name == BASE_NAME else "Alternativa"}
                    for row in result["months"])
    return alt.Chart(pd.DataFrame(rows)).mark_line(strokeWidth=2.5, point=False).encode(
        x=alt.X("Mês:Q", axis=alt.Axis(title="Mês", tickMinStep=1)),
        y=alt.Y("Saldo:Q", axis=alt.Axis(title="Saldo (R$)", format=",.2f"), scale=alt.Scale(zero=True)),
        color=alt.Color("Cenário:N", scale=alt.Scale(domain=names, range=COLORS[:len(names)])),
        strokeDash=alt.StrokeDash("Tipo:N", scale=alt.Scale(domain=["Base", "Alternativa"],
                                                           range=[[1, 0], [6, 3]]), legend=None),
        tooltip=[alt.Tooltip("Mês:Q"), alt.Tooltip("Cenário:N"),
                 alt.Tooltip("Saldo:Q", format=",.2f", title="Saldo (R$)")],
    ).properties(height=340).interactive(bind_y=False)


def composition_chart(result: dict) -> alt.Chart:
    """Do not stack negative net contributions or negative returns."""
    rows = []
    for row in result["months"]:
        rows.append({"Mês": row["month"], "Parcela": "Aportes líquidos",
                     "Valor": float(row["net_contributions_total"])})
        rows.append({"Mês": row["month"], "Parcela": "Rendimento acumulado",
                     "Valor": float(row["earnings_total"])})
    return alt.Chart(pd.DataFrame(rows)).mark_line(strokeWidth=2.5).encode(
        x=alt.X("Mês:Q", axis=alt.Axis(title="Mês", tickMinStep=1)),
        y=alt.Y("Valor:Q", axis=alt.Axis(title="Valor (R$)", format=",.2f")),
        color=alt.Color("Parcela:N", scale=alt.Scale(domain=["Aportes líquidos", "Rendimento acumulado"],
                                                     range=["#5EEAD4", "#F8C96B"])),
        tooltip=[alt.Tooltip("Mês:Q"), alt.Tooltip("Parcela:N"),
                 alt.Tooltip("Valor:Q", format=",.2f", title="Valor (R$)")],
    ).properties(height=260).interactive(bind_y=False)


def summary_table(data: dict) -> pd.DataFrame:
    rows = []
    for name, result in [(BASE_NAME, data["base"]), *[(s["name"], s) for s in data["scenarios"]]]:
        summary = result["summary"]
        rows.append({
            "Cenário": name,
            "Saldo final": currency(summary["final_balance"]),
            "Aportado": currency(summary["contributions_total"]),
            "Retirado": currency(summary["withdrawals_total"]),
            "Rendimento": currency(summary["earnings_total"]),
            "Diferença vs. base": currency(summary.get("difference_from_base", "0.00")),
            "Retirada não atendida": currency(summary["unmet_withdrawal_total"]),
        })
    return pd.DataFrame(rows)


def monthly_table(result: dict) -> pd.DataFrame:
    rows = []
    for month in result["months"]:
        rows.append({
            "Mês": month["month"], "Aporte": currency(month["contribution"]),
            "Juros": currency(month["interest"]),
            "Retirada solicitada": currency(month["withdrawal_requested"]),
            "Retirada efetiva": currency(month["withdrawal"]),
            "Não atendida": currency(month["unmet_withdrawal"]),
            "Saldo": currency(month["balance"]),
        })
    return pd.DataFrame(rows)
