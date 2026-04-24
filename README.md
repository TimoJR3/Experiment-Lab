# Experiment Lab

Experiment Lab — portfolio-проект для моделирования и анализа продуктовых A/B экспериментов.  
Проект показывает полный путь от событий пользователей до assignment, расчета метрик, статистического анализа, API и dashboard.

## Что умеет проект

- хранит пользователей, события, эксперименты, варианты и assignment в PostgreSQL;
- генерирует synthetic event stream для e-commerce/product app сценария;
- детерминированно назначает пользователей в `control` / `treatment`;
- считает продуктовые метрики по эксперименту;
- выполняет базовый статистический анализ;
- сохраняет результаты анализа;
- отдает read-only API для dashboard;
- показывает MVP dashboard в Streamlit.

## Стек

- Python 3.11
- FastAPI
- Streamlit
- PostgreSQL
- Docker Compose
- pandas
- SciPy / statsmodels
- pytest
- GitHub Actions

## Структура

```text
.
|-- app/
|   |-- api/
|   |-- core/
|   |-- db/
|   |-- experiments/
|   |-- schemas/
|   |-- services/
|   `-- main.py
|-- dashboard/
|-- docs/
|-- sql/
|-- tests/
|-- .github/workflows/
|-- .env.example
|-- Dockerfile
|-- Makefile
|-- docker-compose.yml
|-- requirements.txt
`-- README.md
```

## Быстрый старт через Docker

```bash
copy .env.example .env
docker compose up --build
```

После запуска:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`
- PostgreSQL: `localhost:5432`

Docker Compose автоматически применяет SQL schema из `sql/001_init_schema.sql` и seed из `sql/002_seed_data.sql` при первом создании volume.

## Локальный запуск

Для локального запуска нужен PostgreSQL на `localhost:5432`.

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

## Тесты и проверки

```bash
pytest -q
python -m compileall app dashboard tests
```

Через Makefile:

```bash
make check
```

CI в `.github/workflows/ci.yml` запускает:

- установку зависимостей;
- `compileall`;
- `pytest`;
- сборку Docker image.

## Demo Flow

1. Поднять проект через Docker Compose.
2. Проверить API: `GET /health`.
3. Сгенерировать события, если нужен больший dataset:

```bash
python -m app.db.ingest_events --users 250 --days 60 --seed 42
```

4. Создать эксперимент:

```bash
curl -X POST http://localhost:8000/experiments ^
  -H "Content-Type: application/json" ^
  -d "{\"experiment_key\":\"checkout_copy_v2\",\"name\":\"Checkout Copy Test\",\"hypothesis\":\"New checkout copy improves purchase conversion\",\"owner_name\":\"Ahmed\",\"primary_metric_key\":\"conversion_rate\",\"variants\":[{\"variant_key\":\"control\",\"name\":\"Control\",\"is_control\":true,\"allocation_percent\":\"50\"},{\"variant_key\":\"treatment\",\"name\":\"Treatment\",\"is_control\":false,\"allocation_percent\":\"50\"}]}"
```

5. Назначить пользователей в группы:

```bash
curl -X POST http://localhost:8000/experiments/checkout_copy_v2/start ^
  -H "Content-Type: application/json" ^
  -d "{\"user_ids\":[1,2,3,4,5,6],\"assignment_source\":\"hash\"}"
```

6. Посчитать и сохранить результаты:

```bash
curl -X POST http://localhost:8000/experiments/checkout_copy_v2/analyze
```

7. Открыть dashboard: `http://localhost:8501`.

## Основные API Endpoints

- `GET /health` — healthcheck.
- `GET /experiments` — список экспериментов.
- `GET /experiments/{id}` — детали эксперимента.
- `GET /experiments/{id}/assignments` — размеры групп.
- `GET /experiments/{id}/metrics` — live metrics из текущих assignments/events.
- `GET /experiments/{id}/results` — сохраненные результаты анализа.
- `GET /users/summary` — сводка по пользователям.
- `GET /events/summary` — сводка по событиям.
- `POST /experiments` — создать эксперимент.
- `POST /experiments/{experiment_key}/start` — запустить experiment assignment.
- `POST /experiments/{experiment_key}/analyze` — посчитать и сохранить анализ.

## Метрики

Реализованы:

- `conversion_rate` — доля пользователей с хотя бы одной покупкой;
- `average_revenue_per_user` — revenue на назначенного пользователя;
- `average_order_value` — средний чек по purchase events;
- `purchase_rate` — среднее число покупок на пользователя.

Статистика:

- для бинарной метрики используется two-proportion z-test;
- для числовых метрик используется Welch's t-test;
- считаются absolute lift, relative lift, p-value и confidence interval.

Подробности: [docs/metrics.md](docs/metrics.md).

## Что считает API, а что уже сохранено

- `/experiments/{id}/metrics` считает live metrics на лету из `experiment_assignments` и `events`.
- `/experiments/{id}/results` читает сохраненные результаты из `experiment_results`.
- Dashboard показывает оба слоя: текущие live metrics и сохраненный statistical output после `POST /analyze`.

## Документация

- [docs/architecture.md](docs/architecture.md) — архитектура проекта.
- [docs/data_dictionary.md](docs/data_dictionary.md) — таблицы и связи.
- [docs/decisions.md](docs/decisions.md) — решения по synthetic data.
- [docs/experiment_flow.md](docs/experiment_flow.md) — lifecycle эксперимента.
- [docs/metrics.md](docs/metrics.md) — формулы и статистика.
- [docs/resume_bullets.md](docs/resume_bullets.md) — bullets для резюме.
- [docs/interview_story.md](docs/interview_story.md) — story для интервью.
- [demo-checklist.md](demo-checklist.md) — checklist для демонстрации.

## Ограничения

- Synthetic data не заменяет реальные продуктовые данные.
- Assignment пока hash-based без stratification и overlap checks.
- Нет SRM check, CUPED и поправки на множественные проверки.
- Dashboard — MVP для демонстрации логики, не production BI.
- Revenue-метрики могут иметь скошенное распределение, поэтому p-value надо интерпретировать аккуратно.
