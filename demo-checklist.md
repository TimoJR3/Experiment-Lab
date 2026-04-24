# Demo Checklist

## Before Demo

- Make sure Docker Desktop is running.
- Run `copy .env.example .env` if `.env` does not exist.
- Run `docker compose up --build`.
- Open API docs at `http://localhost:8000/docs`.
- Open dashboard at `http://localhost:8501`.

## Smoke Checks

- `GET /health` returns `{"status": "ok"}`.
- `GET /users/summary` returns non-zero users.
- `GET /events/summary` returns event counts.
- Dashboard loads without API connection errors.

## Demo Flow

1. Show repository structure.
2. Show PostgreSQL schema in `sql/001_init_schema.sql`.
3. Show synthetic data generator in `app/experiments/synthetic_data.py`.
4. Show deterministic assignment in `app/experiments/assignment.py`.
5. Show metrics engine in `app/experiments/metrics.py`.
6. Show FastAPI docs and endpoints.
7. Show Streamlit dashboard.
8. Explain live metrics versus saved results.
9. Show tests and GitHub Actions workflow.

## Good Talking Points

- The project is not just EDA; it is an analytics service with engineering packaging.
- Assignment is deterministic, reproducible, and stored.
- Metrics are calculated from event data after assignment.
- Statistical methods are intentionally simple and explainable.
- Dashboard calls FastAPI rather than querying the database directly.
- CI makes the project safer to change.

## Known Limitations To Mention

- Synthetic data is not real production data.
- No migrations yet.
- No SRM checks or CUPED yet.
- No overlapping experiment protection.
- Dashboard is intentionally MVP.
