# Data Dictionary

## Зачем такая модель

Схема построена вокруг простой идеи: события пользователя хранятся отдельно от сущностей эксперимента, а связь между ними происходит через таблицу назначений в эксперимент.  
Это позволяет независимо:

- хранить сырые пользовательские события;
- задавать состав эксперимента и его варианты;
- знать, в какую группу попал пользователь;
- считать метрики по событиям и сравнивать группы;
- сохранять результат статистического анализа отдельно от сырого event log.

Такой дизайн достаточно простой для pet-project, но уже поддерживает типичные продуктовые и A/B test запросы.

## ER-логика простыми словами

- Один пользователь (`users`) может иметь много событий (`events`).
- Один эксперимент (`experiments`) имеет несколько вариантов (`experiment_variants`).
- Обычно среди вариантов есть один `control` и один или несколько `treatment`.
- Пользователь попадает в эксперимент через таблицу `experiment_assignments`.
- Метрика описывается в `metrics_definitions`: из какого события она считается и как агрегируется.
- Результаты анализа сохраняются в `experiment_results`, чтобы не пересчитывать их каждый раз в dashboard.

## Таблицы

### `users`

Хранит пользователя как аналитическую сущность.

Основные поля:

- `id` — внутренний surrogate key.
- `user_key` — внешний бизнес-идентификатор пользователя.
- `registered_at` — время регистрации.
- `country_code`, `device_type`, `acquisition_channel` — полезные аналитические признаки.
- `attributes` — JSONB для дополнительных гибких атрибутов.
- `created_at`, `updated_at` — технические временные поля.

### `events`

Хранит event log.

Основные поля:

- `id` — идентификатор события.
- `user_id` — ссылка на пользователя.
- `event_name` — название события: `app_open`, `purchase`, `checkout_start`.
- `event_timestamp` — время события.
- `event_value` — числовое значение, например выручка.
- `event_properties` — JSONB с дополнительными параметрами события.
- `created_at`, `updated_at` — технические поля.

### `experiments`

Хранит описание эксперимента.

Основные поля:

- `experiment_key` — уникальный ключ эксперимента.
- `name`, `description`, `hypothesis` — описание для аналитика и dashboard.
- `status` — `draft`, `running`, `completed`.
- `start_at`, `end_at` — границы эксперимента.
- `owner_name` — кто отвечает за эксперимент.
- `primary_metric_key` — ключ основной метрики.
- `created_at`, `updated_at` — технические поля.

### `experiment_variants`

Хранит варианты внутри эксперимента.

Основные поля:

- `experiment_id` — ссылка на эксперимент.
- `variant_key` — машинный ключ варианта, например `control`, `treatment`.
- `name` — человекочитаемое название.
- `is_control` — признак контрольной группы.
- `allocation_percent` — плановый процент трафика.
- `created_at`, `updated_at` — технические поля.

Правила:

- у варианта уникальный `variant_key` внутри эксперимента;
- у эксперимента может быть только один `control` на уровне БД;
- минимум два варианта для эксперимента лучше проверять в сервисном слое или при публикации эксперимента.

### `experiment_assignments`

Хранит факт назначения пользователя в эксперимент и вариант.

Основные поля:

- `experiment_id` — ссылка на эксперимент.
- `variant_id` — ссылка на вариант.
- `user_id` — ссылка на пользователя.
- `assigned_at` — когда пользователь был назначен.
- `assignment_source` — способ назначения, например `hash` или `seed`.

Ключевая идея:

- один пользователь может участвовать в эксперименте только один раз;
- составной foreign key гарантирует, что вариант действительно принадлежит этому эксперименту.

### `metrics_definitions`

Хранит определения метрик.

Основные поля:

- `metric_key` — уникальный ключ метрики.
- `metric_name` — отображаемое название.
- `metric_type` — тип: `conversion`, `sum`, `mean`, `retention_proxy`, `count`.
- `source_event_name` — событие-источник.
- `aggregation_level` — уровень агрегации: по пользователю или по событию.
- `value_column` — какую числовую колонку использовать.
- `metadata` — JSONB для окна расчёта и дополнительных параметров.

### `experiment_results`

Хранит уже рассчитанные результаты сравнения вариантов.

Основные поля:

- `experiment_id` — эксперимент.
- `metric_definition_id` — метрика.
- `baseline_variant_id` — базовый вариант, обычно control.
- `compared_variant_id` — сравниваемый treatment.
- `sample_size_baseline`, `sample_size_compared` — размеры выборок.
- `baseline_value`, `compared_value` — значения метрики.
- `absolute_lift`, `relative_lift` — эффект.
- `p_value`, `ci_lower`, `ci_upper`, `is_significant` — статистический вывод.
- `test_method` — какой тест применялся.
- `result_payload` — JSONB для дополнительной информации.

## Связи

```text
users 1 --- * events
users 1 --- * experiment_assignments
experiments 1 --- * experiment_variants
experiments 1 --- * experiment_assignments
experiment_variants 1 --- * experiment_assignments
metrics_definitions 1 --- * experiment_results
experiments 1 --- * experiment_results
```

## Индексы и зачем они нужны

- `users(registered_at)` — ускоряет отбор когорт по времени регистрации.
- `experiments(status)` и `experiments(status, start_at)` — помогают быстро находить активные и завершённые эксперименты.
- `experiment_variants(experiment_id)` — нужен при загрузке вариантов эксперимента.
- `experiment_assignments(user_id)` — нужен для поиска назначений пользователя.
- `experiment_assignments(experiment_id, variant_id)` — нужен для подсчёта размеров групп.
- `events(user_id, event_timestamp)` — базовый индекс для user-level метрик и retention.
- `events(event_name, event_timestamp)` — ускоряет фильтрацию нужного типа событий во временном окне.
- `events(event_timestamp)` — полезен для range scan по датам.
- `events GIN(event_properties)` — позволяет фильтровать события по JSON-полям.
- `experiment_results(experiment_id, metric_definition_id, calculated_at desc)` — ускоряет выбор последнего расчёта по метрике.

## Ограничения целостности

- `user_key` и `experiment_key` уникальны.
- `status` ограничен значениями `draft`, `running`, `completed`.
- `allocation_percent` ограничен диапазоном от 0 до 100.
- у эксперимента только один control-вариант через partial unique index.
- пользователь не может быть назначен в один эксперимент дважды.
- составной foreign key гарантирует, что `variant_id` принадлежит тому же `experiment_id`.
- `p_value` ограничен диапазоном от 0 до 1.
- `updated_at` обновляется триггером автоматически.

## Небольшой seed dataset

В seed включены:

- 6 пользователей;
- 1 эксперимент со статусом `running`;
- 2 варианта: `control` и `treatment`;
- назначения пользователей в группы;
- события `app_open`, `checkout_start`, `purchase`;
- 3 определения метрик;
- 1 сохранённый результат по конверсии.

Этого достаточно, чтобы:

- проверить joins;
- написать первые SQL-запросы;
- показать данные в dashboard;
- отладить будущий слой аналитики.

## Почему модель выбрана именно такой

- Она отделяет сырые данные (`events`) от управления экспериментом (`experiments`, `experiment_variants`, `experiment_assignments`).
- Она не привязывает события жёстко к эксперименту, потому что в реальной жизни один и тот же event log может использоваться в разных аналитических задачах.
- Она поддерживает как простые продуктовые метрики, так и последующее сохранение статистических результатов.
- В ней мало таблиц и мало магии, поэтому её легко объяснить на собеседовании.
