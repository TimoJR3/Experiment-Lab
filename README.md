# Experiment Lab

## Обзор проекта

Experiment Lab моделирует работу аналитика над продуктовым A/B-тестом. Вместо
анализа в notebook проект показывает end-to-end упаковку:

- генерация synthetic users и событий;
- хранение событий, экспериментов и назначений в PostgreSQL;
- deterministic assignment пользователей в control/treatment;
- расчёт conversion rate, ARPU, AOV, purchase rate;
- расчёт uplift, p-value и confidence interval;
- выдача результатов через FastAPI;
- русскоязычный Streamlit dashboard для демонстрации результата.

Проект хорошо подходит для обсуждения на стажировку Product Analyst /
Data Analyst, потому что показывает не только формулы, но и понимание полного
аналитического workflow.

## Контекст эксперимента

Demo-сценарий — e-commerce / product app с checkout funnel. Пользователь может:

- открыть приложение;
- посмотреть товар;
- добавить товар в корзину;
- совершить покупку;
- начать подписку;
- продлить подписку.

Продуктовая задача: понять, помогает ли новая версия checkout улучшить
покупательское поведение. В проекте это демонстрируется на эксперименте:

```text
big_data_checkout_test
```

## Пример гипотезы

```text
Если изменить checkout experience, пользователи будут чаще завершать покупку,
а ключевая метрика conversion_rate вырастет.
```

Гипотеза специально простая: она понятна бизнесу, проверяема через события и
связана с конкретной метрикой.

## Дизайн эксперимента

В проекте есть две группы:

| Группа | Что означает |
|---|---|
| `control` | Текущая версия checkout |
| `treatment` | Тестовая версия checkout |

Assignment устроен deterministic:

- берётся пара `experiment_key:user_id`;
- считается hash;
- hash переводится в bucket от 0 до 100;
- bucket попадает в диапазон control или treatment;
- результат сохраняется в `experiment_assignments`.

Почему это важно: один и тот же пользователь должен оставаться в одной группе
при повторном расчёте. Иначе метрики могут меняться не из-за продукта, а из-за
нестабильного assignment.

Для demo-эксперимента используется сплит:

```text
control: 50%
treatment: 50%
```

## Метрики

В проекте реализованы четыре продуктовые метрики и несколько статистических
полей для интерпретации.

| Метрика | Простое объяснение | Зачем аналитику |
|---|---|---|
| `conversion_rate` | Доля назначенных пользователей, которые сделали хотя бы одну покупку | Проверить, увеличивает ли treatment вероятность покупки |
| `average_revenue_per_user` / ARPU | Средняя выручка на назначенного пользователя | Понять, растёт ли денежная отдача на пользователя |
| `average_order_value` / AOV | Средняя сумма одного `purchase` события | Проверить, не падает ли средний чек |
| `purchase_rate` | Среднее число покупок на назначенного пользователя | Оценить частоту покупок |
| `absolute_lift` | `treatment - control` | Показать размер эффекта в абсолютных единицах |
| `relative_lift` | `(treatment - control) / control` | Показать относительное изменение |
| `p_value` | Совместимость наблюдаемой разницы с нулевой гипотезой | Оценить статистическую убедительность |
| `confidence_interval` | Диапазон неопределённости для эффекта | Понять, насколько точна оценка |

### Conversion rate

Conversion rate — доля пользователей, которые совершили целевое действие. В
этом проекте целевое действие — `purchase`.

```text
conversion_rate = users_with_purchase / assigned_users
```

### ARPU

ARPU показывает среднюю выручку на назначенного пользователя. Пользователи без
покупок входят в знаменатель с revenue = 0.

```text
ARPU = total_purchase_revenue / assigned_users
```

### AOV

AOV показывает средний чек среди purchase-событий.

```text
AOV = total_purchase_revenue / purchase_events
```

### Uplift

Uplift показывает, насколько treatment отличается от control.

```text
absolute uplift = treatment_metric - control_metric
relative uplift = (treatment_metric - control_metric) / control_metric
```

### P-value

P-value не означает “вероятность, что treatment победил”. В проекте p-value
используется как показатель того, насколько наблюдаемая разница совместима с
нулевой гипотезой, где эффекта между группами нет.

### Confidence interval

Confidence interval показывает диапазон возможных значений эффекта с учётом
статистической неопределённости. Если интервал пересекает 0, направление
эффекта нельзя считать устойчивым.

