CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_key TEXT NOT NULL UNIQUE,
    registered_at TIMESTAMPTZ,
    country_code CHAR(2),
    device_type TEXT,
    acquisition_channel TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (user_key <> ''),
    CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$')
);

CREATE TABLE IF NOT EXISTS experiments (
    id BIGSERIAL PRIMARY KEY,
    experiment_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    hypothesis TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    owner_name TEXT,
    primary_metric_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (experiment_key <> ''),
    CHECK (status IN ('draft', 'running', 'completed')),
    CHECK (end_at IS NULL OR start_at IS NULL OR end_at >= start_at)
);

CREATE TABLE IF NOT EXISTS experiment_variants (
    id BIGSERIAL PRIMARY KEY,
    experiment_id BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_control BOOLEAN NOT NULL DEFAULT FALSE,
    allocation_percent NUMERIC(5,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (experiment_id, variant_key),
    UNIQUE (experiment_id, id),
    CHECK (variant_key <> ''),
    CHECK (allocation_percent >= 0 AND allocation_percent <= 100)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_experiment_variants_one_control
    ON experiment_variants (experiment_id)
    WHERE is_control;

CREATE TABLE IF NOT EXISTS experiment_assignments (
    id BIGSERIAL PRIMARY KEY,
    experiment_id BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    variant_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assignment_source TEXT NOT NULL DEFAULT 'hash',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (experiment_id, user_id),
    FOREIGN KEY (experiment_id, variant_id)
        REFERENCES experiment_variants (experiment_id, id)
        ON DELETE CASCADE,
    CHECK (assignment_source <> '')
);

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    event_uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    event_value NUMERIC(14,2),
    event_properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (event_name <> '')
);

CREATE TABLE IF NOT EXISTS metrics_definitions (
    id BIGSERIAL PRIMARY KEY,
    metric_key TEXT NOT NULL UNIQUE,
    metric_name TEXT NOT NULL,
    description TEXT,
    metric_type TEXT NOT NULL,
    source_event_name TEXT NOT NULL,
    aggregation_level TEXT NOT NULL DEFAULT 'user',
    value_column TEXT NOT NULL DEFAULT 'event_value',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (metric_key <> ''),
    CHECK (source_event_name <> ''),
    CHECK (metric_type IN ('conversion', 'sum', 'mean', 'retention_proxy', 'count')),
    CHECK (aggregation_level IN ('user', 'event')),
    CHECK (value_column IN ('event_value', 'none'))
);

CREATE TABLE IF NOT EXISTS experiment_results (
    id BIGSERIAL PRIMARY KEY,
    experiment_id BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    metric_definition_id BIGINT NOT NULL REFERENCES metrics_definitions(id) ON DELETE RESTRICT,
    baseline_variant_id BIGINT NOT NULL REFERENCES experiment_variants(id) ON DELETE RESTRICT,
    compared_variant_id BIGINT NOT NULL REFERENCES experiment_variants(id) ON DELETE RESTRICT,
    sample_size_baseline INTEGER NOT NULL,
    sample_size_compared INTEGER NOT NULL,
    baseline_value NUMERIC(14,6) NOT NULL,
    compared_value NUMERIC(14,6) NOT NULL,
    absolute_lift NUMERIC(14,6),
    relative_lift NUMERIC(14,6),
    p_value NUMERIC(8,6),
    ci_lower NUMERIC(14,6),
    ci_upper NUMERIC(14,6),
    is_significant BOOLEAN,
    test_method TEXT,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    result_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (
        experiment_id,
        metric_definition_id,
        baseline_variant_id,
        compared_variant_id,
        calculated_at
    ),
    CHECK (sample_size_baseline >= 0),
    CHECK (sample_size_compared >= 0),
    CHECK (p_value IS NULL OR (p_value >= 0 AND p_value <= 1)),
    CHECK (baseline_variant_id <> compared_variant_id)
);

CREATE INDEX IF NOT EXISTS ix_users_registered_at
    ON users (registered_at);

CREATE INDEX IF NOT EXISTS ix_experiments_status
    ON experiments (status);

CREATE INDEX IF NOT EXISTS ix_experiments_status_start_at
    ON experiments (status, start_at);

CREATE INDEX IF NOT EXISTS ix_experiment_variants_experiment_id
    ON experiment_variants (experiment_id);

CREATE INDEX IF NOT EXISTS ix_experiment_assignments_user_id
    ON experiment_assignments (user_id);

CREATE INDEX IF NOT EXISTS ix_experiment_assignments_experiment_variant
    ON experiment_assignments (experiment_id, variant_id);

CREATE INDEX IF NOT EXISTS ix_events_user_timestamp
    ON events (user_id, event_timestamp);

CREATE INDEX IF NOT EXISTS ix_events_name_timestamp
    ON events (event_name, event_timestamp);

CREATE INDEX IF NOT EXISTS ix_events_timestamp
    ON events (event_timestamp);

CREATE INDEX IF NOT EXISTS ix_events_properties_gin
    ON events USING GIN (event_properties);

CREATE INDEX IF NOT EXISTS ix_results_experiment_metric
    ON experiment_results (experiment_id, metric_definition_id, calculated_at DESC);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_experiments_updated_at ON experiments;
CREATE TRIGGER trg_experiments_updated_at
BEFORE UPDATE ON experiments
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_experiment_variants_updated_at ON experiment_variants;
CREATE TRIGGER trg_experiment_variants_updated_at
BEFORE UPDATE ON experiment_variants
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_experiment_assignments_updated_at ON experiment_assignments;
CREATE TRIGGER trg_experiment_assignments_updated_at
BEFORE UPDATE ON experiment_assignments
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_events_updated_at ON events;
CREATE TRIGGER trg_events_updated_at
BEFORE UPDATE ON events
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_metrics_definitions_updated_at ON metrics_definitions;
CREATE TRIGGER trg_metrics_definitions_updated_at
BEFORE UPDATE ON metrics_definitions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_experiment_results_updated_at ON experiment_results;
CREATE TRIGGER trg_experiment_results_updated_at
BEFORE UPDATE ON experiment_results
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
