# Metrics Engine

## Что считает первая версия

Metrics engine считает четыре продуктовые метрики по пользователям, назначенным в эксперимент:

- `conversion_rate`
- `average_revenue_per_user`
- `average_order_value`
- `purchase_rate`

Данные берутся из:

- `experiment_assignments` — кто попал в какую группу;
- `experiment_variants` — где control и treatment;
- `events` — покупки и revenue.

## Формулы

### Conversion Rate

Доля пользователей, которые совершили хотя бы одну покупку.

```text
conversion_rate = users_with_purchase / assigned_users
```

Пример: если в treatment 100 пользователей и 12 из них купили, conversion rate = `0.12`.

### Average Revenue Per User

Средняя выручка на назначенного пользователя.

```text
ARPU = total_purchase_revenue / assigned_users
```

Пользователи без покупок входят в знаменатель с revenue = 0. Это важно для честного сравнения групп.

### Average Order Value

Средний чек по purchase-событиям.

```text
AOV = total_purchase_revenue / purchase_events
```

Здесь знаменатель — не пользователи, а заказы. Поэтому sample size для AOV равен количеству покупок.

### Purchase Rate

Среднее количество покупок на назначенного пользователя.

```text
purchase_rate = purchase_events / assigned_users
```

Эта метрика отличается от conversion rate: пользователь с тремя покупками влияет на purchase rate сильнее, но в conversion rate он всё равно считается как `1`.

## Uplift

Для каждой метрики считается абсолютный и относительный uplift:

```text
absolute_lift = treatment_value - control_value
relative_lift = (treatment_value - control_value) / control_value
```

Если control value равен нулю, relative lift не считается, чтобы не делить на ноль.

## Статистические тесты

### Бинарная метрика

Для `conversion_rate` используется two-proportion z-test.

Почему:

- метрика бинарная на уровне пользователя;
- сравниваются две независимые доли;
- метод простой и часто используется в базовой продуктовой аналитике.

Также считается нормальная 95% confidence interval для разницы долей:

```text
(treatment_rate - control_rate) +/- 1.96 * SE
```

### Числовые метрики

Для `average_revenue_per_user`, `average_order_value` и `purchase_rate` используется Welch's t-test.

Почему:

- группы могут иметь разную дисперсию;
- размеры групп могут отличаться;
- Welch's t-test практичнее обычного t-test с равными дисперсиями.

Для числовых метрик считается 95% confidence interval для разницы средних.

## Как интерпретировать результат

- `baseline_value` — значение в control.
- `compared_value` — значение в treatment.
- `absolute_lift` — разница treatment минус control.
- `relative_lift` — относительное изменение к control.
- `p_value` — вероятность увидеть такую или более сильную разницу при нулевой гипотезе.
- `is_significant` — `true`, если `p_value < 0.05`.
- `ci_lower`, `ci_upper` — доверительный интервал для разницы treatment минус control.

## Ограничения первой версии

- Нет проверки SRM и качества рандомизации.
- Нет CUPED, стратификации и variance reduction.
- Нет поправки на множественные проверки.
- Для revenue-метрик распределения могут быть скошенными, поэтому t-test нужно интерпретировать аккуратно.
- AOV считается по заказам, а не по пользователям, поэтому его нельзя читать как user-level эффект.
- Нет event window настройки на уровне API: сейчас учитываются события после `assigned_at`.
- Статистическая значимость не равна бизнес-значимости.

## Почему это подходит для portfolio-проекта

Эта версия показывает практичный минимум для A/B analytics:

- есть понятные формулы;
- есть агрегация по control/treatment;
- есть uplift;
- есть базовые статистические тесты;
- результаты сохраняются в PostgreSQL;
- код остаётся читаемым и объяснимым.
