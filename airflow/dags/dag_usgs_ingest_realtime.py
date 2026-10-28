"""
DAG de Ingesta en Tiempo Real — USGS Earthquake Feed
Frecuencia: Cada 5 minutos (*/5 * * * *)
Destino: Capa Bronze (raw.earthquake_events_raw)
Produce: Dataset("postgres://sismowatch/raw/earthquake_events_raw")
"""

from datetime import datetime, timedelta
import logging
from airflow.decorators import dag, task
from airflow.datasets import Dataset
from airflow.exceptions import AirflowException

from airflow.include.usgs_client import fetch_realtime_hour, USGSUnavailableError
from airflow.include.db_utils import get_db_engine, upsert_raw_events

logger = logging.getLogger(__name__)

RAW_DATASET = Dataset("postgres://sismowatch/raw/earthquake_events_raw")


def alert_on_failure(context):
    """Callback invocado cuando una tarea del DAG falla."""
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    exec_date = context.get("execution_date")
    exception = context.get("exception")
    logger.error(
        "ALERTA OPERACIONAL: Fallo en DAG '%s' | Tarea '%s' | Fecha: %s | Causa: %s",
        dag_id, task_id, exec_date, exception
    )


default_args = {
    "owner": "sismowatch_ops",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=20),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=5),
    "on_failure_callback": alert_on_failure,
}


@dag(
    dag_id="dag_usgs_ingest_realtime",
    default_args=default_args,
    description="Ingesta automatizada del feed USGS all_hour.geojson hacia la capa raw cada 5 minutos",
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "ingest", "realtime", "bronze", "usgs"],
    doc_md="""
    # Ingesta en Tiempo Real — USGS (Bronze)
    - **Frecuencia:** Cada 5 minutos.
    - **Fuente:** `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson`
    - **Destino:** Tabla inmutable `raw.earthquake_events_raw`.
    - **Idempotencia:** `ON CONFLICT (event_id) DO UPDATE SET raw_payload = EXCLUDED.raw_payload...`
    - **Seguridad:** Utiliza rol de base de datos con mínimo privilegio `role_ingest`.
    - **Desencadenador:** Al finalizar satisfactoriamente, emite el `Dataset` para activar la transformación reactiva.
    """,
)
def dag_usgs_ingest_realtime():

    @task(task_id="check_usgs_connectivity")
    def check_connectivity() -> bool:
        """Verifica disponibilidad previa de la fuente antes de iniciar la ingesta."""
        try:
            feed = fetch_realtime_hour(timeout=10, max_retries=1)
            count = len(feed.get("features", []))
            logger.info("Verificación de conectividad USGS exitosa (%d eventos disponibles)", count)
            return True
        except USGSUnavailableError as exc:
            logger.warning("USGS no respondió en chequeo rápido: %s. Procediendo con tarea principal.", exc)
            return False

    @task(task_id="extract_and_load_raw", outlets=[RAW_DATASET])
    def extract_and_load(precheck_ok: bool) -> int:
        """Extrae el feed GeoJSON completo e inserta de forma idempotente en la capa raw."""
        logger.info("Iniciando extracción de feed USGS en tiempo real...")
        try:
            feed_data = fetch_realtime_hour(timeout=20, max_retries=3)
        except USGSUnavailableError as exc:
            raise AirflowException(f"Error crítico de ingesta USGS: {str(exc)}") from exc

        features = feed_data.get("features", [])
        if not features:
            logger.warning("El feed de USGS retornó 0 eventos en la última hora.")
            return 0

        engine = get_db_engine(role="ingest")
        inserted_count = upsert_raw_events(engine, features, source_feed="realtime_hour")
        logger.info("Ingesta completada: %d registros insertados/actualizados en raw.earthquake_events_raw", inserted_count)
        return inserted_count

    precheck = check_connectivity()
    extract_and_load(precheck)


dag_usgs_ingest_realtime()
