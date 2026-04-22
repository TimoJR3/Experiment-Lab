# Experiment Lab

Experiment Lab is a portfolio pet project for simulating and analyzing product experiments.  
Stage 1 contains only the scaffold: API, dashboard, database container, tests, and developer tooling.

## Stack

- Python 3.11
- FastAPI
- Streamlit
- PostgreSQL
- Docker Compose
- pandas
- SciPy / statsmodels
- pytest

## Repository Structure

```text
.
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── experiments/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── dashboard/
├── docs/
├── tests/
├── .env.example
├── Dockerfile
├── Makefile
├── README.md
├── docker-compose.yml
└── requirements.txt
```

## Quickstart

### Local launch

1. Create and activate a virtual environment.
2. Copy `.env.example` to `.env`.
3. Install dependencies.
4. Run API and dashboard.

```bash
python -m venv .venv
.venv\Scripts\activate
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
streamlit run dashboard/app.py
pytest -q
```

### Docker launch

```bash
copy .env.example .env
docker compose up --build
```

## Available Endpoints

- `GET /health` returns the API health status.

## Current Stage Scope

Stage 1 intentionally does not include:

- experiment logic
- event ingestion
- user randomization
- statistical analysis
- production dashboards

## Next Stage

The next stage is to add the first real data model and persistence flow:

- PostgreSQL schema for events and experiments
- SQLAlchemy models
- simple CRUD for experiment description
- basic event loading for demo data
