# Experiment Lab

Minimal A/B testing lab for product experiments: synthetic events, deterministic user assignment, product metrics, statistical analysis, FastAPI, PostgreSQL, and Streamlit dashboard.

> Portfolio project for Junior Data Scientist / Product Analyst roles.  
> The goal is to show not only analysis, but also engineering packaging around analytics.

## What This Project Shows

Experiment Lab models a practical product analytics workflow:

```text
users + events -> experiment setup -> control/treatment assignment -> metrics -> statistical results -> dashboard
```

It answers questions like:

- Did treatment improve conversion?
- How much did ARPU or purchase rate change?
- Are observed differences statistically reliable?
- Can the result be reproduced and shown through an API/dashboard?

## Highlights

- PostgreSQL data model for users, events, experiments, variants, assignments, metrics, and results.
- Synthetic e-commerce event generator with realistic funnel drop-offs.
- Deterministic hash-based assignment to `control` / `treatment`.
- Metrics engine for conversion, revenue, order value, and purchase behavior.
- Statistical tests with uplift, p-values, and confidence intervals.
- FastAPI backend with documented endpoints.
- Streamlit dashboard for experiment monitoring and result interpretation.
- Docker Compose, pytest, GitHub Actions, and MIT License.

## Tech Stack

| Area | Tools |
|---|---|
| Backend | Python 3.11, FastAPI |
| Database | PostgreSQL |
| Analytics | pandas, SciPy, statsmodels |
| Dashboard | Streamlit |
| Infrastructure | Docker Compose |
| Quality | pytest, GitHub Actions |

## Architecture

```text
Synthetic Data Generator
        |
        v
PostgreSQL <---- FastAPI Services <---- Streamlit Dashboard
        ^              |
        |              v
SQL Schema       Assignment + Metrics Engine
```

Core idea: events and experiment assignments are stored separately.  
Events describe product behavior. Assignments describe experiment exposure. Metrics are calculated by joining both.

## Quickstart

### 1. Run With Docker

```bash
copy .env.example .env
docker compose up --build
```

Open:

| Service | URL |
|---|---|
| API | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |
| Dashboard | `http://localhost:8501` |
| PostgreSQL | `localhost:5432` |

Docker applies the schema and seed data from `sql/` on first volume creation.

### 2. Local Run

Requires PostgreSQL on `localhost:5432`.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

python -m app.db.init_db --schema --seed
python -m app.db.ingest_events --users 250 --days 60 --seed 42

uvicorn app.main:app --reload
streamlit run dashboard/app.py
```

## Demo Flow

1. Start the project.
2. Open `http://localhost:8000/docs`.
3. Create an experiment.
4. Assign users to variants.
5. Run analysis.
6. Open `http://localhost:8501`.
7. Show group sizes, metrics, uplift, p-values, and summary.

Create experiment:

```bash
curl -X POST http://localhost:8000/experiments ^
  -H "Content-Type: application/json" ^
  -d "{\"experiment_key\":\"checkout_copy_v2\",\"name\":\"Checkout Copy Test\",\"hypothesis\":\"New checkout copy improves purchase conversion\",\"owner_name\":\"Ahmed\",\"primary_metric_key\":\"conversion_rate\",\"variants\":[{\"variant_key\":\"control\",\"name\":\"Control\",\"is_control\":true,\"allocation_percent\":\"50\"},{\"variant_key\":\"treatment\",\"name\":\"Treatment\",\"is_control\":false,\"allocation_percent\":\"50\"}]}"
```

Assign users:

```bash
curl -X POST http://localhost:8000/experiments/checkout_copy_v2/start ^
  -H "Content-Type: application/json" ^
  -d "{\"user_ids\":[1,2,3,4,5,6],\"assignment_source\":\"hash\"}"
```

Run analysis:

```bash
curl -X POST http://localhost:8000/experiments/checkout_copy_v2/analyze
```

## Metrics

| Metric | Meaning | Level |
|---|---|---|
| `conversion_rate` | Share of assigned users with at least one purchase | User |
| `average_revenue_per_user` | Purchase revenue per assigned user | User |
| `average_order_value` | Revenue per purchase event | Order |
| `purchase_rate` | Average number of purchases per assigned user | User |

Statistical methods:

- binary metric: two-proportion z-test;
- numeric metrics: Welch's t-test;
- output: baseline value, treatment value, absolute lift, relative lift, p-value, confidence interval.

Details: [docs/metrics.md](docs/metrics.md).

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service healthcheck |
| `GET` | `/experiments` | List experiments |
| `GET` | `/experiments/{id}` | Experiment details |
| `GET` | `/experiments/{id}/assignments` | Group sizes |
| `GET` | `/experiments/{id}/metrics` | Live metrics from assignments/events |
| `GET` | `/experiments/{id}/results` | Saved analysis results |
| `GET` | `/users/summary` | User data summary |
| `GET` | `/events/summary` | Event data summary |
| `POST` | `/experiments` | Create experiment |
| `POST` | `/experiments/{experiment_key}/start` | Assign users |
| `POST` | `/experiments/{experiment_key}/analyze` | Calculate and save results |

## Dashboard

The Streamlit dashboard shows:

- experiment list and status;
- control/treatment group sizes;
- live metrics calculated from current data;
- saved statistical results;
- short text summary: whether an effect was detected and how reliable it looks.

Important distinction:

- `/metrics` calculates current metrics on the fly;
- `/results` reads saved results from `experiment_results` after `/analyze`.

## Repository Structure

```text
.
|-- app/
|   |-- api/              # FastAPI routes
|   |-- db/               # DB connection and initialization
|   |-- experiments/      # assignment, metrics, synthetic data
|   |-- schemas/          # Pydantic response/request models
|   `-- services/         # business services and read models
|-- dashboard/            # Streamlit UI
|-- docs/                 # architecture, metrics, interview notes
|-- sql/                  # PostgreSQL schema and seed data
|-- tests/                # pytest suite
|-- docker-compose.yml
|-- Dockerfile
|-- Makefile
`-- README.md
```

## Tests and CI

Run locally:

```bash
pytest -q
python -m compileall app dashboard tests
```

Or:

```bash
make check
```

GitHub Actions runs:

- dependency installation;
- Python compile check;
- pytest;
- Docker image build.

## Documentation

- [Architecture](docs/architecture.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Synthetic Data Decisions](docs/decisions.md)
- [Experiment Flow](docs/experiment_flow.md)
- [Metrics and Statistics](docs/metrics.md)
- [Resume Bullets](docs/resume_bullets.md)
- [Interview Story](docs/interview_story.md)
- [Demo Checklist](demo-checklist.md)

## Why This Is Portfolio-Ready

This project is designed to be discussed in an interview:

- clear business problem;
- understandable data model;
- reproducible assignment logic;
- practical product metrics;
- honest statistical analysis;
- API and dashboard for demonstration;
- tests, Docker, CI, and documentation.

## Limitations

- Synthetic data is not a substitute for real production data.
- Assignment is hash-based and does not yet support stratification or overlapping experiment checks.
- No SRM check, CUPED, sequential testing, or multiple testing correction.
- Revenue metrics may be skewed, so p-values should be interpreted carefully.
- Dashboard is an MVP for demonstration, not a full BI system.

## License

MIT License. See [LICENSE](LICENSE).
