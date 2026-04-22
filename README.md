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

### Генерация synthetic data

Сгенерировать preview без загрузки в БД:

```bash
python -m app.experiments.synthetic_data --users 250 --days 60 --seed 42
```

Сгенерировать данные и загрузить их в PostgreSQL:

```bash
python -m app.db.ingest_events --users 250 --days 60 --seed 42
```

## Доступные endpoints

- `GET /health` возвращает статус API.

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
