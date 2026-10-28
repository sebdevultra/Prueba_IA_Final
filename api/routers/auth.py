"""
Router de Autenticación para SismoWatch.
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from api.schemas import LoginRequest, TokenResponse, UserProfileResponse
from api.security import authenticate_user, create_access_token, get_current_user, UserAuth
from api.config import settings

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """
    Inicia sesión validando credenciales sembradas.
    Retorna token Bearer JWT con el rol asignado ('admin' o 'viewer').
    """
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas: usuario o contraseña inválidos",
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",  # nosec B106
        role=user.role,
        username=user.username,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: UserAuth = Depends(get_current_user)):
    """Retorna los datos de sesión y rol del usuario autenticado."""
    return UserProfileResponse(username=current_user.username, role=current_user.role)
