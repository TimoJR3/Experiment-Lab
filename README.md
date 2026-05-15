# Experiment Lab

Experiment Lab — демонстрационный проект по A/B-тестированию для
Product Analyst / Data Analyst intern-junior роли. Проект показывает полный
аналитический цикл: от событий пользователей и разбиения на control/treatment
до продуктовых метрик, статистической интерпретации, API и dashboard.

```text
users + events -> experiment setup -> deterministic assignment
-> product metrics -> statistical analysis -> dashboard/API demo
```

## Бизнес-задача

Команда продукта хочет понять, стоит ли выкатывать изменение в checkout. Для
этого нужно не просто посмотреть на конверсию, а воспроизводимо:

- собрать события пользователей;
- создать гипотезу эксперимента;
- разделить пользователей на control и treatment;
- посчитать продуктовые метрики по группам;
- оценить uplift, p-value и confidence interval;
- сформулировать понятный продуктовый вывод.

Проект честно моделирует этот процесс на synthetic data. Это лаборатория
A/B-тестирования для демонстрации навыков, а не система для реального
продуктового трафика.

## Какие продуктовые вопросы решает проект

- Улучшает ли тестовый вариант конверсию в покупку?
- Как меняется ARPU после изменения checkout?
- Не ухудшается ли average order value?
- Меняется ли частота покупок на пользователя?
- Является ли наблюдаемый эффект статистически убедительным?
- Можно ли рассматривать treatment как кандидата на дальнейший rollout?

## Продуктовые метрики

| Метрика | Что показывает |
|---|---|
| `conversion_rate` | Доля назначенных пользователей, совершивших хотя бы одну покупку |
| `average_revenue_per_user` / ARPU | Средняя выручка на назначенного пользователя |
| `average_order_value` / AOV | Средняя сумма одного события `purchase` |
| `purchase_rate` | Среднее число покупок на назначенного пользователя |
| `absolute_lift` | Разница treatment minus control |
| `relative_lift` | Относительное изменение к control |
| `p_value` | Насколько наблюдаемая разница совместима с нулевой гипотезой |
| `confidence_interval` | Интервал неопределенности для разницы treatment-control |

## Дизайн эксперимента

В проекте используется deterministic assignment:

- для каждого пользователя считается hash от `experiment_key:user_id`;
- hash переводится в стабильный bucket;
- bucket сопоставляется с вариантом эксперимента;
- один и тот же пользователь при повторном расчете попадает в ту же группу;
- assignment сохраняется в PostgreSQL в таблице `experiment_assignments`;
- дубли защищены ограничением уникальности `(experiment_id, user_id)`.

Для demo-эксперимента используется разбиение:

```text
control: 50%
treatment: 50%
```

Такой подход нужен, чтобы результат анализа был воспроизводимым: если
пользователь случайно меняет группу между запусками, метрики становятся
нестабильными.

## Статистическая интерпретация

Первая версия использует простые и объяснимые методы:

- для бинарной метрики `conversion_rate` используется z-test для двух долей;
- для числовых метрик ARPU, AOV и purchase rate используется Welch t-test;
- dashboard показывает uplift, p-value, confidence interval и текстовый вывод.

Пример интерпретации:

```text
Вариант B улучшил метрику, но результат пока не является статистически
значимым. Это сигнал для анализа, а не доказанное продуктовое решение.
```

## Архитектура

```text
PostgreSQL
  хранит users, events, experiments, assignments, metric definitions, results

FastAPI
  отдает health, summaries, experiments, assignments, metrics, results

Metrics engine
  считает conversion rate, ARPU, AOV, purchase rate, uplift и статтесты

Streamlit dashboard
  показывает русскоязычный интерфейс для демонстрации A/B-теста
```

Dashboard получает данные через FastAPI и не ходит в PostgreSQL напрямую.

## Схема данных

| Таблица | Назначение |
|---|---|
| `users` | Synthetic users с датой регистрации и атрибутами привлечения |
| `events` | События продукта: open, view, cart, purchase, subscription |
| `experiments` | Метаданные эксперимента, гипотеза, статус, владелец, основная метрика |
| `experiment_variants` | Варианты control/treatment и проценты распределения |
| `experiment_assignments` | Сохраненное назначение user-to-variant |
| `metrics_definitions` | Справочник поддерживаемых метрик |
| `experiment_results` | Сохраненные результаты анализа после `/analyze` |

Подробнее: [docs/data_dictionary.md](docs/data_dictionary.md).

## Быстрый запуск демо

```bash
git clone https://github.com/TimoJR3/Experiment-Lab.git
cd Experiment-Lab
docker compose up --build -d
docker compose exec api python -m app.db.prepare_demo
```

