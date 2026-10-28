"""
Router de Dashboard, Métricas Sísmicas y Estado del Pipeline.
Solo accesible por usuarios autenticados (viewer o admin).
Lee exclusivamente de la capa Curated (Gold).
"""

from datetime import datetime, timezone
import logging
from typing import Optional
import requests
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.schemas import (
    KpiResponse,
    EventsListResponse,
    EarthquakeEventSchema,
    TimeseriesResponse,
    TimeseriesPoint,
    PipelineStatusResponse,
    DataQualityRunSchema,
)
from api.security import get_current_user, UserAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Dashboard & Analítica"])


@router.get("/kpis", response_model=KpiResponse)
def get_kpis(
    db: Session = Depends(get_db),
    _current_user: UserAuth = Depends(get_current_user),
):
    """
    Retorna los indicadores clave (KPIs) del dashboard calculados sobre las últimas 24 horas.
    """
    stmt = text("""
        SELECT
            COUNT(*)::int AS events_24h,
            COALESCE(MAX(mag), 0.0) AS max_magnitude,
            COALESCE(ROUND(AVG(mag)::numeric, 2), 0.0) AS avg_magnitude,
            COALESCE(SUM(CASE WHEN tsunami > 0 THEN 1 ELSE 0 END), 0)::int AS tsunami_count,
            COALESCE(MAX(time_utc), NOW()) AS last_update_utc
        FROM curated.earthquake_events
        WHERE time_utc >= NOW() - INTERVAL '24 hours';
    """)
    row = db.execute(stmt).fetchone()

    # Obtener el último Quality Score registrado
    stmt_quality = text("""
        SELECT quality_score, freshness_ok
        FROM curated.data_quality_runs
        ORDER BY evaluated_at DESC
        LIMIT 1;
    """)
    row_q = db.execute(stmt_quality).fetchone()

    quality_score = float(row_q[0]) if row_q else 100.0
    freshness_ok = bool(row_q[1]) if row_q else True

    events_24h = int(row[0]) if row else 0
    max_mag = float(row[1]) if row else 0.0
    avg_mag = float(row[2]) if row else 0.0
    tsunami_cnt = int(row[3]) if row else 0
    last_up = str(row[4]) if row else datetime.now(timezone.utc).isoformat()

    return KpiResponse(
        events_24h=events_24h,
        max_magnitude=max_mag,
        avg_magnitude=avg_mag,
        tsunami_count=tsunami_cnt,
        quality_score=quality_score,
        last_update_utc=last_up,
        freshness_ok=freshness_ok,
    )


@router.get("/events", response_model=EventsListResponse)
def get_events(
    min_mag: Optional[float] = Query(None, description="Magnitud mínima"),
    start_date: Optional[str] = Query(None, description="Fecha inicial ISO"),
    end_date: Optional[str] = Query(None, description="Fecha final ISO"),
    region: Optional[str] = Query(None, description="Búsqueda por texto en lugar/región"),
    tsunami: Optional[bool] = Query(None, description="Filtrar por presencia de alerta de tsunami"),
    sort_by: Optional[str] = Query("time_utc", description="Ordenar por: time_utc, mag, depth_km"),
    sort_order: Optional[str] = Query("desc", description="Orden: asc o desc"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db),
    _current_user: UserAuth = Depends(get_current_user),
):
    """
    Retorna el listado paginado y filtrable de eventos sísmicos certificados en curated.
    Soporta filtros por magnitud mínima, rango temporal, región, alerta de tsunami y ordenamiento configurable.
    """
    clauses = ["1=1"]
    params = {}

    if min_mag is not None:
        clauses.append("mag >= :min_mag")
        params["min_mag"] = min_mag

    if start_date:
        clauses.append("time_utc >= CAST(:start_date AS timestamptz)")
        params["start_date"] = start_date

    if end_date:
        clauses.append("time_utc <= CAST(:end_date AS timestamptz)")
        params["end_date"] = end_date

    if region:
        clauses.append("place ILIKE :region")
        params["region"] = f"%{region}%"

    if tsunami is not None:
        if tsunami:
            clauses.append("tsunami > 0")
        else:
            clauses.append("tsunami = 0")

    where_sql = " AND ".join(clauses)

    count_stmt = text(f"SELECT COUNT(*) FROM curated.earthquake_events WHERE {where_sql};")  # nosec B608
    total = db.execute(count_stmt, params).scalar() or 0

    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    # Mapeo seguro de campos de ordenamiento
    sort_mapping = {
        "time_utc": "time_utc",
        "mag": "mag",
        "depth_km": "depth_km",
        "place": "place",
    }
    col = sort_mapping.get(sort_by, "time_utc")
    direction = "ASC" if sort_order and sort_order.lower() == "asc" else "DESC"

    data_stmt = text(f"""
        SELECT event_id, mag, place, time_utc, updated_utc, tsunami, sig,
               status, mag_type, event_type, url, longitude, latitude, depth_km
        FROM curated.earthquake_events
        WHERE {where_sql}
        ORDER BY {col} {direction} NULLS LAST
        LIMIT :limit OFFSET :offset;
    """)  # nosec B608

    rows = db.execute(data_stmt, params).fetchall()
    events = [EarthquakeEventSchema(**dict(r._mapping)) for r in rows]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return EventsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        events=events,
    )


