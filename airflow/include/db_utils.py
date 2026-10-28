"""
Utilidades de Base de Datos para el pipeline SismoWatch.
Proporciona conexiones segregadas por rol RBAC y operaciones idempotentes de UPSERT
en las tres capas del patrón Medallion (raw, staging, curated).
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def get_db_url_for_role(role: str = "transform") -> str:
    """
    Obtiene la URI de conexión de SQLAlchemy adecuada según el rol de base de datos.
    Soporta resolución dentro de la red Docker ('postgres:5432') o desde el host ('localhost:5435').
    """
    env_var_map = {
        "ingest": "DB_INGEST_CONN_URI",
        "transform": "DB_TRANSFORM_CONN_URI",
        "readonly": "DB_READONLY_CONN_URI",
    }
    target_var = env_var_map.get(role, "DB_TRANSFORM_CONN_URI")
    conn_uri = os.getenv(target_var)

    if not conn_uri:
        # Valores por defecto de desarrollo
        creds = {
            "ingest": ("ingest_user", "ingest_secure_pass"),
            "transform": ("transform_user", "transform_secure_pass"),
            "readonly": ("readonly_user", "readonly_secure_pass"),
        }
        user, pwd = creds.get(role, ("transform_user", "transform_secure_pass"))
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "sismowatch_db")
        conn_uri = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

    # Si estamos corriendo fuera de Docker (en el host) y el host es 'postgres', permitir fallback a localhost
    if "postgres:5432" in conn_uri and not os.path.exists("/.dockerenv"):
        # Verificar si 'postgres' es resoluble
        try:
            import socket
            socket.gethostbyname("postgres")
        except socket.gaierror:
            # Reemplazar con localhost:5435 para desarrollo en host
            conn_uri = conn_uri.replace("postgres:5432", "localhost:5435")

    return conn_uri


def get_db_engine(role: str = "transform") -> Engine:
    """Crea y retorna un Engine de SQLAlchemy para el rol especificado."""
    url = get_db_url_for_role(role)
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def upsert_raw_events(engine: Engine, features: List[Dict[str, Any]], source_feed: str = "realtime_hour") -> int:
    """
    Inserta o actualiza eventos GeoJSON en la capa Bronze (raw.earthquake_events_raw).
    Garantiza idempotencia absoluta mediante ON CONFLICT (event_id).
    """
    if not features:
        return 0

    stmt = text("""
        INSERT INTO raw.earthquake_events_raw (event_id, raw_payload, source_feed, ingested_at)
        VALUES (:event_id, CAST(:raw_payload AS jsonb), :source_feed, NOW())
        ON CONFLICT (event_id) DO UPDATE
        SET raw_payload = EXCLUDED.raw_payload,
            source_feed = EXCLUDED.source_feed,
            ingested_at = NOW();
    """)

    params = []
    for f in features:
        eid = str(f.get("id") or "").strip()
        if eid:
            params.append({
                "event_id": eid,
                "raw_payload": json.dumps(f),
                "source_feed": source_feed,
            })

    if not params:
        return 0

    with engine.begin() as conn:
        conn.execute(stmt, params)

    logger.info("Capa Raw: Upsert de %d eventos completado exitosamente", len(params))
    return len(params)


def upsert_staging_events(engine: Engine, annotated_records: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Inserta o actualiza registros válidos en la capa Silver (staging.earthquake_events).
    Los registros inválidos con fallas críticas son retenidos exclusivamente en Bronze (raw.earthquake_events_raw).
    Retorna (conteo_validos, conteo_invalidos).
    """
    if not annotated_records:
        return 0, 0

    valid_records = [r for r in annotated_records if r.get("is_valid", False)]
    invalid_count = len(annotated_records) - len(valid_records)

    if not valid_records:
        logger.warning("Capa Staging: 0 registros válidos en el lote. %d inválidos retenidos en Bronze.", invalid_count)
        return 0, invalid_count

    stmt = text("""
        INSERT INTO staging.earthquake_events (
            event_id, mag, place, time_utc, updated_utc, tsunami, sig,
            status, mag_type, event_type, url, longitude, latitude, depth_km,
            is_valid, validation_errors, processed_at
        ) VALUES (
            :event_id, :mag, :place, :time_utc, :updated_utc, :tsunami, :sig,
            :status, :mag_type, :event_type, :url, :longitude, :latitude, :depth_km,
            TRUE, '[]'::jsonb, NOW()
        )
        ON CONFLICT (event_id) DO UPDATE
        SET mag = EXCLUDED.mag,
            place = EXCLUDED.place,
            time_utc = EXCLUDED.time_utc,
            updated_utc = EXCLUDED.updated_utc,
            tsunami = EXCLUDED.tsunami,
            sig = EXCLUDED.sig,
            status = EXCLUDED.status,
            mag_type = EXCLUDED.mag_type,
            event_type = EXCLUDED.event_type,
            url = EXCLUDED.url,
            longitude = EXCLUDED.longitude,
            latitude = EXCLUDED.latitude,
            depth_km = EXCLUDED.depth_km,
            is_valid = TRUE,
            validation_errors = '[]'::jsonb,
            processed_at = NOW()
        WHERE EXCLUDED.updated_utc >= staging.earthquake_events.updated_utc
           OR staging.earthquake_events.updated_utc IS NULL;
    """)

    params = []
    for r in valid_records:
        params.append({
            "event_id": r["event_id"],
            "mag": r.get("mag"),
            "place": r.get("place"),
            "time_utc": r.get("time_utc"),
            "updated_utc": r.get("updated_utc"),
            "tsunami": r.get("tsunami", 0),
            "sig": r.get("sig"),
            "status": r.get("status"),
            "mag_type": r.get("mag_type"),
            "event_type": r.get("event_type"),
            "url": r.get("url"),
            "longitude": r.get("longitude"),
            "latitude": r.get("latitude"),
            "depth_km": r.get("depth_km"),
        })

    with engine.begin() as conn:
        conn.execute(stmt, params)

    logger.info("Capa Staging: %d válidos persistidos. %d inválidos retenidos en Bronze.", len(params), invalid_count)
    return len(params), invalid_count


