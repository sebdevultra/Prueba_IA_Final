-- ==============================================================================
-- SismoWatch — Inicialización de Base de Datos PostgreSQL 16
-- Multi-database, Esquemas Medallion y Roles de Mínimo Privilegio (RBAC)
-- ==============================================================================

-- 1. Crear base de datos para los metadatos de Apache Airflow
SELECT 'CREATE DATABASE airflow_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow_db')\gexec

-- Conectarse a la base de datos de negocio sismowatch_db
\connect sismowatch_db;

-- 2. Habilitar extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 3. Crear Esquemas del Patrón Medallion
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;

-- 4. Crear Roles Segregados (Mínimo Privilegio)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'role_ingest') THEN
        CREATE ROLE role_ingest NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'role_transform') THEN
        CREATE ROLE role_transform NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'role_readonly') THEN
        CREATE ROLE role_readonly NOLOGIN;
    END IF;
END $$;

-- 5. Crear Usuarios con credenciales
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ingest_user') THEN
        CREATE USER ingest_user WITH PASSWORD 'ingest_secure_pass';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'transform_user') THEN
        CREATE USER transform_user WITH PASSWORD 'transform_secure_pass';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE USER readonly_user WITH PASSWORD 'readonly_secure_pass';
    END IF;
END $$;

-- ==============================================================================
-- 6. TABLAS DE LA CAPA BRONZE (raw)
-- Ingesta inmutable de feeds GeoJSON tal como llegan de USGS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS raw.earthquake_events_raw (
    event_id VARCHAR(64) PRIMARY KEY,
    raw_payload JSONB NOT NULL,
    source_feed VARCHAR(32) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==============================================================================
-- 7. TABLAS DE LA CAPA SILVER (staging)
-- Limpieza, tipado y retención de inválidos (sin tabla de cuarentena separada)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS staging.earthquake_events (
    event_id VARCHAR(64) PRIMARY KEY,
    mag DOUBLE PRECISION,
    place TEXT,
    time_utc TIMESTAMPTZ,
    updated_utc TIMESTAMPTZ,
    tsunami INTEGER,
    sig INTEGER,
    status VARCHAR(32),
    mag_type VARCHAR(32),
    event_type VARCHAR(32),
    url TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    depth_km DOUBLE PRECISION,
    is_valid BOOLEAN NOT NULL,
    validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_is_valid ON staging.earthquake_events(is_valid);
CREATE INDEX IF NOT EXISTS idx_staging_time_utc ON staging.earthquake_events(time_utc DESC);

-- ==============================================================================
-- 8. TABLAS DE LA CAPA GOLD (curated)
-- Datos limpios certificados, métricas de calidad, anomalías y reportes IA
-- ==============================================================================
CREATE TABLE IF NOT EXISTS curated.earthquake_events (
    event_id VARCHAR(64) PRIMARY KEY,
    mag DOUBLE PRECISION NOT NULL,
    place TEXT,
    time_utc TIMESTAMPTZ NOT NULL,
    updated_utc TIMESTAMPTZ NOT NULL,
    tsunami INTEGER DEFAULT 0,
    sig INTEGER,
    status VARCHAR(32),
    mag_type VARCHAR(32),
    event_type VARCHAR(32),
    url TEXT,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    depth_km DOUBLE PRECISION NOT NULL,
    curated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curated_time_utc ON curated.earthquake_events(time_utc DESC);
CREATE INDEX IF NOT EXISTS idx_curated_mag ON curated.earthquake_events(mag);
CREATE INDEX IF NOT EXISTS idx_curated_lat_lon ON curated.earthquake_events(latitude, longitude);

-- Métricas de corridas de calidad de datos
CREATE TABLE IF NOT EXISTS curated.data_quality_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dag_run_id VARCHAR(128),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_records INT NOT NULL,
    valid_records INT NOT NULL,
    invalid_records INT NOT NULL,
    freshness_ok BOOLEAN NOT NULL,
    volume_ok BOOLEAN NOT NULL,
    quality_score NUMERIC(5,2) NOT NULL,
    rule_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_quality_evaluated_at ON curated.data_quality_runs(evaluated_at DESC);

-- Detección analítica de anomalías y enjambres sísmicos
CREATE TABLE IF NOT EXISTS curated.seismic_anomalies (
    anomaly_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anomaly_type VARCHAR(64) NOT NULL,
    region TEXT,
    event_count INT NOT NULL,
    max_mag DOUBLE PRECISION NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    explanation TEXT NOT NULL,
    related_event_ids JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON curated.seismic_anomalies(detected_at DESC);

-- Reportes diarios ejecutivos generados por IA
CREATE TABLE IF NOT EXISTS curated.ai_daily_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_date DATE UNIQUE NOT NULL,
    headline VARCHAR(255) NOT NULL,
    executive_summary TEXT NOT NULL,
    most_active_zones JSONB NOT NULL DEFAULT '[]'::jsonb,
    notable_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    computed_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_report_date ON curated.ai_daily_reports(report_date DESC);

-- Logs de auditoría, latencia, tokens y costo estimado de IA
CREATE TABLE IF NOT EXISTS curated.ai_execution_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prompt_version VARCHAR(32) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0.0,
    validation_passed BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_logs_executed_at ON curated.ai_execution_logs(executed_at DESC);

-- ==============================================================================
-- 9. ASIGNACIÓN ESTRICTA DE PRIVILEGIOS POR ROL
-- ==============================================================================

-- A) role_ingest: Acceso exclusivo a schema raw
GRANT USAGE ON SCHEMA raw TO role_ingest;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA raw TO role_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT, UPDATE ON TABLES TO role_ingest;

-- B) role_transform: Lectura en raw, completo en staging, escritura/lectura en curated
GRANT USAGE ON SCHEMA raw, staging, curated TO role_transform;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO role_transform;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO role_transform;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA curated TO role_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO role_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT ALL PRIVILEGES ON TABLES TO role_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT ALL PRIVILEGES ON TABLES TO role_transform;

-- C) role_readonly: Lectura sobre curated y auditoría de inválidos en staging
GRANT USAGE ON SCHEMA curated, staging TO role_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA curated TO role_readonly;
GRANT SELECT ON staging.earthquake_events TO role_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT SELECT ON TABLES TO role_readonly;

-- 10. Vincular usuarios a sus respectivos roles
GRANT role_ingest TO ingest_user;
GRANT role_transform TO transform_user;
GRANT role_readonly TO readonly_user;
