# Interview Story

## 60-90 Second Pitch

Experiment Lab is a portfolio project where I built a small A/B testing platform for product experiments. The goal was to show not only data analysis, but also engineering packaging around it: PostgreSQL schema, FastAPI backend, deterministic assignment logic, metrics engine, statistical analysis, tests, Docker Compose, CI, and a Streamlit dashboard.

The project simulates an e-commerce/product app. It generates users and events like `app_open`, `view_item`, `add_to_cart`, `purchase`, and subscription events. Users are assigned to control or treatment with a deterministic hash split, so the same user always lands in the same group for the same experiment. Then the metrics layer calculates conversion rate, ARPU, average order value, and purchase rate, estimates uplift, runs basic statistical tests, and stores results for the dashboard.

The main value is that the project mirrors a real product analytics workflow: define experiment, assign users, collect events, calculate metrics, interpret results, and present them in a simple dashboard.

## Business Problem

The business problem is deciding whether a product change improves user behavior. For example, a new checkout copy might increase purchase conversion or revenue. Instead of relying on intuition, the project models an experiment workflow where users are split into groups and outcomes are compared with metrics and statistical tests.

## Data Model

The data model separates product behavior from experiment exposure:

- `users` stores user attributes.
- `events` stores product behavior.
- `experiments` stores experiment metadata and status.
- `experiment_variants` stores control/treatment variants.
- `experiment_assignments` stores which user saw which variant.
- `metrics_definitions` stores metric metadata.
- `experiment_results` stores calculated analysis results.

The key design choice is keeping assignment separate from events. This makes analysis reproducible and lets the same event stream support multiple experiments.

## Assignment Logic

Assignment is deterministic and hash-based. The engine hashes `experiment_key:user_id`, converts it into a bucket from 0 to 100, and maps that bucket to variant allocation percentages.

This is useful because:

- the same user gets the same variant on repeated runs;
- assignment can be recalculated and audited;
- duplicate assignments are prevented in the database;
- the logic is simple enough to test and explain.

## Metrics

The metrics engine calculates:

- conversion rate: users with at least one purchase divided by assigned users;
- ARPU: purchase revenue divided by assigned users;
- average order value: revenue divided by purchase events;
- purchase rate: purchase events divided by assigned users.

The engine also calculates absolute lift and relative lift for treatment versus control.

## Statistical Analysis

For conversion rate, the project uses a two-proportion z-test because the metric is binary at user level. For numeric metrics, it uses Welch's t-test because group variance and sample sizes can differ.

The output includes:

- baseline value;
- treatment value;
- uplift;
- p-value;
- confidence interval;
- significance flag.

I would explain that these tests are intentionally basic and suitable for a first version, not a replacement for a mature experimentation platform.

## Dashboard

The dashboard shows:

- list of experiments;
- status and metadata;
- group sizes;
- live metrics from current events and assignments;
- saved statistical results;
- short interpretation of whether the effect looks statistically reliable.

The dashboard talks to FastAPI, not directly to PostgreSQL. This keeps the UI thin and backend logic testable.

## Honest Limitations

- Synthetic data is useful for demos, but real product data would have more noise and edge cases.
- The assignment engine does not support stratification, mutual exclusion, or overlapping experiment checks.
- The statistics layer does not include SRM checks, CUPED, sequential testing, or multiple testing correction.
- Revenue distributions are often skewed, so t-test results should be interpreted carefully.
- The dashboard is an MVP, not production BI.

## How I Would Improve It Next

- Add Alembic migrations.
- Add experiment completion endpoint.
- Add SRM checks and sample size planning.
- Add configurable analysis windows.
- Add dashboard controls for creating and running demo experiments.
- Add CI integration tests with a real PostgreSQL service.
