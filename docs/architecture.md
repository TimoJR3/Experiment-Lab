# Architecture Overview

Experiment Lab uses a simple layered structure so the project stays easy to explain in an interview and easy to extend in later stages.

## Layers

```text
Dashboard (Streamlit)
        |
API Layer (FastAPI routes, schemas)
        |
Service Layer (business logic)
        |
Data Layer (db session, models, PostgreSQL)
```

## Folder Roles

- `app/api` contains HTTP routes and API-facing handlers.
- `app/core` contains settings and shared cross-cutting utilities.
- `app/db` contains database connection helpers and later will include persistence utilities.
- `sql` contains PostgreSQL schema and seed scripts for local initialization.
- `app/models` will store ORM models for events, experiments, and assignments.
- `app/schemas` contains request and response schemas.
- `app/services` will contain business logic separated from transport and storage.
- `app/experiments` is reserved for experiment-specific logic when the project moves beyond scaffold stage.
- `dashboard` contains the Streamlit UI.

## Design Principles

- Keep layers explicit and small.
- Separate transport, business logic, and persistence.
- Favor readability over abstraction.
- Make each module easy to discuss during an interview.