### Statistical significance

В проекте результат считается statistically significant, если `p_value < 0.05`.
Это учебное правило для demo-проекта. В реальной аналитике дополнительно нужно
смотреть на дизайн эксперимента, качество данных, размер эффекта и ограничения.

## Статистические методы

В проекте используются базовые и объяснимые методы:

| Тип метрики | Метод |
|---|---|
| Бинарная метрика `conversion_rate` | two-proportion z-test |
| Числовые метрики ARPU, AOV, purchase rate | Welch t-test |
| Интервалы | 95% confidence interval для разницы treatment-control |

Почему так: для intern/junior проекта важнее показать корректную базовую
логику и честную интерпретацию, чем добавлять сложные методы без необходимости.

## Архитектура проекта

```text
PostgreSQL
  users, events, experiments, variants, assignments, metrics, results

FastAPI
  endpoints для health, experiments, assignments, metrics, results, summaries

Metrics engine
  conversion rate, ARPU, AOV, purchase rate, uplift, p-value, CI

Streamlit dashboard
  русскоязычная визуальная демонстрация A/B-теста
```

Dashboard получает данные через FastAPI. Он не обращается к PostgreSQL
напрямую.

## API endpoints

Эти endpoints реально есть в `app/api/routes.py`.

| Method | Endpoint | Что делает |
|---|---|---|
| `GET` | `/health` | Проверка доступности API |
| `GET` | `/experiments` | Список экспериментов для dashboard |
| `GET` | `/experiments/{id}` | Детали эксперимента по числовому id |
| `GET` | `/experiments/{id}/assignments` | Размеры групп control/treatment |
| `GET` | `/experiments/{id}/metrics` | Live-расчёт метрик по текущим данным |
| `GET` | `/experiments/{id}/results` | Сохранённые результаты анализа |
| `GET` | `/users/summary` | Summary по пользователям |
| `GET` | `/events/summary` | Summary по событиям |
| `POST` | `/experiments` | Создание draft experiment |
| `POST` | `/experiments/{experiment_key}/start` | Назначение пользователей в варианты |
| `POST` | `/experiments/{experiment_key}/analyze` | Расчёт и сохранение результатов |

TODO: в репозитории пока нет отдельного screenshot Swagger / request example.
Swagger доступен локально после запуска API.

## Dashboard и скриншоты

Dashboard запускается через Streamlit и показывает весь experiment flow:
overview → список экспериментов → выбранный эксперимент → группы →
метрики → статистический вывод.

### 1. Обзор проекта и synthetic event log

![Обзор dashboard](docs/assets/screenshots/01_dashboard_overview.png)

Что показано: количество пользователей, событий, типов событий и выручка.

Как связано с experiment flow: это стартовая точка анализа — перед A/B-тестом
аналитик должен понимать, какие данные доступны.

Почему важно для аналитика: без проверки объёма и природы данных нельзя
доверять последующим метрикам.

### 2. Распределение событий и список экспериментов

![Распределение событий и список экспериментов](docs/assets/screenshots/02_events_and_experiments.png)

Что показано: event distribution и таблица экспериментов.

Как связано с experiment flow: события дают основу для расчёта метрик, а список
экспериментов показывает, какие тесты можно анализировать.

Почему важно для аналитика: видно, что данные не являются одним случайным
числом, а похожи на воронку поведения пользователей.

### 3. Выбранный эксперимент и разбиение пользователей

![Выбранный эксперимент и группы](docs/assets/screenshots/03_selected_experiment.png)

Что показано: гипотеза, ключ эксперимента, статус, owner и размеры групп.

Как связано с experiment flow: это этап control/treatment assignment.

Почему важно для аналитика: размеры групп позволяют быстро увидеть, есть ли
данные для сравнения и нет ли очевидного перекоса.

### 4. Сравнение метрик control и treatment

![Сравнение метрик](docs/assets/screenshots/04_metrics.png)

Что показано: conversion rate, ARPU, AOV, purchase rate, uplift и p-value по
метрикам.

Как связано с experiment flow: это основная аналитическая часть A/B-теста —
сравнение групп по заранее выбранным метрикам.

Почему важно для аналитика: можно увидеть не только направление эффекта, но и
его размер.

### 5. Статистические результаты и итоговая интерпретация

![Статистические результаты](docs/assets/screenshots/05_statistical_results.png)

