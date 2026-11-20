from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db
from backend.app.services.interview_management_service import (
    InterviewManagementError,
    generar_y_guardar_entrevista,
    obtener_historial_entrevistas as obtener_historial_entrevistas_service,
)


router = APIRouter(
    prefix="/entrevistas",
    tags=["Simulador de entrevistas"],
)


# ==========================================
# MODELO DE DATOS
# ==========================================

class EntrevistaRequest(BaseModel):
    perfil: str


# ==========================================
# GENERAR Y GUARDAR ENTREVISTA
# ==========================================

@router.post("/generar-preguntas")
def obtener_preguntas(
    datos: EntrevistaRequest,
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    try:
        return generar_y_guardar_entrevista(
            db=db,
            usuario=usuario,
            perfil=datos.perfil,
        )
    except InterviewManagementError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


# ==========================================
# HISTORIAL DE ENTREVISTAS
# ==========================================

@router.get("/historial")
def obtener_historial_entrevistas(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    """
    Consulta las entrevistas y sus respuestas
    del usuario autenticado.
    """
    return obtener_historial_entrevistas_service(db=db, usuario=usuario)