Откройте:

| Сервис | URL |
|---|---|
| Dashboard | `http://localhost:8501` |
| Swagger / FastAPI Docs | `http://localhost:8000/docs` |

В dashboard выберите эксперимент:

```text
big_data_checkout_test
```

Команда подготовки демо создает или переиспользует:

- 10 000 synthetic users;
- события за 180 дней;
- demo-эксперимент `big_data_checkout_test`;
- назначения пользователей в control/treatment;
- сохраненные результаты анализа.

## Скриншоты

### Обзор

![Dashboard overview](docs/assets/screenshots/01_dashboard_overview.png)

### Распределение событий и эксперименты

![Event distribution and experiments](docs/assets/screenshots/02_events_and_experiments.png)

### Выбранный эксперимент

![Selected experiment](docs/assets/screenshots/03_selected_experiment.png)

### Метрики

![Experiment metrics](docs/assets/screenshots/04_metrics.png)

### Статистические результаты

![Statistical results](docs/assets/screenshots/05_statistical_results.png)

## Демо-сценарий

1. Запустить контейнеры через Docker Compose.
2. Подготовить данные командой `python -m app.db.prepare_demo`.
3. Открыть dashboard на `http://localhost:8501`.
4. Выбрать `big_data_checkout_test`.
5. Показать обзор: пользователи, события, типы событий, выручка.
6. Показать размеры групп control и treatment.
7. Показать метрики, uplift и p-value.
8. Показать confidence interval и итоговую интерпретацию.
9. Открыть Swagger и показать API endpoints, которые питают dashboard.

## API / Swagger

Swagger доступен по адресу:

```text
http://localhost:8000/docs
```

Основные endpoints:

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/health` | Проверка доступности API |
| `GET` | `/experiments` | Список экспериментов |
| `GET` | `/experiments/{id}` | Детали эксперимента |
| `GET` | `/experiments/{id}/assignments` | Размеры групп |
| `GET` | `/experiments/{id}/metrics` | Расчет текущих метрик |
| `GET` | `/experiments/{id}/results` | Сохраненные результаты анализа |
| `GET` | `/users/summary` | Summary по пользователям |
| `GET` | `/events/summary` | Summary по событиям |
| `POST` | `/experiments` | Создание эксперимента |
| `POST` | `/experiments/{experiment_key}/start` | Назначение пользователей |
| `POST` | `/experiments/{experiment_key}/analyze` | Расчет и сохранение результатов |

## Локальный запуск без Docker

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

## Проверки

```bash
python -m compileall app dashboard tests
pytest -q
ruff check .
```

## Troubleshooting

Если API не запущен:

```bash
docker compose ps
docker compose logs api
```

Если порты `5432`, `8000` или `8501` заняты другим проектом:

```powershell
$env:POSTGRES_HOST_PORT="5433"
$env:API_HOST_PORT="8001"
$env:DASHBOARD_HOST_PORT="8502"
docker compose up --build -d
docker compose exec api python -m app.db.prepare_demo
```

После этого откройте:

```text
Dashboard: http://localhost:8502
Swagger: http://localhost:8001/docs
```

Если PowerShell перехватывает `curl`, используйте:

```powershell
curl.exe http://localhost:8000/health
```

или:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Если данные отсутствуют, повторите:

```bash
docker compose exec api python -m app.db.prepare_demo
```

## Ограничения

- Данные synthetic, поэтому они не доказывают эффект на реальных пользователях.
- Demo-сценарий сфокусирован на checkout и purchase behavior.
- Assignment hash-based и не учитывает стратификацию.
- Нет SRM check, CUPED, sequential testing и multiple testing correction.
- Revenue-метрики могут быть скошенными, поэтому p-value нужно читать
  осторожно.
- Dashboard создан для объяснения аналитического workflow, а не как полноценный
  BI-инструмент.

## Что демонстрирует проект

Для Product Analyst / Data Analyst intern-junior роли проект показывает:

- понимание полного цикла A/B-теста;
- умение формулировать продуктовую гипотезу и метрику успеха;
- расчет conversion rate, ARPU, AOV, purchase rate и uplift;
- базовую статистическую интерпретацию p-value и confidence interval;
- моделирование event log и аналитической схемы PostgreSQL;
- воспроизводимое разделение пользователей на control/treatment;
- упаковку аналитики в FastAPI и Streamlit dashboard;
- тесты, Docker Compose и понятный demo-запуск.

## GitHub-подача

Описание репозитория:

```text
Демонстрационный проект по A/B-тестированию с расчётом продуктовых метрик, статистической интерпретацией, FastAPI, PostgreSQL и Streamlit.
```

Темы:

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
