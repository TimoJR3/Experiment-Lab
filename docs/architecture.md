# Architecture

Experiment Lab построен как простой layered application для демонстрации
A/B-analysis flow. Это не production experimentation platform: проект показывает
понятные границы между данными, API, расчетом метрик и dashboard.

## High-Level Flow

```text
Synthetic Data Generator
        |
        v
PostgreSQL
  users
  events
  experiments
  experiment_variants
  experiment_assignments
  metrics_definitions
  experiment_results
        |
        v
FastAPI Services
  ExperimentService
  MetricsService
  DashboardService
        |
        v
Streamlit Dashboard
```

Поток данных от events до результата:

```text
synthetic users/events
    -> PostgreSQL users/events
    -> experiment_assignments через deterministic assignment
    -> metrics engine объединяет assignments и events
    -> experiment_results сохраняет расчет analyze
    -> FastAPI отдает live metrics и saved results
    -> Streamlit dashboard показывает интерпретацию
```

## PostgreSQL

PostgreSQL хранит факты, необходимые для A/B-анализа:

- `users` — synthetic пользователи и базовые атрибуты;
- `events` — synthetic event log с `event_name`, временем и revenue value;
- `experiments` — карточки экспериментов, гипотезы, статусы и primary metric;
- `experiment_variants` — control/treatment варианты и доли allocation;
- `experiment_assignments` — зафиксированное попадание пользователя в вариант;
- `metrics_definitions` — справочник поддержанных метрик;
- `experiment_results` — сохраненные результаты статистического анализа.

Важное архитектурное решение: assignment хранится отдельно от событий. Events
описывают поведение пользователя, а assignments описывают экспериментальную
экспозицию. Метрики считаются только после join этих двух фактов.

## FastAPI

FastAPI выступает границей между backend-логикой и dashboard. Основные группы
endpoints:

- `/health` — проверка доступности API;
- `/experiments` — создание и список экспериментов;
- `/experiments/{id}` — карточка эксперимента;
- `/experiments/{id}/assignments` — размеры control/treatment групп;
- `/experiments/{id}/metrics` — live-расчет метрик без сохранения;
- `/experiments/{id}/results` — сохраненные результаты анализа;
- `/experiments/{experiment_key}/start` — deterministic assignment пользователей;
- `/experiments/{experiment_key}/analyze` — расчет и сохранение результатов;
- `/users/summary` и `/events/summary` — компактные summaries для dashboard.

Routes в `app/api/routes.py` отвечают за HTTP-слой и mapping ошибок. Основная
логика вынесена в сервисы, чтобы ее можно было тестировать без Streamlit.

## Metrics Engine

Metrics engine находится в `app/experiments/metrics.py`. Он работает с
user-level агрегатами, которые готовит `MetricsRepository`:

- считает `conversion_rate`;
- считает ARPU (`average_revenue_per_user`);
- считает AOV (`average_order_value`);
- считает `purchase_rate`;
- сравнивает control и treatment;
- возвращает absolute/relative uplift;
- считает `p_value`;
- считает 95% confidence interval;
- маркирует `is_significant` по правилу `p_value < 0.05`.

Для `conversion_rate` используется two-proportion z-test. Для ARPU, AOV и
purchase rate используется Welch t-test. Это осознанно базовый набор методов:
он достаточно прозрачен для portfolio-проекта и хорошо объясняется на интервью.

## Streamlit Dashboard

Dashboard находится в `dashboard/app.py`. Он не импортирует DB-слой и не ходит
в PostgreSQL напрямую. Все данные он получает через `httpx` и `API_BASE_URL`.

Это разделение полезно для демонстрации:

- backend можно проверять через Swagger и curl;
- dashboard остается тонким UI-слоем;
- API response schemas являются контрактом между backend и UI;
- расчет метрик можно тестировать отдельно от визуализации.

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
    DB connection helpers, schema initialization and demo preparation

sql/
    PostgreSQL schema and seed dataset
```

## Testing Strategy

- Pure unit tests cover assignment and metrics logic.
- Service tests use fake repositories.
- API tests use FastAPI `TestClient` and monkeypatch services.
- SQL schema tests check required tables and seed data.
- Documentation tests guard the portfolio positioning and public README claims.
