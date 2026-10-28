"""
Módulo de normalización y aplanamiento de eventos GeoJSON a modelo relacional.
Convierte timestamps epoch en milisegundos a datetimes con zona horaria UTC
y desglosa el vector de coordenadas en columnas individuales.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def ms_to_utc_datetime(ms: Optional[int | float]) -> Optional[datetime]:
    """Convierte un timestamp epoch en milisegundos a un objeto datetime UTC."""
    if ms is None:
        return None
    try:
        # USGS maneja milisegundos
        return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def flatten_geojson_feature(feature: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recibe un elemento del arreglo 'features' GeoJSON y retorna un dict relacional:
    - event_id: str
    - mag: float | None
    - place: str | None
    - time_utc: datetime | None
    - updated_utc: datetime | None
    - tsunami: int
    - sig: int | None
    - status: str | None
    - mag_type: str | None
    - event_type: str | None
    - url: str | None
    - longitude: float | None
    - latitude: float | None
    - depth_km: float | None
    """
    if not isinstance(feature, dict):
        return {}

    event_id = str(feature.get("id") or "").strip()
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else []

    # Extraer magnitud de forma segura
    mag_raw = properties.get("mag")
    try:
        mag = float(mag_raw) if mag_raw is not None else None
    except (ValueError, TypeError):
        mag = None

    # Coordenadas: [longitude, latitude, depth_km]
    longitude = None
    latitude = None
    depth_km = None

    if isinstance(coordinates, (list, tuple)):
        if len(coordinates) >= 1:
            try:
                longitude = float(coordinates[0]) if coordinates[0] is not None else None
            except (ValueError, TypeError):
                longitude = None

        if len(coordinates) >= 2:
            try:
                latitude = float(coordinates[1]) if coordinates[1] is not None else None
            except (ValueError, TypeError):
                latitude = None

        if len(coordinates) >= 3:
            try:
                depth_km = float(coordinates[2]) if coordinates[2] is not None else None
            except (ValueError, TypeError):
                depth_km = None

    # Tsunami flag (0 o 1)
    tsunami_raw = properties.get("tsunami")
    try:
        tsunami = int(tsunami_raw) if tsunami_raw is not None else 0
    except (ValueError, TypeError):
        tsunami = 0

    # Significance score
    sig_raw = properties.get("sig")
    try:
        sig = int(sig_raw) if sig_raw is not None else None
    except (ValueError, TypeError):
        sig = None

    place_raw = properties.get("place")
    place = str(place_raw).strip() if place_raw is not None else None

    status_raw = properties.get("status")
    status = str(status_raw).strip() if status_raw is not None else None

    mag_type_raw = properties.get("magType")
    mag_type = str(mag_type_raw).strip() if mag_type_raw is not None else None

    event_type_raw = properties.get("type")
    event_type = str(event_type_raw).strip() if event_type_raw is not None else None

    url_raw = properties.get("url")
    url = str(url_raw).strip() if url_raw is not None else None

    time_utc = ms_to_utc_datetime(properties.get("time"))
    updated_utc = ms_to_utc_datetime(properties.get("updated"))

    return {
        "event_id": event_id,
        "mag": mag,
        "place": place,
        "time_utc": time_utc,
        "updated_utc": updated_utc,
        "tsunami": tsunami,
        "sig": sig,
        "status": status,
        "mag_type": mag_type,
        "event_type": event_type,
        "url": url,
        "longitude": longitude,
        "latitude": latitude,
        "depth_km": depth_km,
    }


def flatten_geojson_batch(features: list[dict]) -> list[dict]:
    """Aplaza un lote completo de features GeoJSON."""
    records = []
    for f in features:
        if isinstance(f, dict):
            flat = flatten_geojson_feature(f)
            if flat and flat.get("event_id"):
                records.append(flat)
    return records