@router.get("/stats/timeseries", response_model=TimeseriesResponse)
def get_timeseries_stats(
    db: Session = Depends(get_db),
    _current_user: UserAuth = Depends(get_current_user),
):
    """
    Genera serie temporal de sismos por hora, distribución por magnitud y top regiones activas.
    Garantiza que la categoría Mayor (>= 6.0) siempre esté presente.
    """
    # 1. Puntos horarios (últimas 24 horas)
    stmt_hours = text("""
        SELECT
            TO_CHAR(DATE_TRUNC('hour', time_utc), 'YYYY-MM-DD HH24:00') AS hour,
            COUNT(*)::int AS event_count,
            COALESCE(ROUND(AVG(mag)::numeric, 2), 0.0) AS avg_mag,
            COALESCE(MAX(mag), 0.0) AS max_mag
        FROM curated.earthquake_events
        WHERE time_utc >= NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', time_utc)
        ORDER BY DATE_TRUNC('hour', time_utc) ASC;
    """)
    rows_h = db.execute(stmt_hours).fetchall()
    points = [TimeseriesPoint(hour=r[0], event_count=r[1], avg_mag=float(r[2]), max_mag=float(r[3])) for r in rows_h]

    # 2. Distribución por magnitudes (siempre incluye las 4 categorías clave)
    stmt_dist = text("""
        SELECT
            CASE
                WHEN mag < 2.5 THEN 'Menor (< 2.5)'
                WHEN mag >= 2.5 AND mag < 4.5 THEN 'Ligero (2.5 - 4.4)'
                WHEN mag >= 4.5 AND mag < 6.0 THEN 'Moderado (4.5 - 5.9)'
                ELSE 'Fuerte / Mayor (>= 6.0)'
            END AS category,
            COUNT(*)::int AS cnt
        FROM curated.earthquake_events
        WHERE time_utc >= NOW() - INTERVAL '24 hours'
        GROUP BY category;
    """)
    rows_dist = db.execute(stmt_dist).fetchall()
    distribution = {
        "Menor (< 2.5)": 0,
        "Ligero (2.5 - 4.4)": 0,
        "Moderado (4.5 - 5.9)": 0,
        "Fuerte / Mayor (>= 6.0)": 0,
    }
    for r in rows_dist:
        distribution[r[0]] = r[1]

    # 3. Top regiones activas
    stmt_regions = text("""
        SELECT
            COALESCE(NULLIF(TRIM(place), ''), 'Desconocido') AS region,
            COUNT(*)::int AS count,
            COALESCE(MAX(mag), 0.0) AS max_mag
        FROM curated.earthquake_events
        WHERE time_utc >= NOW() - INTERVAL '24 hours'
        GROUP BY region
        ORDER BY count DESC, max_mag DESC
        LIMIT 5;
    """)
    rows_reg = db.execute(stmt_regions).fetchall()
    top_regions = [{"region": r[0], "count": r[1], "max_mag": float(r[2])} for r in rows_reg]

    return TimeseriesResponse(
        points=points,
        distribution_by_magnitude=distribution,
        top_active_regions=top_regions,
    )


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
def get_pipeline_status(
    db: Session = Depends(get_db),
    _current_user: UserAuth = Depends(get_current_user),
):
    """
    Retorna el estado de observabilidad de los DAGs de Airflow y la última corrida de calidad.
    Consulta la REST API oficial de Apache Airflow en tiempo real.
    """
    # Última corrida de calidad
    stmt_q = text("""
        SELECT run_id, dag_run_id, evaluated_at, total_records, valid_records,
               invalid_records, freshness_ok, volume_ok, quality_score, rule_breakdown
        FROM curated.data_quality_runs
        ORDER BY evaluated_at DESC
        LIMIT 1;
    """)
    row_q = db.execute(stmt_q).fetchone()

    last_run = None
    if row_q:
        last_run = DataQualityRunSchema(
            run_id=str(row_q[0]),
            dag_run_id=row_q[1],
            evaluated_at=row_q[2],
            total_records=row_q[3],
            valid_records=row_q[4],
            invalid_records=row_q[5],
            freshness_ok=row_q[6],
            volume_ok=row_q[7],
            quality_score=float(row_q[8]),
            rule_breakdown=row_q[9] if isinstance(row_q[9], dict) else {},
        )

    # Consulta en vivo de DAGs a la API REST de Apache Airflow
    dags_info = []
    airflow_online = False
    try:
        resp = requests.get(
            f"{settings.airflow_internal_url}/api/v1/dags",
            auth=(settings.airflow_username, settings.airflow_password),
            timeout=5,
        )
        if resp.status_code == 200:
            airflow_online = True
            dags_list = resp.json().get("dags", [])
            for d in dags_list:
                did = d.get("dag_id")
                is_p = d.get("is_paused", False)
                sched = d.get("timetable_description") or (d.get("schedule_interval", {}) or {}).get("value") or "Manual"
                desc = d.get("description", "")

                last_state = "paused" if is_p else "ready"
                last_run_time = None
                try:
                    r_run = requests.get(
                        f"{settings.airflow_internal_url}/api/v1/dags/{did}/dagRuns?order_by=-execution_date&limit=1",
                        auth=(settings.airflow_username, settings.airflow_password),
                        timeout=3,
                    )
                    if r_run.status_code == 200:
                        runs = r_run.json().get("dag_runs", [])
                        if runs:
                            last_state = runs[0].get("state", last_state)
                            last_run_time = runs[0].get("end_date") or runs[0].get("execution_date")
                except Exception as exc:
                    logger.debug("No se pudo obtener runs para DAG %s: %s", did, exc)

                dags_info.append({
                    "dag_id": did,
                    "schedule": sched,
                    "state": last_state,
                    "is_paused": is_p,
                    "description": desc,
                    "last_run_time": last_run_time,
                })
    except Exception as exc:
        logger.warning("No se pudo consultar Airflow REST API: %s", exc)

    if not dags_info:
        dags_info = [
            {"dag_id": "dag_usgs_ingest_realtime", "schedule": "*/5 * * * *", "state": "active", "description": "Ingesta 5 min"},
            {"dag_id": "dag_usgs_transform_and_quality", "schedule": "Dataset Trigger", "state": "active", "description": "Medallion Silver/Gold"},
            {"dag_id": "dag_ai_daily_report_and_anomalies", "schedule": "0 2 * * *", "state": "active", "description": "DBSCAN + IA Gemini"},
            {"dag_id": "dag_usgs_backfill_30d", "schedule": "Manual", "state": "ready", "description": "Backfill 30 días"},
        ]

    return PipelineStatusResponse(
        airflow_online=airflow_online,
        dags_status=dags_info,
        last_quality_run=last_run,
        database_status="healthy",
    )
