"""
Gestor de conexiones a base de datos para la API de SismoWatch.
Garantiza el uso del rol de mínimo privilegio (readonly_user).
"""

import os
import socket
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from api.config import settings

Base = declarative_base()


def resolve_db_uri(base_uri: str) -> str:
    """Resuelve la URI adaptando 'postgres:5432' a 'localhost:5435' si se corre en el host."""
    uri = base_uri
    if "postgres:5432" in uri and not os.path.exists("/.dockerenv"):
        try:
            socket.gethostbyname("postgres")
        except socket.gaierror:
            uri = uri.replace("postgres:5432", "localhost:5435")
    return uri


engine_readonly: Engine = create_engine(
    resolve_db_uri(settings.db_readonly_conn_uri),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocalReadonly = sessionmaker(autocommit=False, autoflush=False, bind=engine_readonly)


def get_db() -> Generator[Session, None, None]:
    """Inyector de dependencias para sesiones de base de datos en endpoints FastAPI."""
    db = SessionLocalReadonly()
    try:
        yield db
    finally:
        db.close()
