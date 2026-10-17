"""Streamlit frontend for compound-interest projections."""

import os
from decimal import Decimal
from uuid import uuid4

import httpx
import streamlit as st

from frontend.client import describe_error, simulate

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Investimento composto", page_icon="📈", layout="wide")
st.markdown("""
<style>
.block-container { max-width: 1240px; padding-top: 2.5rem; padding-bottom: 4rem; }
h1, h2, h3 { letter-spacing: -0.025em; }
[data-testid="stMetric"] { border: 1px solid #304057; border-radius: 14px; padding: 1.1rem; background: #141f32; }
</style>
""", unsafe_allow_html=True)


def currency(value: str) -> str:
    formatted = f"{Decimal(value):,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def new_item() -> dict:
    return {"id": uuid4().hex}


if "scenarios" not in st.session_state:
    st.session_state.scenarios = []
if "result" not in st.session_state:
    st.session_state.result = None

st.title("Investimento composto")
st.caption("Planeje aportes, compare retiradas e acompanhe cada mês do seu investimento.")

st.subheader("Parâmetros do investimento")
left, middle, right = st.columns([1, 1, 1], gap="large")
with left:
    monthly = st.number_input("Aporte mensal (R$)", min_value=0.0, max_value=1_000_000_000_000.0,
                              value=500.0, step=100.0, format="%.2f")
    lump = st.number_input("Aporte pontual (R$)", min_value=0.0, max_value=1_000_000_000_000.0,
                           value=1000.0, step=100.0, format="%.2f")
with middle:
    lump_month = st.number_input("Mês do aporte pontual", min_value=1, max_value=600, value=1, step=1)
    annual_rate = st.number_input("Juros anuais efetivos (%)", min_value=-99.99, max_value=1000.0,
                                  value=10.0, step=0.25, format="%.2f")
with right:
    months = st.number_input("Prazo (meses)", min_value=1, max_value=600, value=120, step=1)
    st.info("Aportes no início do mês; juros em seguida; retiradas no fim. Valores nominais, sem impostos ou inflação.")

st.divider()
heading, action = st.columns([4, 1])
with heading:
    st.subheader("Cenários de retirada")
    st.caption("Compare até 10 planos independentes com a projeção sem retiradas.")
with action:
    if st.button("＋ Novo cenário", use_container_width=True, disabled=len(st.session_state.scenarios) >= 10):
        st.session_state.scenarios.append({"id": uuid4().hex, "withdrawals": []})
        st.rerun()

scenario_payloads = []
for index, scenario in enumerate(st.session_state.scenarios, start=1):
    identifier = scenario["id"]
    with st.container(border=True):
        name_column, delete_column = st.columns([5, 1])
        with name_column:
            name = st.text_input("Nome do cenário", value=f"Cenário {index}", key=f"name_{identifier}")
        with delete_column:
            st.write(" ")
            if st.button("Remover cenário", key=f"remove_{identifier}"):
                st.session_state.scenarios.remove(scenario)
                st.rerun()
        withdrawals = []
        for item in scenario["withdrawals"]:
            event_id = item["id"]
            with st.expander("Retirada", expanded=True):
                kind_label = st.selectbox("Tipo", ["Pontual", "Recorrente"], key=f"kind_{event_id}")
                amount_column, start_column = st.columns(2)
                with amount_column:
                    amount = st.number_input("Valor da retirada (R$)", min_value=0.01,
                                             max_value=1_000_000_000_000.0, value=100.0,
                                             step=50.0, format="%.2f", key=f"amount_{event_id}")
                with start_column:
                    start = st.number_input("Mês inicial", min_value=1, max_value=600,
                                            value=1, step=1, key=f"start_{event_id}")
                event = {"kind": "one_time" if kind_label == "Pontual" else "recurring",
                         "amount": f"{amount:.2f}", "start_month": start}
                if kind_label == "Recorrente":
                    end_column, interval_column = st.columns(2)
                    with end_column:
                        event["end_month"] = st.number_input("Mês final", min_value=1, max_value=600,
                                                             value=int(months), step=1, key=f"end_{event_id}")
                    with interval_column:
                        event["interval_months"] = st.number_input("Intervalo (meses)", min_value=1,
                                                                   max_value=600, value=1, step=1,
                                                                   key=f"interval_{event_id}")
                if st.button("Excluir retirada", key=f"delete_{event_id}"):
                    scenario["withdrawals"].remove(item)
                    st.rerun()
                withdrawals.append(event)
        if st.button("＋ Adicionar retirada", key=f"add_{identifier}",
                     disabled=len(scenario["withdrawals"]) >= 30):
            scenario["withdrawals"].append(new_item())
            st.rerun()
        scenario_payloads.append({"name": name, "withdrawals": withdrawals})

if not st.session_state.scenarios:
    st.caption("Nenhum cenário cadastrado. A simulação mostrará somente a projeção-base.")

st.divider()
if st.button("Simular projeção", type="primary", use_container_width=True):
    st.session_state.result = None
    payload = {
        "monthly_contribution": f"{monthly:.2f}",
        "one_time_contribution": f"{lump:.2f}",
        "one_time_month": lump_month,
        "annual_rate_pct": str(annual_rate),
        "months": months,
        "scenarios": scenario_payloads,
    }
    try:
        with st.spinner("Calculando projeção..."):
            st.session_state.result = simulate(API_URL, payload)
    except httpx.HTTPError as exc:
        st.error(describe_error(exc))
    except (ValueError, KeyError) as exc:
        st.error(f"Resposta inesperada da API: {exc}")

if st.session_state.result is not None:
    data = st.session_state.result
    st.subheader("Resultado da última simulação")
    st.caption("Altere os parâmetros e simule novamente para atualizar esta projeção.")
    st.metric("Saldo final sem retiradas", currency(data["base"]["summary"]["final_balance"]))
    for scenario in data["scenarios"]:
        st.write(f"{scenario['name']}: {currency(scenario['summary']['final_balance'])}")
        if Decimal(scenario["summary"]["unmet_withdrawal_total"]) > 0:
            st.warning(f"{scenario['name']}: retiradas não atendidas de {currency(scenario['summary']['unmet_withdrawal_total'])}.")
