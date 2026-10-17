# exemplo-bi-24-2

Demonstração ao vivo de uso de agente assíncrono para desenvolvimento.

## Simulador de investimentos

Simulador de juros compostos com backend em FastAPI e interface Python em Streamlit. A aplicação não exige banco de dados nem serviços externos.

### Preparação (Python 3.11+)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

### Execução

Em dois terminais, com o ambiente virtual ativado:

```bash
uvicorn backend.main:app --reload --port 8000
```

```bash
streamlit run frontend/app.py --server.port 8501
```

Acesse a interface em `http://localhost:8501`. A API oferece `http://localhost:8000/health` e documentação interativa em `http://localhost:8000/docs`.
Para usar outro endereço da API, defina `API_URL` antes de executar o Streamlit (por exemplo, `API_URL=http://localhost:9000`). O frontend chama a API pelo processo Python, sem precisar de proxy de navegador.

### Testes

```bash
python -m pytest -q
```
