INSERT INTO users (
    user_key,
    registered_at,
    country_code,
    device_type,
    acquisition_channel,
    attributes
)
VALUES
    ('user_001', '2026-04-01 08:00:00+00', 'RU', 'ios', 'organic', '{"plan": "free"}'),
    ('user_002', '2026-04-01 08:10:00+00', 'RU', 'android', 'ads', '{"plan": "free"}'),
    ('user_003', '2026-04-02 09:30:00+00', 'KZ', 'web', 'organic', '{"plan": "pro"}'),
    ('user_004', '2026-04-02 11:15:00+00', 'RU', 'ios', 'referral', '{"plan": "free"}'),
    ('user_005', '2026-04-03 12:45:00+00', 'BY', 'android', 'organic', '{"plan": "free"}'),
    ('user_006', '2026-04-03 14:10:00+00', 'RU', 'web', 'ads', '{"plan": "pro"}')
ON CONFLICT (user_key) DO NOTHING;

INSERT INTO experiments (
    experiment_key,
    name,
    description,
    hypothesis,
    status,
    start_at,
    end_at,
    owner_name,
    primary_metric_key
)
VALUES (
    'checkout_button_v1',
    'Checkout Button Copy Test',
    'Сравнение базовой и новой формулировки кнопки оплаты.',
    'Новый текст кнопки увеличит конверсию в покупку без падения выручки.',
    'running',
    '2026-04-10 00:00:00+00',
    NULL,
    'Ahmed',
    'purchase_conversion'
)
ON CONFLICT (experiment_key) DO NOTHING;

INSERT INTO experiment_variants (
    experiment_id,
    variant_key,
    name,
    description,
    is_control,
    allocation_percent
)
SELECT e.id, 'control', 'Control', 'Текущий текст кнопки.', TRUE, 50.00
FROM experiments e
WHERE e.experiment_key = 'checkout_button_v1'
ON CONFLICT (experiment_id, variant_key) DO NOTHING;

INSERT INTO experiment_variants (
    experiment_id,
    variant_key,
    name,
    description,
    is_control,
    allocation_percent
)
SELECT e.id, 'treatment', 'Treatment', 'Новый текст кнопки.', FALSE, 50.00
FROM experiments e
WHERE e.experiment_key = 'checkout_button_v1'
ON CONFLICT (experiment_id, variant_key) DO NOTHING;

INSERT INTO experiment_assignments (
    experiment_id,
    variant_id,
    user_id,
    assigned_at,
    assignment_source
)
SELECT
    e.id,
    v.id,
    u.id,
    '2026-04-10 08:00:00+00',
    'seed'
FROM experiments e
JOIN experiment_variants v
    ON v.experiment_id = e.id
JOIN users u
    ON u.user_key IN ('user_001', 'user_002', 'user_003')
WHERE e.experiment_key = 'checkout_button_v1'
  AND v.variant_key = 'control'
ON CONFLICT (experiment_id, user_id) DO NOTHING;

INSERT INTO experiment_assignments (
    experiment_id,
    variant_id,
    user_id,
    assigned_at,
    assignment_source
)
SELECT
    e.id,
    v.id,
    u.id,
    '2026-04-10 08:00:00+00',
    'seed'
FROM experiments e
JOIN experiment_variants v
    ON v.experiment_id = e.id
JOIN users u
    ON u.user_key IN ('user_004', 'user_005', 'user_006')
WHERE e.experiment_key = 'checkout_button_v1'
  AND v.variant_key = 'treatment'
ON CONFLICT (experiment_id, user_id) DO NOTHING;

INSERT INTO metrics_definitions (
    metric_key,
    metric_name,
    description,
    metric_type,
    source_event_name,
    aggregation_level,
    value_column,
    metadata
)
VALUES
    (
        'purchase_conversion',
        'Purchase Conversion',
        'Доля пользователей, совершивших событие purchase.',
        'conversion',
        'purchase',
        'user',
        'none',
        '{"window_days": 7}'
    ),
    (
        'arpu',
        'Average Revenue Per User',
        'Средняя выручка на пользователя по событию purchase.',
        'mean',
        'purchase',
        'user',
        'event_value',
        '{"currency": "USD"}'
    ),
    (
        'retention_proxy_day_1',
        'Day 1 Retention Proxy',
        'Доля пользователей, вернувшихся и совершивших app_open на следующий день.',
        'retention_proxy',
        'app_open',
        'user',
        'none',
        '{"window_days": 1}'
    )
