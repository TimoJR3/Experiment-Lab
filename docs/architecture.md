# Architecture

Experiment Lab построен как простой layered application: данные хранятся в PostgreSQL, backend отдает API и выполняет бизнес-логику, Streamlit показывает dashboard.

## High-level Flow

```text
Synthetic Data Generator
        |
        v
PostgreSQL <---- FastAPI Services <---- Streamlit Dashboard
        ^              |
        |              v
SQL Schema       Metrics / Assignment Engine
```

## Layers

```text
dashboard/
    Streamlit UI, calls FastAPI only

app/api/
    FastAPI routes and HTTP error mapping

app/services/
    Application services: experiments, metrics, dashboard read models

app/experiments/
    Pure logic: deterministic assignment, synthetic data, metrics engine

app/db/
    DB connection helpers and schema initialization

sql/
    PostgreSQL schema and seed dataset
```

## Main Components

- `ExperimentService` creates experiments, validates statuses, assigns users, and stores assignments.
- `MetricsService` loads assigned users and events, calculates metrics, runs tests, and saves results.
- `DashboardService` exposes read-only dashboard data: experiment list, group sizes, live metrics, saved results, users/events summaries.
- `assignment.py` contains deterministic hash-based split logic.
- `metrics.py` contains pure metric formulas and statistical tests.
- `synthetic_data.py` generates reproducible e-commerce/product events.

## Data Model

Core tables:

- `users`
- `events`
- `experiments`
- `experiment_variants`
- `experiment_assignments`
- `metrics_definitions`
- `experiment_results`

The important design choice is that assignments are stored separately from events. Events describe product behavior, assignments describe experiment exposure. Metrics are calculated by joining those two facts.

## API and Dashboard Boundary

The dashboard does not query PostgreSQL directly. It calls FastAPI endpoints:

- `/experiments`
- `/experiments/{id}/assignments`
- `/experiments/{id}/metrics`
- `/experiments/{id}/results`
- `/users/summary`
- `/events/summary`

This keeps the UI simple and makes backend logic testable without Streamlit.

## Testing Strategy

- Pure unit tests cover assignment and metrics logic.
- Service tests use fake repositories.
- API tests use FastAPI `TestClient` and monkeypatch services.
- SQL schema tests check required tables and seed data.
- CI runs `compileall`, `pytest`, and Docker image build.
