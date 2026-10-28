"""
Módulo de Seguridad, Autenticación JWT y Control de Acceso Basado en Roles (RBAC).
Cumple requisitos de mínimo privilegio:
- Viewer: acceso a dashboard, eventos, reportes, SSE.
- Admin: acceso a backfill manual, regeneración de reportes y consultas al Agente Gold.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from api.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_bearer = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    username: str
    role: str


class UserAuth(BaseModel):
    username: str
    role: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera hash bcrypt para una contraseña."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Genera un token JWT firmado con HS256."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def authenticate_user(username: str, password: str) -> Optional[UserAuth]:
    """
    Autentica usuarios sembrados a partir de variables de entorno.
    Evita credenciales hardcodeadas en el código fuente.
    """
    if username == settings.admin_username and password == settings.admin_password:
        return UserAuth(username=username, role="admin")

    if username == settings.viewer_username and password == settings.viewer_password:
        return UserAuth(username=username, role="viewer")

    return None


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> UserAuth:
    """
    Valida el token Bearer JWT.
    Lanza 401 Unauthorized si no hay token o es inválido/expirado.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado: cabecera Authorization Bearer requerida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: atributos sub o role faltantes",
            )
        return UserAuth(username=username, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado o inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_current_user_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    token: Optional[str] = Query(None, description="Token JWT opcional para descargas directas en navegador"),
) -> UserAuth:
    """
    Autentica usuario vía cabecera Bearer O vía parámetro de consulta ?token=
    (Esencial para descargas directas de CSV/HTML/PDF desde enlaces <a href> en navegador).
    """
    raw_token = credentials.credentials if (credentials and credentials.credentials) else token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado: cabecera Authorization Bearer o parámetro ?token requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(raw_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: atributos sub o role faltantes",
            )
        return UserAuth(username=username, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado o inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def require_admin(current_user: UserAuth = Depends(get_current_user)) -> UserAuth:
    """
    Protege rutas exclusivas de administración.
    Retorna 403 Forbidden si el rol es 'viewer' u otro distinto a 'admin'.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requieren privilegios de Administrador para esta acción",
        )
    return current_user
