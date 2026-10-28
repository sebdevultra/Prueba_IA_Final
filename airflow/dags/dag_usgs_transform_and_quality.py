"""
DAG de Transformación, Calidad y Promoción — Medallion Pipeline
Disparador: Dataset("postgres://sismowatch/raw/earthquake_events_raw")
Capa Silver: staging.earthquake_events (Retención de válidos e inválidos con motivos)
Capa Gold: curated.earthquake_events (Solo registros que aprueban 100% de calidad)
Produce: Dataset("postgres://sismowatch/curated/earthquake_events")
"""

from datetime import datetime, timedelta
import json
import logging
from airflow.decorators import dag, task, task_group
from airflow.datasets import Dataset
from airflow.exceptions import AirflowException
from sqlalchemy import text

from airflow.include.db_utils import (
    get_db_engine,
    upsert_staging_events,
    promote_staging_to_curated,
    save_data_quality_run,
)
from airflow.include.transformer import flatten_geojson_batch
from airflow.include.quality_engine import evaluate_batch_quality

logger = logging.getLogger(__name__)

RAW_DATASET = Dataset("postgres://sismowatch/raw/earthquake_events_raw")
CURATED_DATASET = Dataset("postgres://sismowatch/curated/earthquake_events")


def alert_on_failure(context):
    """Callback de alerta ante fallos."""
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    logger.error("ALERTA CRÍTICA: Fallo en DAG '%s', Tarea '%s'", dag_id, task_id)


default_args = {
    "owner": "sismowatch_data",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=15),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=10),
    "on_failure_callback": alert_on_failure,
}


@dag(
    dag_id="dag_usgs_transform_and_quality",
    default_args=default_args,
    description="Procesa datos de raw hacia staging con validaciones bloqueantes y promueve a curated",
    schedule=[RAW_DATASET],
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "transform", "quality", "silver", "gold"],
    doc_md="""
    # Pipeline de Transformación y Calidad (Medallion)
    - **Activación:** Event-driven por actualización en el `RAW_DATASET`.
    - **Capa Staging (Silver):** Convierte GeoJSON a columnas relacionales y evalúa reglas de validación física/espacial. Los registros con `is_valid = FALSE` son retenidos en staging para auditoría y NO pasan a curated.
    - **Capa Curated (Gold):** Recibe exclusivamente registros con `is_valid = TRUE`.
    - **Métricas:** Guarda el resultado del lote en `curated.data_quality_runs`.
    """,
)
def dag_usgs_transform_and_quality():

    @task_group(group_id="tg_transform")
    def transform_group():

        @task(task_id="extract_recent_raw_events")
        def extract_raw() -> list[dict]:
            """Extrae los eventos de raw pendientes de procesamiento o actualizados."""
            engine = get_db_engine(role="transform")
            stmt = text("""
                SELECT r.raw_payload
                FROM raw.earthquake_events_raw r
                LEFT JOIN curated.earthquake_events c ON r.event_id = c.event_id
                WHERE c.event_id IS NULL OR r.ingested_at >= NOW() - INTERVAL '6 hours'
                ORDER BY r.ingested_at DESC;
            """)
            with engine.connect() as conn:
                rows = conn.execute(stmt).fetchall()
                features = [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in rows]

            logger.info("Extraídos %d eventos crudos desde raw.earthquake_events_raw", len(features))
            return features

        @task(task_id="flatten_geojson")
        def flatten_features(features: list[dict]) -> list[dict]:
            """Aplana y tipa los features GeoJSON."""
            records = flatten_geojson_batch(features)
            logger.info("Aplanados %d registros relacionales", len(records))
            return records

        raw_feats = extract_raw()
        return flatten_features(raw_feats)

    @task_group(group_id="tg_quality")
    def quality_group(records: list[dict]):

        @task(task_id="evaluate_and_persist_staging")
        def evaluate_and_persist(recs: list[dict], **kwargs) -> dict:
            """
            Aplica compuertas de calidad, persiste registros anotados en staging
            y registra las métricas en curated.data_quality_runs.
            """
            dag_run = kwargs.get("dag_run")
            dag_run_id = dag_run.run_id if dag_run else "manual_run"

            quality_eval = evaluate_batch_quality(recs)
            annotated = quality_eval.pop("annotated_records", [])

            engine = get_db_engine(role="transform")
            valid_cnt, invalid_cnt = upsert_staging_events(engine, annotated)

            # Persistir corrida de calidad
            run_id = save_data_quality_run(engine, quality_eval, dag_run_id=dag_run_id)
            logger.info(
                "Calidad completada: %d válidos, %d inválidos (Score: %.2f%%). Run ID: %s",
                valid_cnt, invalid_cnt, quality_eval.get("quality_score", 0.0), run_id
            )

            # Si el lote no contiene ningún registro válido habiendo datos, levantar alerta
            if quality_eval.get("total_records", 0) > 0 and valid_cnt == 0:
                raise AirflowException("Compuerta de calidad bloqueante: 0 registros válidos en el lote.")

            return {
                "valid_count": valid_cnt,
                "invalid_count": invalid_cnt,
                "quality_score": quality_eval.get("quality_score", 0.0),
            }

        return evaluate_and_persist(records)

    @task_group(group_id="tg_curated")
    def curated_group(quality_result: dict):

        @task(task_id="promote_valid_to_curated", outlets=[CURATED_DATASET])
        def promote_records(q_res: dict) -> int:
            """Promociona registros válidos desde staging a curated."""
            engine = get_db_engine(role="transform")
            promoted = promote_staging_to_curated(engine)
            logger.info("Promoción exitosa: %d registros incorporados a curated.earthquake_events", promoted)
            return promoted

        return promote_records(quality_result)

    flat_records = transform_group()
    q_result = quality_group(flat_records)
    curated_group(q_result)


dag_usgs_transform_and_quality()
