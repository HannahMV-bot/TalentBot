from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.app.database.connection import obtener_db
from backend.app.services.jwt_service import crear_token_acceso
from backend.app.api.dependencies import obtener_usuario_actual

from backend.app.services.user_service import (
    registrar_usuario,
    iniciar_sesion
)


router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)


# ==========================================
# MODELOS DE DATOS
# ==========================================

class RegistroRequest(BaseModel):
    nombres: str
    apellidos: str
    correo: EmailStr
    contrasena: str


class LoginRequest(BaseModel):
    correo: EmailStr
    contrasena: str


# ==========================================
# REGISTRO DE USUARIOS
# ==========================================

@router.post("/registro")
def registro(
    datos: RegistroRequest,
    db: Session = Depends(obtener_db)
):
    usuario = registrar_usuario(
        db=db,
        nombres=datos.nombres,
        apellidos=datos.apellidos,
        correo=str(datos.correo),
        contrasena=datos.contrasena
    )

    if usuario is None:
        raise HTTPException(
            status_code=400,
            detail="El correo electrónico ya está registrado."
        )

    return {
        "mensaje": "Usuario registrado correctamente.",
        "usuario": {
            "id": usuario.id,
            "nombres": usuario.nombres,
            "apellidos": usuario.apellidos,
            "correo": usuario.correo
        }
    }


# ==========================================
# INICIO DE SESIÓN
# ==========================================

@router.post("/login")
def login(
    datos: LoginRequest,
    db: Session = Depends(obtener_db)
):
    usuario = iniciar_sesion(
        db=db,
        correo=str(datos.correo),
        contrasena=datos.contrasena
    )

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos."
        )

    token = crear_token_acceso({
        "sub": str(usuario.id),
        "correo": usuario.correo
    })

    return {
        "mensaje": "Inicio de sesión exitoso.",
        "tipo_token": "bearer",
        "access_token": token,
        "usuario": {
            "id": usuario.id,
            "nombres": usuario.nombres,
            "apellidos": usuario.apellidos,
            "correo": usuario.correo
        }
    }


# ==========================================
# RUTA PRIVADA: PERFIL DEL USUARIO
# ==========================================

@router.get("/perfil")
def obtener_perfil(
    usuario=Depends(obtener_usuario_actual)
):
    return {
        "mensaje": "Acceso autorizado.",
        "usuario": {
            "id": usuario.id,
            "nombres": usuario.nombres,
            "apellidos": usuario.apellidos,
            "correo": usuario.correo
        }
    }
