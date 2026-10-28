"""
DAG Diario de IA y Detección de Anomalías — SismoWatch
Frecuencia: Diario a las 02:00 UTC (0 2 * * *) y On-Demand
Automatización 1: Detección de anomalías con DBSCAN y Z-Score
Automatización 2: Reporte narrativo con IA generativa (Gemini + fallback determinista Jinja2)
"""

from datetime import datetime, timedelta, date
import logging
from airflow.decorators import dag, task

from airflow.include.db_utils import (
    get_db_engine,
    get_curated_events_last_24h,
    get_curated_metrics_last_24h,
)
from airflow.include.anomaly_detector import (
    detect_seismic_anomalies,
    save_anomalies_to_curated,
)
from airflow.include.ai_reporter import (
    generate_daily_report,
    save_daily_report_to_curated,
)

logger = logging.getLogger(__name__)


def alert_on_failure(context):
    """Callback ante fallos de tareas de IA."""
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    logger.error("ALERTA IA: Fallo en DAG '%s', Tarea '%s'", dag_id, task_id)


default_args = {
    "owner": "sismowatch_ai",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=10),
    "on_failure_callback": alert_on_failure,
}


@dag(
    dag_id="dag_ai_daily_report_and_anomalies",
    default_args=default_args,
    description="Detección analítica de anomalías y generación de reporte ejecutivo diario con IA",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "ai", "gemini", "dbscan", "anomalies", "reports"],
    doc_md="""
    # Automatización con IA y Detección de Anomalías
    - **Frecuencia:** Ejecución diaria consolidada a las 02:00 UTC o invocación on-demand desde la API de administración.
    - **Detección de Anomalías:** Algoritmos estadísticos Z-Score para picos horarios y DBSCAN con métrica Haversine para enjambres espaciales.
    - **Reporte Ejecutivo:** Integración con Google Gemini con structured outputs y validación Pydantic. Si la IA falla, excede el tiempo o genera números desfasados, conmuta al fallback determinista Jinja2 sin romper el pipeline.
    - **Auditoría:** Métricas de tokens, latencia y costos estimados registradas en `curated.ai_execution_logs`.
    """,
)
def dag_ai_daily_report_and_anomalies():

    @task(task_id="detect_and_persist_anomalies")
    def task_anomalies() -> list[dict]:
        """Recupera eventos curated de 24h y detecta anomalías espaciales y temporales."""
        engine = get_db_engine(role="transform")
        events = get_curated_events_last_24h(engine)
        logger.info("Analizando %d eventos de las últimas 24 horas para detección de anomalías...", len(events))

        anomalies = detect_seismic_anomalies(events)
        saved_count = save_anomalies_to_curated(engine, anomalies)
        logger.info("Se identificaron y guardaron %d anomalías en curated.seismic_anomalies", saved_count)
        return anomalies

    @task(task_id="generate_and_persist_daily_report")
    def task_report(anomalies: list[dict], **kwargs) -> str:
        """Calcula métricas preverificadas y genera el informe ejecutivo con IA."""
        engine = get_db_engine(role="transform")
        metrics = get_curated_metrics_last_24h(engine)
        events = get_curated_events_last_24h(engine)

        logger.info(
            "Generando reporte con métricas oficiales: Total=%d, MaxMag=%.1f, AvgMag=%.2f",
            metrics.get("total_events", 0), metrics.get("max_mag", 0.0), metrics.get("avg_mag", 0.0)
        )

        report_dict, log_dict = generate_daily_report(metrics, anomalies, events)

        # Determinar fecha del reporte
        ds = kwargs.get("ds")
        report_date = datetime.strptime(ds, "%Y-%m-%d").date() if ds else date.today()

        report_id = save_daily_report_to_curated(engine, report_dict, log_dict, report_date=report_date)
        logger.info("Reporte diario persistido exitosamente con ID %s para fecha %s", report_id, report_date)
        return report_id

    detected_anomalies = task_anomalies()
    task_report(detected_anomalies)


dag_ai_daily_report_and_anomalies()
