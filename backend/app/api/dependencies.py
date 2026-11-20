from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.database.connection import obtener_db
from backend.app.database.models import Usuario
from backend.app.services.jwt_service import verificar_token


# Obtener el token Bearer enviado por el usuario
bearer_scheme = HTTPBearer()


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(obtener_db)
):
    """
    Verifica el token JWT y obtiene el usuario autenticado.
    """

    excepcion_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la autenticación.",
        headers={"WWW-Authenticate": "Bearer"}
    )

    # Extraer el token
    token = credenciales.credentials

    # Verificar el token JWT
    datos_token = verificar_token(token)

    if datos_token is None:
        raise excepcion_credenciales

    # Obtener el identificador del usuario
    id_usuario = datos_token.get("sub")

    if not id_usuario or not str(id_usuario).isdigit():
        raise excepcion_credenciales

    # Buscar el usuario en la base de datos
    usuario = db.query(Usuario).filter(
        Usuario.id == int(id_usuario)
    ).first()

    if usuario is None:
        raise excepcion_credenciales

    return usuario
