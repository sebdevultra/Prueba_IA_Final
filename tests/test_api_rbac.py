"""
Pruebas de Seguridad y Control de Acceso por Roles (RBAC) en FastAPI.
Valida el cumplimiento estricto de autenticación JWT y restricción de endpoints administrativos.
"""

from fastapi.testclient import TestClient
from api.main import app
from api.config import settings

client = TestClient(app)


def test_health_check_public():
    """El endpoint /health debe ser accesible públicamente sin autenticación."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_unauthenticated_access_denied():
    """Cualquier endpoint de datos sin token Bearer debe retornar HTTP 401 Unauthorized."""
    endpoints = [
        "/api/kpis",
        "/api/events",
        "/api/stats/timeseries",
        "/api/reports",
        "/api/pipeline/status",
        "/api/agent/chat",
    ]

    for ep in endpoints:
        res = client.get(ep) if ep != "/api/agent/chat" else client.post(ep, json={"message": "hola"})
        assert res.status_code == 401, f"Endpoint {ep} no bloqueó acceso anónimo (obtenido {res.status_code})"


def test_login_invalid_credentials():
    """Credenciales incorrectas deben retornar 401 Unauthorized."""
    res = client.post("/auth/login", json={"username": "hacker", "password": "wrongpassword"})
    assert res.status_code == 401


def test_login_viewer_success():
    """El login con usuario viewer debe devolver un token JWT con rol 'viewer'."""
    res = client.post("/auth/login", json={
        "username": settings.viewer_username,
        "password": settings.viewer_password,
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "viewer"


def test_login_admin_success():
    """El login con usuario admin debe devolver un token JWT con rol 'admin'."""
    res = client.post("/auth/login", json={
        "username": settings.admin_username,
        "password": settings.admin_password,
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"


def test_viewer_forbidden_from_admin_backfill():
    """Un usuario con rol 'viewer' que intenta lanzar un backfill DEBE recibir HTTP 403 Forbidden."""
    login_res = client.post("/auth/login", json={
        "username": settings.viewer_username,
        "password": settings.viewer_password,
    })
    token = login_res.json()["access_token"]

    res = client.post(
        "/api/admin/backfill",
        headers={"Authorization": f"Bearer {token}"},
        json={"days_back": 15, "min_magnitude": 3.0},
    )
    assert res.status_code == 403


def test_viewer_forbidden_from_admin_reports_regenerate():
    """Un usuario con rol 'viewer' que intenta regenerar reportes DEBE recibir HTTP 403 Forbidden."""
    login_res = client.post("/auth/login", json={
        "username": settings.viewer_username,
        "password": settings.viewer_password,
    })
    token = login_res.json()["access_token"]

    res = client.post(
        "/api/admin/reports/regenerate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_admin_allowed_access_reports_regenerate():
    """Un usuario con rol 'admin' debe tener acceso a /api/admin/reports/regenerate."""
    login_res = client.post("/auth/login", json={
        "username": settings.admin_username,
        "password": settings.admin_password,
    })
    token = login_res.json()["access_token"]

    res = client.post(
        "/api/admin/reports/regenerate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"


def test_authenticated_user_access_agent_chat(monkeypatch):
    """Un usuario autenticado (viewer o admin) puede consultar al agente de IA y recibe respuesta estructurada."""
    login_res = client.post("/auth/login", json={
        "username": settings.viewer_username,
        "password": settings.viewer_password,
    })
    token = login_res.json()["access_token"]

    class MockResponse:
        status_code = 200
        def json(self):
            return {"response": "Análisis sísmico de la capa Gold: actividad moderada registrada."}

    monkeypatch.setattr("requests.post", lambda *args, **kwargs: MockResponse())

    res = client.post(
        "/api/agent/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "¿Cuáles son los sismos más fuertes de la capa Gold?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "model" in data
    assert "data_points_analyzed" in data
    assert "sources_used" in data
    assert len(data["reply"]) > 10
