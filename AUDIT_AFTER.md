# Audit After

## Что исправлено

- README переписан как честный portfolio case для Product/Data Analyst:
  - удалена старая строка про отсутствие Swagger screenshot / request example;
  - добавлен раздел `API и примеры запросов`;
  - добавлены curl-команды, примеры ответов и пояснения для аналитика;
  - объяснены conversion rate, ARPU, AOV, purchase rate, uplift, p-value и confidence interval;
  - добавлены блоки про интерпретацию A/B-теста и ограничения synthetic data;
  - добавлена команда `cp .env.example .env` перед Docker Compose запуском.
- Создан Swagger screenshot: `docs/images/swagger_api.png`.
- Обновлен `docs/architecture.md` с описанием PostgreSQL, FastAPI, metrics engine, Streamlit dashboard и data flow.
- Добавлен `docs/ab_testing_notes.md` с базовыми A/B testing notes.
- Расширен `.gitignore` для IDE/cache/temp/coverage артефактов.
- Обновлены документационные тесты под новую структуру README.
- Проверено, что Streamlit dashboard использует `httpx` и `API_BASE_URL`, а не прямой доступ к PostgreSQL.

## Какие файлы изменены

- `README.md`
- `.gitignore`
- `docs/architecture.md`
- `docs/ab_testing_notes.md`
- `docs/images/swagger_api.png`
- `tests/test_product_docs.py`
- `AUDIT_AFTER.md`

## Какие проверки запускались

Успешно:

```bash
python -m compileall app dashboard tests
pytest -q
PYTHONPATH=/tmp/experiment-lab-ruff python -m ruff check .
cp .env.example .env
docker compose config
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -sS http://127.0.0.1:8000/health
```

Результаты:

- `compileall` прошел.
- `pytest -q`: 55 passed, 2 warnings.
- `ruff check .`: All checks passed.
- `docker compose config` прошел после создания `.env`.
- `GET /health` вернул `{"status":"ok"}`.
- Swagger UI открылся на `http://127.0.0.1:8000/docs`; screenshot сохранен в `docs/images/swagger_api.png` и подключен в README.
- Streamlit dashboard стартовал на `http://127.0.0.1:8501` и отрендерил страницу с `API: http://127.0.0.1:8000`.
- Проверено, что dashboard использует `httpx` и `API_BASE_URL`, без прямого доступа к PostgreSQL из `dashboard/`.
- Локальные markdown-ссылки в `.md` файлах резолвятся.
- В README/docs/audit не найдено `TODO`, `placeholder`, `[ADD ...]` или `добавить потом`.

Не удалось выполнить полностью:

```bash
docker compose up --build -d
```

Что произошло:

- Docker Desktop удалось запустить через `open -a Docker`.
- `docker compose up --build -d` начал сборку images и скачал зависимости.
- Build упал на этапе unpack/export image layer с ошибкой Docker Desktop storage:

```text
failed to extract layer ... read-only file system
```

После этого Docker Desktop перешел в состояние:

```text
Docker Desktop is unable to start
```

Дополнительная диагностика показала почти полностью заполненный диск:

```text
/System/Volumes/Data: 437Gi used, 160Mi available, 100% capacity
```

Я удалил только созданные мной временные файлы и Python cache. Агрессивную
очистку Docker storage (`docker system prune -a`, reset Docker Desktop data)
не выполнял, чтобы не удалить пользовательские Docker images/volumes.

Из-за этого не были завершены:

```bash
docker compose exec api python -m app.db.prepare_demo
curl http://localhost:8000/experiments
docker compose ps
docker compose down
```

При локальном запуске API без Docker endpoint `/experiments` возвращал 500,
потому что PostgreSQL с ожидаемыми demo credentials не был доступен. Это
ожидаемо для проверки без поднятого Compose-стека.

## Финальный git status перед коммитом

Ожидаемые изменения:

```text
M  .gitignore
M  README.md
M  docs/architecture.md
M  tests/test_product_docs.py
A  AUDIT_AFTER.md
A  docs/ab_testing_notes.md
A  docs/images/swagger_api.png
```

## Что осталось проверить вручную

После освобождения места на диске и восстановления Docker Desktop:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose exec api python -m app.db.prepare_demo
curl http://localhost:8000/health
curl http://localhost:8000/experiments
curl http://localhost:8000/experiments/1/metrics
curl -X POST http://localhost:8000/experiments/big_data_checkout_test/analyze
docker compose down
```

Открыть в браузере:

- `http://localhost:8000/docs`
- `http://localhost:8501`

В dashboard выбрать `big_data_checkout_test` и проверить, что видны:

- synthetic users/events overview;
- список экспериментов;
- assignment по control/treatment;
- live metrics;
- saved results после analyze.