Что показано: сохранённые результаты анализа, p-value, confidence interval,
significance flag и итоговый текстовый вывод.

Как связано с experiment flow: это финальный этап — интерпретация результата и
ограничений.

Почему важно для аналитика: задача аналитика не заканчивается расчётом метрик;
нужно объяснить, насколько результат надёжен и можно ли использовать его для
решения.

## Как запустить локально

### Быстрый запуск через Docker Compose

```bash
git clone https://github.com/TimoJR3/Experiment-Lab.git
cd Experiment-Lab
docker compose up --build -d
docker compose exec api python -m app.db.prepare_demo
```

Открыть:

| Сервис | URL |
|---|---|
| Streamlit dashboard | `http://localhost:8501` |
| FastAPI Swagger | `http://localhost:8000/docs` |

В dashboard выберите:

```text
big_data_checkout_test
```

### Если порт PostgreSQL занят

```powershell
$env:POSTGRES_HOST_PORT="5433"
$env:API_HOST_PORT="8001"
$env:DASHBOARD_HOST_PORT="8502"
docker compose up --build -d
docker compose exec api python -m app.db.prepare_demo
```

После этого:

```text
Dashboard: http://localhost:8502
Swagger: http://localhost:8001/docs
```

### Локальный запуск без Docker

Нужен запущенный PostgreSQL.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

python -m app.db.init_db --schema --seed
python -m app.db.prepare_demo

uvicorn app.main:app --reload
streamlit run dashboard/app.py
```

## Примеры API-запросов

Проверка API:

```bash
curl http://localhost:8000/health
```

Список экспериментов:

```bash
curl http://localhost:8000/experiments
```

Summary по событиям:

```bash
curl http://localhost:8000/events/summary
```

Live-метрики выбранного эксперимента:

```bash
curl http://localhost:8000/experiments/1/metrics
```

Сохранённые результаты анализа:

```bash
curl http://localhost:8000/experiments/1/results
```

Запуск анализа по ключу эксперимента:

```bash
curl -X POST http://localhost:8000/experiments/big_data_checkout_test/analyze
```

PowerShell иногда использует alias `curl`. Если команда ведёт себя не так,
используйте:

```powershell
curl.exe http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health
```

## Структура репозитория

```text
.
├── app/
│   ├── api/             # FastAPI routes
│   ├── core/            # настройки приложения
│   ├── db/              # подключение к БД, init, ingestion, prepare_demo
│   ├── experiments/     # assignment, synthetic data, metrics engine
│   ├── schemas/         # Pydantic schemas
│   └── services/        # сервисный слой экспериментов, метрик и dashboard
├── dashboard/           # Streamlit dashboard
├── docs/                # документация и screenshots
├── sql/                 # PostgreSQL schema и seed data
├── tests/               # pytest tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Ограничения

- Данные synthetic и не отражают реальный трафик.
- Проект не доказывает реальный бизнес-эффект.
- Demo-сценарий сфокусирован на checkout и purchase behavior.
- Assignment hash-based, без стратификации.
- Нет SRM check.
- Нет power analysis и расчёта минимального размера выборки.
- Нет CUPED.
- Нет sequential testing.
- Нет коррекции на multiple testing.
- Revenue-метрики могут быть скошенными, поэтому p-value нужно трактовать
  осторожно.
- Dashboard создан для демонстрации аналитического workflow, а не как замена BI.

## Проверки

```bash
python -m compileall app dashboard tests
pytest -q
ruff check .
```

## GitHub-подача

Описание репозитория:

```text
Демонстрационный проект по A/B-тестированию с расчётом продуктовых метрик, статистической интерпретацией, FastAPI, PostgreSQL и Streamlit.
```

Topics:

```text
product-analytics, ab-testing, python, fastapi, postgresql, streamlit, statistics, uplift, confidence-intervals
```

## Документация

- [Продуктовый кейс](docs/product_case.md)
- [Заметки для собеседования](docs/interview_notes.md)
- [Архитектура](docs/architecture.md)
- [Словарь данных](docs/data_dictionary.md)
- [Решения по synthetic data](docs/decisions.md)
- [Жизненный цикл эксперимента](docs/experiment_flow.md)
- [Метрики и статистика](docs/metrics.md)
- [Demo checklist](docs/demo_checklist.md)
- [Bullets для резюме](docs/resume_bullets.md)

## License

MIT License. См. [LICENSE](LICENSE).