ON CONFLICT (metric_key) DO NOTHING;

INSERT INTO events (
    user_id,
    event_name,
    event_timestamp,
    event_value,
    event_properties
)
SELECT
    u.id,
    seed_events.event_name,
    seed_events.event_timestamp::timestamptz,
    seed_events.event_value,
    seed_events.event_properties::jsonb
FROM (
    VALUES
        ('user_001', 'app_open', '2026-04-10 09:00:00+00', NULL, '{"session_number": 1}'),
        ('user_001', 'purchase', '2026-04-10 09:10:00+00', 20.00, '{"order_id": "A1001"}'),
        ('user_001', 'app_open', '2026-04-11 10:00:00+00', NULL, '{"session_number": 2}'),
        ('user_002', 'app_open', '2026-04-10 09:05:00+00', NULL, '{"session_number": 1}'),
        ('user_002', 'checkout_start', '2026-04-10 09:20:00+00', NULL, '{"step": 1}'),
        ('user_003', 'app_open', '2026-04-10 09:15:00+00', NULL, '{"session_number": 1}'),
        ('user_003', 'purchase', '2026-04-10 09:40:00+00', 35.00, '{"order_id": "A1002"}'),
        ('user_004', 'app_open', '2026-04-10 09:00:00+00', NULL, '{"session_number": 1}'),
        ('user_004', 'purchase', '2026-04-10 09:12:00+00', 25.00, '{"order_id": "B1001"}'),
        ('user_004', 'app_open', '2026-04-11 09:05:00+00', NULL, '{"session_number": 2}'),
        ('user_005', 'app_open', '2026-04-10 09:03:00+00', NULL, '{"session_number": 1}'),
        ('user_006', 'app_open', '2026-04-10 09:08:00+00', NULL, '{"session_number": 1}'),
        ('user_006', 'purchase', '2026-04-10 09:25:00+00', 40.00, '{"order_id": "B1002"}'),
        ('user_006', 'app_open', '2026-04-11 09:20:00+00', NULL, '{"session_number": 2}')
) AS seed_events(user_key, event_name, event_timestamp, event_value, event_properties)
JOIN users u
    ON u.user_key = seed_events.user_key
LEFT JOIN events existing_events
    ON existing_events.user_id = u.id
   AND existing_events.event_name = seed_events.event_name
   AND existing_events.event_timestamp = seed_events.event_timestamp::timestamptz
WHERE existing_events.id IS NULL;

INSERT INTO experiment_results (
    experiment_id,
    metric_definition_id,
    baseline_variant_id,
    compared_variant_id,
    sample_size_baseline,
    sample_size_compared,
    baseline_value,
    compared_value,
    absolute_lift,
    relative_lift,
    p_value,
    ci_lower,
    ci_upper,
    is_significant,
    test_method,
    calculated_at,
    result_payload
)
SELECT
    e.id,
    m.id,
    control_variant.id,
    treatment_variant.id,
    3,
    3,
    0.666667,
    0.666667,
    0.000000,
    0.000000,
    1.000000,
    -0.450000,
    0.450000,
    FALSE,
    'two_proportion_ztest',
    '2026-04-12 00:00:00+00',
    '{"note": "Seed result for demo dashboard and query testing."}'
FROM experiments e
JOIN metrics_definitions m
    ON m.metric_key = 'purchase_conversion'
JOIN experiment_variants control_variant
    ON control_variant.experiment_id = e.id
   AND control_variant.variant_key = 'control'
JOIN experiment_variants treatment_variant
    ON treatment_variant.experiment_id = e.id
   AND treatment_variant.variant_key = 'treatment'
WHERE e.experiment_key = 'checkout_button_v1'
ON CONFLICT DO NOTHING;
