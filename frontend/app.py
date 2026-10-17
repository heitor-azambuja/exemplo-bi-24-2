"""Python-only frontend entry point."""

import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Investimento composto", page_icon="📈", layout="wide")
st.title("Simulador de investimentos")
st.caption("Projeções de juros compostos e retiradas — em desenvolvimento")

if st.button("Verificar conexão com a API"):
    try:
        response = httpx.get(f"{API_URL}/health", timeout=10)
        response.raise_for_status()
        st.success("API disponível")
    except httpx.HTTPError as exc:
        st.error(f"Não foi possível acessar a API: {exc}")
