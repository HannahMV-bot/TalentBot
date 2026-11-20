from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from backend.app.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


def crear_token_acceso(datos: dict):
    """
    Genera un token JWT para el usuario autenticado.
    """

    datos_token = datos.copy()

    fecha_expiracion = (
        datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    datos_token.update({
        "exp": fecha_expiracion
    })

    token = jwt.encode(
        datos_token,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def verificar_token(token: str):
    """
    Verifica la validez de un token JWT.
    """

    try:
        datos = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return datos

    except JWTError:
        return None
