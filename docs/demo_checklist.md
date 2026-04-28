# Demo Checklist

## Быстрый сценарий

1. Склонировать репозиторий.
2. Запустить сервисы:

```bash
docker compose up --build -d
```

3. Подготовить воспроизводимые demo-данные:

```bash
docker compose exec api python -m app.db.prepare_demo
```

4. Открыть dashboard:

```text
http://localhost:8501
```

5. В sidebar выбрать эксперимент:

```text
big_data_checkout_test
```

6. Открыть Swagger:

```text
http://localhost:8000/docs
```

## Что должно быть видно

- В секции **Обзор** есть пользователи, события, типы событий и выручка.
- В секции **Эксперименты** есть `big_data_checkout_test`.
- В секции **Выбранный эксперимент** есть гипотеза checkout-теста.
- В секции **Разбиение пользователей** видны контрольная и тестовая группы.
- В секции **Метрики** видны conversion rate, ARPU, средний чек и purchase rate.
- В секции **Статистические результаты** есть uplift, p-value и CI.
- В секции **Проверка демо** основные проверки показывают успех.

## Что проговорить на демо

- Данные генерируются детерминированно: `users=10000`, `days=180`, `seed=42`.
- `prepare_demo.py` делает демо воспроизводимым одной командой.
- Dashboard не ходит напрямую в PostgreSQL, а получает данные через FastAPI.
- Assignment хранится отдельно от событий, поэтому анализ воспроизводим.
- Метрики считаются из событий после назначения пользователей в группы.
- Статистический вывод намеренно простой и объяснимый для junior-проекта.

## Troubleshooting

Если API недоступен:

```bash
docker compose ps
docker compose logs api
```

Если PowerShell перехватывает `curl`, используйте:

```powershell
curl.exe http://localhost:8000/health
```

или:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Если данные или эксперимент отсутствуют:

```bash
docker compose exec api python -m app.db.prepare_demo
```

Если нужна полностью чистая база:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec api python -m app.db.prepare_demo
```
