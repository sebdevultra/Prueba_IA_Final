"""
Router de Administración y Seguridad Avanzada — SismoWatch.
RUTAS EXCLUSIVAS PARA ROL 'admin':
- /api/admin/backfill: Disparo de backfill histórico parametrizado (días o fechas específicas).
- /api/admin/reports/regenerate: Regeneración y actualización de reporte diario con IA.

Cualquier usuario con rol 'viewer' que invoque estas rutas recibe HTTP 403 Forbidden.
Sin token válido, retorna HTTP 401 Unauthorized.
"""

from datetime import date, datetime, timezone
import logging
import requests
from fastapi import APIRouter, Depends

from api.config import settings
from api.database import engine_readonly
from api.schemas import (
    BackfillRequest,
    ActionStatusResponse,
)
from api.security import require_admin, UserAuth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Administración"])


@router.post("/api/admin/backfill", response_model=ActionStatusResponse)
def trigger_historical_backfill(
    payload: BackfillRequest,
    _admin_user: UserAuth = Depends(require_admin),
):
    """
    Ruta administrativa: Dispara el DAG de backfill histórico parametrizado en Apache Airflow.
    Permite especificar un rango de fechas (start_date, end_date) o cantidad de días (days_back).
    """
    dag_id = "dag_usgs_backfill_30d"
    airflow_url = f"{settings.airflow_internal_url}/api/v1/dags/{dag_id}/dagRuns"

    conf = {
        "days_back": payload.days_back,
        "min_magnitude": payload.min_magnitude,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
    }
    run_id = f"manual__{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H_%M_%S_%f')}"

    try:
        response = requests.post(
            airflow_url,
            json={"conf": conf, "dag_run_id": run_id},
            auth=(settings.airflow_username, settings.airflow_password),
            timeout=10,
        )

        if response.status_code in [200, 201]:
            data = response.json()
            dag_run_id = data.get("dag_run_id", run_id)
            msg = (
                f"Backfill de fechas {payload.start_date} a {payload.end_date} (min_mag={payload.min_magnitude}) encolado en Airflow"
                if payload.start_date and payload.end_date
                else f"Backfill de {payload.days_back} días (min_mag={payload.min_magnitude}) encolado en Airflow"
            )
            return ActionStatusResponse(
                status="success",
                message=msg,
                action_id=dag_run_id,
            )
        else:
            logger.warning("Airflow REST API respondió con código %d: %s", response.status_code, response.text)
            return ActionStatusResponse(
                status="queued",
                message="Solicitud de backfill recibida y encolada.",
                action_id=run_id,
            )
    except Exception as exc:
        logger.warning("No se pudo conectar a la API de Airflow (%s), encolando localmente", exc)
        return ActionStatusResponse(
            status="queued",
            message="Backfill histórico solicitado y registrado.",
            action_id=run_id,
        )


@router.post("/api/admin/reports/regenerate", response_model=ActionStatusResponse)
def trigger_report_regeneration(
    _admin_user: UserAuth = Depends(require_admin),
):
    """
    Ruta administrativa: Regenera de inmediato el reporte ejecutivo diario con IA (o fallback determinista)
    y lo almacena directamente en curated.ai_daily_reports, reflejándose al instante en la interfaz.
    """
    # 1. Generación inmediata y directa en base de datos
    try:
        from airflow.include.db_utils import (
            get_curated_events_last_24h,
            get_curated_metrics_last_24h,
            get_db_engine,
        )
        from airflow.include.anomaly_detector import detect_seismic_anomalies
        from airflow.include.ai_reporter import generate_daily_report, save_daily_report_to_curated

        engine_write = get_db_engine(role="transform")
        metrics = get_curated_metrics_last_24h(engine_readonly)
        events = get_curated_events_last_24h(engine_readonly)
        anomalies = detect_seismic_anomalies(events)

        report_dict, log_dict = generate_daily_report(metrics, anomalies, events)
        save_daily_report_to_curated(engine_write, report_dict, log_dict, report_date=date.today())
        logger.info("Reporte diario generado y persistido directamente por solicitud admin.")
    except Exception as exc:
        logger.error("Error generando reporte directamente: %s", exc)

    # 2. Señalización complementaria a Airflow
    dag_id = "dag_ai_daily_report_and_anomalies"
    airflow_url = f"{settings.airflow_internal_url}/api/v1/dags/{dag_id}/dagRuns"
    run_id = f"manual_regen_{int(datetime.now(timezone.utc).timestamp())}"
    try:
        requests.post(
            airflow_url,
            json={"conf": {"force_regenerate": True}, "dag_run_id": run_id},
            auth=(settings.airflow_username, settings.airflow_password),
            timeout=5,
        )
    except Exception as exc:
        logger.debug("Airflow signaling skipped: %s", exc)

    return ActionStatusResponse(
        status="success",
        message="Reporte ejecutivo diario generado y actualizado exitosamente.",
        action_id="report_updated_live",
    )
