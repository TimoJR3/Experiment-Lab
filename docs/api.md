# API: эндпоинты и примеры запросов

Swagger доступен после запуска: `http://localhost:8000/docs`.

![FastAPI Swagger](images/swagger_api.png)


Ниже показаны основные endpoints из `app/api/routes.py`. Примеры ответов
сокращены, но сохраняют реальные поля API.

Для dashboard также есть вспомогательные summary endpoints:

- `GET /users/summary` — компактная сводка по synthetic users;
- `GET /events/summary` — компактная сводка по synthetic events и revenue.

### GET /health

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok"
}
```

Зачем аналитику: быстро проверить, что backend доступен перед работой с
dashboard или API-запросами.

### GET /experiments

```bash
curl http://localhost:8000/experiments
```

```json
[
  {
    "id": 1,
    "experiment_key": "big_data_checkout_test",
    "name": "Big Data Checkout Test",
    "status": "running",
    "start_at": "2026-04-10T09:00:00Z",
    "end_at": null,
    "variants_count": 2,
    "assignments_count": 250
  }
]
```

Зачем аналитику: выбрать эксперимент для анализа и сразу увидеть статус,
количество вариантов и число назначенных пользователей.

### GET /experiments/{id}

```bash
curl http://localhost:8000/experiments/1
```

```json
{
  "id": 1,
  "experiment_key": "big_data_checkout_test",
  "name": "Big Data Checkout Test",
  "description": "Synthetic checkout experiment for product analytics demo.",
  "hypothesis": "New checkout experience improves purchase conversion.",
  "status": "running",
  "start_at": "2026-04-10T09:00:00Z",
  "end_at": null,
  "owner_name": "Product Analytics Demo",
  "primary_metric_key": "conversion_rate",
  "created_at": "2026-04-10T09:00:00Z",
  "updated_at": "2026-04-10T09:00:00Z"
}
```

Зачем аналитику: проверить гипотезу, primary metric, владельца и контекст
эксперимента перед чтением результатов.

### GET /experiments/{id}/assignments

```bash
curl http://localhost:8000/experiments/1/assignments
```

```json
{
  "experiment_id": 1,
  "total_assigned": 250,
  "groups": [
    {
      "variant_id": 1,
      "variant_key": "control",
      "is_control": true,
      "users_count": 126
    },
    {
      "variant_id": 2,
      "variant_key": "treatment",
      "is_control": false,
      "users_count": 124
    }
  ]
}
```

Зачем аналитику: оценить размеры групп и заметить грубый перекос assignment до
интерпретации метрик.

### GET /experiments/{id}/metrics

```bash
curl http://localhost:8000/experiments/1/metrics
```

```json
{
  "experiment_id": 1,
  "results": [
    {
      "metric_key": "conversion_rate",
      "metric_name": "Conversion Rate",
      "baseline_variant_key": "control",
      "compared_variant_key": "treatment",
      "sample_size_baseline": 126,
      "sample_size_compared": 124,
      "baseline_value": 0.1746,
      "compared_value": 0.2097,
      "absolute_lift": 0.0351,
      "relative_lift": 0.201,
      "p_value": 0.48,
      "ci_lower": -0.061,
      "ci_upper": 0.131,
      "is_significant": false,
      "test_method": "two_proportion_ztest"
    }
  ]
}
```

Зачем аналитику: получить live-расчет метрик по текущим assignments и events без
сохранения нового результата в `experiment_results`.

### GET /experiments/{id}/results

```bash
curl http://localhost:8000/experiments/1/results
```

```json
{
  "experiment_id": 1,
  "results": [
    {
      "metric_key": "average_revenue_per_user",
      "metric_name": "Average Revenue Per User",
      "baseline_variant_key": "control",
      "compared_variant_key": "treatment",
      "sample_size_baseline": 126,
      "sample_size_compared": 124,
      "baseline_value": 18.42,
      "compared_value": 20.15,
      "absolute_lift": 1.73,
      "relative_lift": 0.0939,
      "p_value": 0.37,
      "ci_lower": -2.04,
      "ci_upper": 5.50,
      "is_significant": false,
      "test_method": "welch_ttest"
    }
  ]
}
```

Зачем аналитику: посмотреть сохраненный результат анализа, который dashboard
может показывать без повторной записи в таблицу результатов.

### POST /experiments

```bash
curl -X POST http://localhost:8000/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_key": "checkout_copy_v2",
    "name": "Checkout Copy Test",
    "description": "Demo draft experiment for checkout copy.",
    "hypothesis": "Clearer checkout copy improves purchase conversion.",
    "owner_name": "Product Analytics Demo",
    "primary_metric_key": "conversion_rate",
    "variants": [
      {
        "variant_key": "control",
        "name": "Current copy",
        "description": "Existing checkout copy.",
        "is_control": true,
        "allocation_percent": "50"
      },
      {
        "variant_key": "treatment",
        "name": "New copy",
        "description": "Updated checkout copy.",
        "is_control": false,
        "allocation_percent": "50"
      }
    ]
  }'
