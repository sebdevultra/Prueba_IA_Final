"""
Pruebas Unitarias para el Módulo de Transformación (airflow/include/transformer.py).
"""

from datetime import datetime, timezone
from airflow.include.transformer import (
    flatten_geojson_feature,
    flatten_geojson_batch,
    ms_to_utc_datetime,
)


def test_ms_to_utc_datetime_conversion():
    """Verifica que los timestamps epoch en milisegundos se conviertan a UTC."""
    ms = 1729000000000
    dt = ms_to_utc_datetime(ms)
    assert dt is not None
    assert isinstance(dt, datetime)
    assert dt.tzinfo == timezone.utc


def test_ms_to_utc_datetime_null_handling():
    """Verifica el manejo de valores nulos o corruptos en timestamps."""
    assert ms_to_utc_datetime(None) is None
    assert ms_to_utc_datetime("invalid") is None


def test_flatten_geojson_feature_valid(sample_geojson_feature):
    """Verifica el aplanamiento correcto de un feature GeoJSON completo."""
    flat = flatten_geojson_feature(sample_geojson_feature)

    assert flat["event_id"] == "us7000m8v5"
    assert flat["mag"] == 5.4
    assert flat["place"] == "12 km SSW of Volcano, Hawaii"
    assert flat["longitude"] == -155.28
    assert flat["latitude"] == 19.34
    assert flat["depth_km"] == 10.2
    assert flat["tsunami"] == 0
    assert flat["status"] == "reviewed"
    assert flat["mag_type"] == "mww"
    assert flat["event_type"] == "earthquake"
    assert isinstance(flat["time_utc"], datetime)
    assert isinstance(flat["updated_utc"], datetime)


def test_flatten_geojson_feature_missing_coordinates():
    """Verifica que un feature sin coordenadas maneje None sin lanzar excepción."""
    incomplete_feature = {
        "id": "missing_coords_01",
        "properties": {"mag": 3.2, "place": "Test Area", "time": 1729000000000},
        "geometry": {"coordinates": []},
    }

    flat = flatten_geojson_feature(incomplete_feature)
    assert flat["event_id"] == "missing_coords_01"
    assert flat["mag"] == 3.2
    assert flat["longitude"] is None
    assert flat["latitude"] is None
    assert flat["depth_km"] is None


def test_flatten_geojson_batch(sample_geojson_feature):
    """Verifica que el aplanamiento por lote funcione correctamente."""
    batch = [sample_geojson_feature, {"invalid": "payload"}]
    records = flatten_geojson_batch(batch)
    assert len(records) == 1
    assert records[0]["event_id"] == "us7000m8v5"
