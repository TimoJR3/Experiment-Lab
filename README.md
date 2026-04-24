# Experiment Lab

Experiment Lab — это pet-project для портфолио, в котором моделируется сервис для запуска и анализа продуктовых экспериментов.  
Этап 1 содержит только scaffold проекта: API, dashboard, контейнер с базой данных, тесты и базовую инженерную упаковку.

## Стек

- Python 3.11
- FastAPI
- Streamlit
- PostgreSQL
- Docker Compose
- pandas
- SciPy / statsmodels
- pytest

## Структура репозитория

```text
.
|-- app/
|   |-- api/
|   |-- core/
|   |-- db/
|   |-- experiments/
|   |-- models/
|   |-- schemas/
|   |-- services/
|   `-- main.py
|-- dashboard/
|-- docs/
|-- sql/
|-- tests/
|-- .env.example
|-- Dockerfile
|-- Makefile
|-- README.md
|-- docker-compose.yml
`-- requirements.txt
```

## Быстрый старт

### Локальный запуск

1. Создай и активируй виртуальное окружение.
2. Скопируй `.env.example` в `.env`.
3. Установи зависимости.
4. Запусти API и dashboard.

```bash
python -m venv .venv
.venv\Scripts\activate
copy .env.example .env
pip install -r requirements.txt
python -m app.db.init_db --schema --seed
uvicorn app.main:app --reload
streamlit run dashboard/app.py
pytest -q
```

### Запуск через Docker

```bash
copy .env.example .env
docker compose up --build
```

API будет доступен на `http://localhost:8000`, dashboard — на `http://localhost:8501`.

### Генерация synthetic data

Сгенерировать preview без загрузки в БД:

```bash
python -m app.experiments.synthetic_data --users 250 --days 60 --seed 42
```

Сгенерировать данные и загрузить их в PostgreSQL:

```bash
python -m app.db.ingest_events --users 250 --days 60 --seed 42
```

### MVP dashboard

Запуск API:

```bash
uvicorn app.main:app --reload
```

Запуск dashboard:

```bash
streamlit run dashboard/app.py
```

Dashboard читает данные из FastAPI через `API_BASE_URL`. Локально по умолчанию используется `http://localhost:8000`, в Docker Compose для dashboard автоматически выставляется `http://api:8000`.

Минимальный demo-сценарий:

```bash
python -m app.db.init_db --schema --seed
python -m app.db.ingest_events --users 250 --days 60 --seed 42
uvicorn app.main:app --reload
streamlit run dashboard/app.py
```

После создания, запуска и анализа эксперимента dashboard покажет:

- список экспериментов;
- статус выбранного эксперимента;
- размеры групп control / treatment;
- live metrics, рассчитанные из `experiment_assignments` и `events`;
- saved results из таблицы `experiment_results`;
- краткое summary по статистической надежности эффекта.

## Доступные endpoints

- `GET /health` возвращает статус API.
- `POST /experiments` создаёт эксперимент в статусе `draft`.
- `POST /experiments/{experiment_key}/start` запускает эксперимент и сохраняет назначения пользователей.
- `POST /experiments/{experiment_key}/analyze` считает метрики эксперимента и сохраняет результаты.
- `GET /experiments` возвращает список экспериментов для dashboard.
- `GET /experiments/{id}` возвращает детали эксперимента.
- `GET /experiments/{id}/assignments` возвращает размеры групп.
- `GET /experiments/{id}/metrics` считает текущие метрики без сохранения.
- `GET /experiments/{id}/results` возвращает сохраненные результаты анализа.
- `GET /users/summary` возвращает сводку по пользователям.
- `GET /events/summary` возвращает сводку по событиям.

## Что входит в текущий этап

На этапе 1 проект специально не включает:

- логику экспериментов
- ingestion событий
- разбиение пользователей на группы
- статистический анализ
- полноценные продуктовые dashboard

## Что будет дальше

Следующий этап — добавить первые реальные сущности и работу с данными:

- PostgreSQL schema для событий и экспериментов
- SQLAlchemy models
- простой CRUD для описания эксперимента
- базовую загрузку demo-данных
