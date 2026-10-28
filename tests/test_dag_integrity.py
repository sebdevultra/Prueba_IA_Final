"""
Pruebas de Integridad de DAGs en Apache Airflow.
Valida que todos los DAGs del proyecto se importen sin errores de sintaxis, dependencias o ciclos.
"""

from pathlib import Path
import pytest
from airflow.models import DagBag

DAGS_FOLDER = str(Path(__file__).parent.parent / "airflow" / "dags")


@pytest.fixture(scope="module")
def dag_bag():
    """Carga todos los DAGs desde la carpeta airflow/dags."""
    return DagBag(dag_folder=DAGS_FOLDER, include_examples=False)


def test_no_import_errors(dag_bag):
    """Verifica que ningún DAG tenga errores de importación."""
    assert len(dag_bag.import_errors) == 0, f"Errores al importar DAGs: {dag_bag.import_errors}"


def test_expected_dags_present(dag_bag):
    """Verifica la presencia de los 4 DAGs especificados en la arquitectura."""
    expected_dags = [
        "dag_usgs_ingest_realtime",
        "dag_usgs_transform_and_quality",
        "dag_ai_daily_report_and_anomalies",
        "dag_usgs_backfill_30d",
    ]

    for dag_id in expected_dags:
        assert dag_id in dag_bag.dags, f"DAG obligatorio '{dag_id}' no encontrado en el DagBag"
        dag = dag_bag.dags[dag_id]
        assert dag.max_active_runs == 1, f"DAG '{dag_id}' debe tener max_active_runs=1 para evitar colisiones"
        assert dag.catchup is False, f"DAG '{dag_id}' debe tener catchup=False"