```

```json
{
  "experiment_id": 2,
  "experiment_key": "checkout_copy_v2",
  "name": "Checkout Copy Test",
  "status": "draft",
  "created_at": "2026-07-04T10:00:00Z"
}
```

Зачем аналитику: создать карточку эксперимента, варианты и primary metric до
назначения пользователей.

### POST /experiments/{experiment_key}/start

```bash
curl -X POST http://localhost:8000/experiments/checkout_copy_v2/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [1, 2, 3, 4, 5],
    "assignment_source": "hash"
  }'
```

```json
{
  "experiment_id": 2,
  "experiment_key": "checkout_copy_v2",
  "status": "running",
  "assigned_users": 5,
  "assignments": [
    {
      "user_id": 1,
      "variant_id": 3,
      "variant_key": "control",
      "assignment_bucket": "12.345678"
    },
    {
      "user_id": 2,
      "variant_id": 4,
      "variant_key": "treatment",
      "assignment_bucket": "76.543210"
    }
  ]
}
```

Зачем аналитику: зафиксировать попадание пользователей в control/treatment,
чтобы дальше считать метрики по стабильному assignment.

### POST /experiments/{experiment_key}/analyze

```bash
curl -X POST http://localhost:8000/experiments/big_data_checkout_test/analyze
```

```json
{
  "experiment_key": "big_data_checkout_test",
  "results_saved": 4,
  "results": [
    {
      "metric_key": "conversion_rate",
      "metric_name": "Conversion Rate",
      "baseline_variant_key": "control",
      "compared_variant_key": "treatment",
      "sample_size_baseline": 126,
      "sample_size_compared": 124,
      "baseline_value": 0.1746,
      "compared_value": 0.2097,
      "absolute_lift": 0.0351,
      "relative_lift": 0.201,
      "p_value": 0.48,
      "ci_lower": -0.061,
      "ci_upper": 0.131,
      "is_significant": false,
      "test_method": "two_proportion_ztest"
    }
  ]
}
```

Зачем аналитику: пересчитать все поддержанные метрики, применить статистические
тесты и сохранить результат в PostgreSQL для последующей демонстрации.

PowerShell иногда использует alias `curl`. Если команда ведет себя не так,
используйте:

```powershell
curl.exe http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health
```


### POST /design/sample-size

Сколько пользователей нужно на группу, чтобы заметить относительный эффект
`mde_relative` для конверсии `baseline_rate`.

```bash
curl -X POST http://localhost:8000/design/sample-size \
  -H "Content-Type: application/json" \
  -d '{"baseline_rate": 0.134, "mde_relative": 0.05, "alpha": 0.05, "power": 0.8}'
```

```json
{"baseline_rate": 0.134, "expected_rate": 0.1407, "mde_absolute": 0.0067,
 "mde_relative": 0.05, "alpha": 0.05, "power": 0.8,
 "users_control": 41430, "users_treatment": 41430, "users_total": 82860}
```

### POST /design/srm-check

Проверка sample ratio mismatch: совпадает ли фактическое разбиение с планом.

```bash
curl -X POST http://localhost:8000/design/srm-check \
  -H "Content-Type: application/json" \
  -d '{"observed": {"control": 10000, "treatment": 10600}}'
```

```json
{"chi_square": 17.48, "p_value": 0.000029, "threshold": 0.001, "has_mismatch": true}
```

### GET /users/summary

Сводка по пользователям для проверки данных перед анализом.

```bash
curl http://localhost:8000/users/summary
```

Поля ответа: `users_count`, `countries_count`, `device_types_count`,
`first_registered_at`, `last_registered_at`.

### GET /events/summary

Сводка по событиям и выручке.

```bash
curl http://localhost:8000/events/summary
```

Поля ответа: `events_count`, `first_event_at`, `last_event_at`, `revenue_total`,
`by_event_name` (список `event_name` + `events_count`).