def promote_staging_to_curated(engine: Engine) -> int:
    """
    Promociona exclusivamente los eventos con is_valid = TRUE de staging hacia la capa Gold (curated).
    Idempotente con resolución de colisiones por updated_utc.
    """
    stmt = text("""
        INSERT INTO curated.earthquake_events (
            event_id, mag, place, time_utc, updated_utc, tsunami, sig,
            status, mag_type, event_type, url, longitude, latitude, depth_km, curated_at
        )
        SELECT
            event_id, mag, place, time_utc, updated_utc, tsunami, sig,
            status, mag_type, event_type, url, longitude, latitude, depth_km, NOW()
        FROM staging.earthquake_events
        WHERE is_valid = TRUE
        ON CONFLICT (event_id) DO UPDATE
        SET mag = EXCLUDED.mag,
            place = EXCLUDED.place,
            time_utc = EXCLUDED.time_utc,
            updated_utc = EXCLUDED.updated_utc,
            tsunami = EXCLUDED.tsunami,
            sig = EXCLUDED.sig,
            status = EXCLUDED.status,
            mag_type = EXCLUDED.mag_type,
            event_type = EXCLUDED.event_type,
            url = EXCLUDED.url,
            longitude = EXCLUDED.longitude,
            latitude = EXCLUDED.latitude,
            depth_km = EXCLUDED.depth_km,
            curated_at = NOW()
        WHERE EXCLUDED.updated_utc >= curated.earthquake_events.updated_utc
           OR curated.earthquake_events.updated_utc IS NULL;
    """)

    with engine.begin() as conn:
        result = conn.execute(stmt)
        promoted_count = result.rowcount

    logger.info("Capa Curated: %d eventos válidos promocionados a Gold", promoted_count)
    return promoted_count


def save_data_quality_run(engine: Engine, quality_summary: Dict[str, Any], dag_run_id: str) -> str:
    """
    Guarda las métricas de la corrida de calidad en curated.data_quality_runs.
    """
    run_id = str(uuid.uuid4())
    stmt = text("""
        INSERT INTO curated.data_quality_runs (
            run_id, dag_run_id, evaluated_at, total_records, valid_records,
            invalid_records, freshness_ok, volume_ok, quality_score, rule_breakdown
        ) VALUES (
            CAST(:run_id AS uuid), :dag_run_id, NOW(), :total_records, :valid_records,
            :invalid_records, :freshness_ok, :volume_ok, :quality_score, CAST(:rule_breakdown AS jsonb)
        );
    """)

    with engine.begin() as conn:
        conn.execute(stmt, {
            "run_id": run_id,
            "dag_run_id": dag_run_id,
            "total_records": quality_summary.get("total_records", 0),
            "valid_records": quality_summary.get("valid_records", 0),
            "invalid_records": quality_summary.get("invalid_records", 0),
            "freshness_ok": bool(quality_summary.get("freshness_ok", True)),
            "volume_ok": bool(quality_summary.get("volume_ok", True)),
            "quality_score": float(quality_summary.get("quality_score", 0.0)),
            "rule_breakdown": json.dumps(quality_summary.get("rule_breakdown", {})),
        })

    logger.info("Calidad: Corrida registrada con ID %s y score %.2f%%", run_id, quality_summary.get("quality_score", 0.0))
    return run_id


def get_curated_metrics_last_24h(engine: Engine) -> Dict[str, Any]:
    """
    Calcula de forma determinista en SQL las métricas agregadas de las últimas 24 horas.
    Estas cifras se inyectan en el prompt para evitar alucinaciones del LLM.
    """
    stmt = text("""
        SELECT
            COUNT(*)::int AS total_events,
            COALESCE(MAX(mag), 0.0) AS max_mag,
            COALESCE(ROUND(AVG(mag)::numeric, 2), 0.0) AS avg_mag,
            COALESCE(SUM(CASE WHEN tsunami > 0 THEN 1 ELSE 0 END), 0)::int AS tsunami_count,
            COALESCE(MIN(time_utc), NOW() - INTERVAL '24 hours') AS earliest_time,
            COALESCE(MAX(time_utc), NOW()) AS latest_time
        FROM curated.earthquake_events
        WHERE time_utc >= NOW() - INTERVAL '24 hours';
    """)

    with engine.connect() as conn:
        row = conn.execute(stmt).fetchone()
        if row:
            return {
                "total_events": int(row.total_events),
                "max_mag": float(row.max_mag),
                "avg_mag": float(row.avg_mag),
                "tsunami_count": int(row.tsunami_count),
                "earliest_time": str(row.earliest_time),
                "latest_time": str(row.latest_time),
            }
        return {
            "total_events": 0,
            "max_mag": 0.0,
            "avg_mag": 0.0,
            "tsunami_count": 0,
            "earliest_time": "",
            "latest_time": "",
        }


def get_curated_events_last_24h(engine: Engine) -> List[Dict[str, Any]]:
    """Recupera todos los eventos sísmicos de las últimas 24 horas en curated."""
    stmt = text("""
        SELECT event_id, mag, place, time_utc, updated_utc, tsunami, sig,
               status, mag_type, event_type, url, longitude, latitude, depth_km
        FROM curated.earthquake_events
        WHERE time_utc >= NOW() - INTERVAL '24 hours'
        ORDER BY time_utc DESC;
    """)

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()
        return [dict(row._mapping) for row in rows]
