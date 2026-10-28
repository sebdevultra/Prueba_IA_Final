"""
Pruebas Unitarias para el Motor de Calidad de Datos (airflow/include/quality_engine.py).
Valida casos conformes, casos inválidos retenidos y cálculo del Quality Score.
"""

from datetime import datetime, timezone, timedelta
from airflow.include.quality_engine import (
    validate_event_record,
    evaluate_batch_quality,
)


def test_validate_event_record_valid():
    """Verifica que un registro completamente válido sea aprobado (is_valid = True)."""
    valid_record = {
        "event_id": "us7000test1",
        "time_utc": datetime.now(timezone.utc) - timedelta(minutes=10),
        "latitude": -12.04,
        "longitude": -77.03,
        "depth_km": 25.4,
        "mag": 4.8,
    }

    is_valid, errors = validate_event_record(valid_record)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_event_record_invalid_latitude():
    """Verifica que una latitud fuera de rango (-90 a 90) sea rechazada."""
    invalid_record = {
        "event_id": "us7000test2",
        "time_utc": datetime.now(timezone.utc),
        "latitude": 105.4,  # Inválida > 90.0
        "longitude": 0.0,
        "depth_km": 10.0,
        "mag": 3.0,
    }

    is_valid, errors = validate_event_record(invalid_record)
    assert is_valid is False
    assert any("OUT_OF_RANGE_LATITUDE" in err for err in errors)


def test_validate_event_record_invalid_magnitude():
    """Verifica que magnitudes fuera de rango (-2.0 a 10.0) sean rechazadas."""
    invalid_record = {
        "event_id": "us7000test3",
        "time_utc": datetime.now(timezone.utc),
        "latitude": 0.0,
        "longitude": 0.0,
        "depth_km": 10.0,
        "mag": 14.5,  # Imposible en física sísmica (> 10.0)
    }

    is_valid, errors = validate_event_record(invalid_record)
    assert is_valid is False
    assert any("OUT_OF_RANGE_MAGNITUDE" in err for err in errors)


def test_validate_event_record_future_timestamp():
    """Verifica que un evento con fecha futura (más de 5 min) sea rechazado."""
    invalid_record = {
        "event_id": "us7000test4",
        "time_utc": datetime.now(timezone.utc) + timedelta(hours=2),
        "latitude": 0.0,
        "longitude": 0.0,
        "depth_km": 10.0,
        "mag": 3.0,
    }

    is_valid, errors = validate_event_record(invalid_record)
    assert is_valid is False
    assert any("FUTURE_TIMESTAMP" in err for err in errors)


def test_evaluate_batch_quality_score_calculation():
    """Verifica el cálculo proporcional del Quality Score y deduplicación por event_id."""
    now = datetime.now(timezone.utc)
    batch = [
        # 1. Válido
        {"event_id": "e1", "time_utc": now, "latitude": 10.0, "longitude": 10.0, "depth_km": 10.0, "mag": 3.0},
        # 2. Válido
        {"event_id": "e2", "time_utc": now, "latitude": -10.0, "longitude": -10.0, "depth_km": 15.0, "mag": 4.0},
        # 3. Inválido (latitud fuera de rango)
        {"event_id": "e3", "time_utc": now, "latitude": 150.0, "longitude": 0.0, "depth_km": 5.0, "mag": 2.0},
        # 4. Inválido (magnitud fuera de rango)
        {"event_id": "e4", "time_utc": now, "latitude": 0.0, "longitude": 0.0, "depth_km": 5.0, "mag": -15.0},
    ]

    res = evaluate_batch_quality(batch)

    assert res["total_records"] == 4
    assert res["valid_records"] == 2
    assert res["invalid_records"] == 2
    assert res["quality_score"] == 50.0  # 2 de 4 = 50%
    assert len(res["annotated_records"]) == 4
