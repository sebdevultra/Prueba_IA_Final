"""
Motor de Calidad de Datos para SismoWatch.
Aplica compuertas bloqueantes de validación a nivel de registro y lote,
calcula el Quality Score y genera el desglose de reglas evaluadas.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple


def validate_event_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Valida un registro sísmico aplanado:
    1. Campos obligatorios no nulos: event_id, time_utc, latitude, longitude, depth_km, mag.
    2. Rangos espaciales y físicos plausibles:
       - -90.0 <= latitude <= 90.0
       - -180.0 <= longitude <= 180.0
       - -2.0 <= mag <= 10.0
       - -10.0 <= depth_km <= 1000.0
    3. time_utc no debe ser futuro (+5 min de margen por desfase de reloj).

    Retorna (True, []) si es válido o (False, ["MOTIVO_1", ...]) si incumple reglas.
    """
    errors: List[str] = []

    # 1. Validación de identificador único
    event_id = record.get("event_id")
    if not event_id or not str(event_id).strip():
        errors.append("MISSING_EVENT_ID")

    # 2. Validación de timestamp UTC
    time_utc = record.get("time_utc")
    if time_utc is None:
        errors.append("MISSING_TIME_UTC")
    elif isinstance(time_utc, datetime):
        now_utc = datetime.now(timezone.utc)
        # Tolerancia de 5 minutos hacia el futuro
        if time_utc > (now_utc + timedelta(minutes=5)):
            errors.append(f"FUTURE_TIMESTAMP: {time_utc.isoformat()} > {now_utc.isoformat()}")

    # 3. Validación de latitud (-90.0 a 90.0)
    lat = record.get("latitude")
    if lat is None:
        errors.append("MISSING_LATITUDE")
    elif not (-90.0 <= float(lat) <= 90.0):
        errors.append(f"OUT_OF_RANGE_LATITUDE: {lat}")

    # 4. Validación de longitud (-180.0 a 180.0)
    lon = record.get("longitude")
    if lon is None:
        errors.append("MISSING_LONGITUDE")
    elif not (-180.0 <= float(lon) <= 180.0):
        errors.append(f"OUT_OF_RANGE_LONGITUDE: {lon}")

    # 5. Validación de magnitud (-2.0 a 10.0)
    mag = record.get("mag")
    if mag is None:
        errors.append("MISSING_MAGNITUDE")
    elif not (-2.0 <= float(mag) <= 10.0):
        errors.append(f"OUT_OF_RANGE_MAGNITUDE: {mag}")

    # 6. Validación de profundidad (-10.0 km a 1000.0 km)
    depth = record.get("depth_km")
    if depth is None:
        errors.append("MISSING_DEPTH")
    elif not (-10.0 <= float(depth) <= 1000.0):
        errors.append(f"OUT_OF_RANGE_DEPTH: {depth}")

    is_valid = len(errors) == 0
    return is_valid, errors


def evaluate_batch_quality(
    records: List[Dict[str, Any]],
    last_success_utc: Optional[datetime] = None,
    freshness_threshold_minutes: int = 45,
    min_volume: int = 1,
    max_volume: int = 5000,
) -> Dict[str, Any]:
    """
    Evalúa la calidad de un lote de registros:
    - Deduplicación por event_id (conservando el más reciente según updated_utc).
    - Anotación de cada registro con 'is_valid' y 'validation_errors'.
    - Verificación de frescura: último evento respecto a la hora actual.
    - Verificación de volumen: número de registros dentro del rango esperado.
    - Calificación Quality Score porcentual (0.0% a 100.0%).
    """
    if not records:
        return {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "freshness_ok": True,
            "volume_ok": False,
            "quality_score": 0.0,
            "rule_breakdown": {"EMPTY_BATCH": 1},
            "annotated_records": [],
        }

    # 1. Deduplicación por event_id
    dedup_dict: Dict[str, Dict[str, Any]] = {}
    for r in records:
        eid = r.get("event_id")
        if not eid:
            # Si no tiene id, lo mantenemos para que falle en validación
            continue

        if eid not in dedup_dict:
            dedup_dict[eid] = r
        else:
            # Conservar el registro más actualizado
            curr_updated = dedup_dict[eid].get("updated_utc")
            new_updated = r.get("updated_utc")
            if new_updated and (curr_updated is None or new_updated > curr_updated):
                dedup_dict[eid] = r

    unique_records = list(dedup_dict.values())
    total_records = len(unique_records)

    valid_records = 0
    invalid_records = 0
    rule_breakdown: Dict[str, int] = {}
    annotated: List[Dict[str, Any]] = []

    latest_event_time: Optional[datetime] = None

    # 2. Evaluación individual de cada registro
    for rec in unique_records:
        rec_copy = dict(rec)
        is_valid, errors = validate_event_record(rec_copy)
        rec_copy["is_valid"] = is_valid
        rec_copy["validation_errors"] = errors
        annotated.append(rec_copy)

        if is_valid:
            valid_records += 1
            t = rec_copy.get("time_utc")
            if t and (latest_event_time is None or t > latest_event_time):
                latest_event_time = t
        else:
            invalid_records += 1
            for err in errors:
                err_category = err.split(":")[0]
                rule_breakdown[err_category] = rule_breakdown.get(err_category, 0) + 1

    # 3. Control de Frescura
    now_utc = datetime.now(timezone.utc)
    freshness_ok = True
    if latest_event_time:
        age_minutes = (now_utc - latest_event_time).total_seconds() / 60.0
        if age_minutes > freshness_threshold_minutes:
            freshness_ok = False
            rule_breakdown["STALE_DATA_WARNING"] = rule_breakdown.get("STALE_DATA_WARNING", 0) + 1

    # 4. Control de Volumen
    volume_ok = min_volume <= total_records <= max_volume
    if not volume_ok:
        rule_breakdown["VOLUME_ANOMALY"] = 1

    # 5. Cálculo del Quality Score
    quality_score = round((valid_records / total_records) * 100.0, 2) if total_records > 0 else 0.0

    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "freshness_ok": freshness_ok,
        "volume_ok": volume_ok,
        "quality_score": float(quality_score),
        "rule_breakdown": rule_breakdown,
        "annotated_records": annotated,
    }
