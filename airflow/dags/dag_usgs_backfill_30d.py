"""
DAG Parametrizado de Backfill Histórico — SismoWatch
Frecuencia: Manual / On-Demand (schedule=None)
Objetivo: Carga idempotente de los últimos 30 días (o período configurado) desde USGS API
Parámetros: days_back (int, default=30), min_magnitude (float, default=2.5)
"""

from datetime import datetime, timedelta, timezone
import logging
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.exceptions import AirflowException

from airflow.include.usgs_client import fetch_historical_window, USGSUnavailableError
from airflow.include.db_utils import get_db_engine, upsert_raw_events

logger = logging.getLogger(__name__)

default_args = {
    "owner": "sismowatch_ops",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=30),
}


@dag(
    dag_id="dag_usgs_backfill_30d",
    default_args=default_args,
    description="Carga histórica parametrizada de eventos sísmicos de USGS sin duplicar registros",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    params={
        "days_back": Param(30, type="integer", minimum=1, maximum=90, description="Días hacia atrás a consultar"),
        "min_magnitude": Param(2.5, type="number", minimum=0.0, maximum=10.0, description="Magnitud mínima de corte"),
    },
    tags=["sismowatch", "backfill", "historical", "usgs"],
    doc_md="""
    # Backfill Histórico Parametrizado (30 Días)
    - **Ejecución:** Manual bajo demanda mediante interfaz de Airflow o endpoint `POST /api/admin/backfill`.
    - **Estrategia de Ventanas:** Divide la ventana temporal en bloques de 5 días para evitar timeouts y saturación de memoria.
    - **Idempotencia:** Utiliza `ON CONFLICT (event_id) DO UPDATE` para garantizar que reejecuciones no dupliquen datos.
    - **Encadenamiento:** Al concluir la ingesta en raw, dispara automáticamente `dag_usgs_transform_and_quality`.
    """,
)
def dag_usgs_backfill_30d():

    @task(task_id="generate_date_windows")
    def create_windows(**kwargs) -> list[dict]:
        """Calcula ventanas de consulta de máximo 5 días considerando parámetros o fechas explícitas."""
        dag_run = kwargs.get("dag_run")
        conf = dag_run.conf if dag_run else {}
        params = kwargs.get("params", {})

        s_date_str = conf.get("start_date")
        e_date_str = conf.get("end_date")
        min_mag = float(conf.get("min_magnitude") or params.get("min_magnitude", 2.5))

        if s_date_str and e_date_str:
            start_dt = datetime.strptime(s_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(e_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt
            # Se adiciona un día a end_dt para incluir el día completo seleccionado en USGS
            end_dt = end_dt + timedelta(days=1)
        elif s_date_str:
            start_dt = datetime.strptime(s_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.now(timezone.utc)
        elif e_date_str:
            end_dt = datetime.strptime(e_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            days_back = int(conf.get("days_back") or params.get("days_back", 30))
            start_dt = end_dt - timedelta(days=days_back)
        else:
            days_back = int(conf.get("days_back") or params.get("days_back", 30))
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=days_back)

        windows = []
        current_start = start_dt
        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=5), end_dt)
            windows.append({
                "start_iso": current_start.strftime("%Y-%m-%d"),
                "end_iso": current_end.strftime("%Y-%m-%d"),
                "min_mag": min_mag,
            })
            current_start = current_end

        logger.info("Generadas %d ventanas temporales para el backfill histórico (%s a %s)", len(windows), start_dt.date(), end_dt.date())
        return windows

    @task(task_id="fetch_and_load_windows")
    def load_windows(windows: list[dict]) -> int:
        """Descarga e inserta los eventos de cada ventana en raw.earthquake_events_raw."""
        engine = get_db_engine(role="ingest")
        total_ingested = 0

        for idx, win in enumerate(windows, start=1):
            s_iso = win["start_iso"]
            e_iso = win["end_iso"]
            m_mag = win["min_mag"]
            logger.info("Procesando ventana [%d/%d]: %s a %s (min_mag=%.1f)", idx, len(windows), s_iso, e_iso, m_mag)

            try:
                res = fetch_historical_window(s_iso, e_iso, min_mag=m_mag, timeout=40, max_retries=3)
                feats = res.get("features", [])
                if feats:
                    cnt = upsert_raw_events(engine, feats, source_feed="backfill_query")
                    total_ingested += cnt
                    logger.info("Ventana [%d/%d]: %d eventos guardados en raw", idx, len(windows), cnt)
            except USGSUnavailableError as exc:
                logger.error("Error en ventana %s - %s: %s", s_iso, e_iso, exc)
                raise AirflowException(f"Fallo en ventana de backfill: {exc}") from exc

        logger.info("Backfill histórico culminado: %d eventos totales procesados en raw", total_ingested)
        return total_ingested

    trigger_transform = TriggerDagRunOperator(
        task_id="trigger_dag_transform_and_quality",
        trigger_dag_id="dag_usgs_transform_and_quality",
        wait_for_completion=False,
    )

    windows_list = create_windows()
    load_task = load_windows(windows_list)
    load_task >> trigger_transform


dag_usgs_backfill_30d()
