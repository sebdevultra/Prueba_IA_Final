"""
Punto de Entrada Principal de la API FastAPI — SismoWatch (SuperApp).
Configura middlewares de CORS, enrutadores modulares y endpoints de salud.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import auth, dashboard, reports, stream, admin, agent

app = FastAPI(
    title="SismoWatch API — Plataforma Sísmica en Tiempo Casi Real",
    description="""
    Backend analítico y de consumo de datos para Operaciones y Gestión de Riesgo.
    Implementa autenticación JWT, RBAC estricto, transmisión en vivo vía SSE,
    agente de IA con Ollama local y acceso exclusivo por capas Medallion (curated).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración de CORS restringido
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de Enrutadores
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(agent.router)
app.include_router(reports.router)
app.include_router(stream.router)
app.include_router(admin.router)


@app.get("/health", tags=["Salud"])
def health_check():
    """Endpoint de comprobación de salud para Docker y monitores."""
    return {"status": "healthy", "service": "sismowatch_api", "version": "1.0.0"}


@app.get("/", tags=["Salud"])
def root():
    return {
        "message": "Bienvenido a SismoWatch API. Visita /docs para la documentación interactiva Swagger.",
        "documentation": "/docs",
    }
