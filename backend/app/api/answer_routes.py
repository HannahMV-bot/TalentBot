from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db
from backend.app.services.interview_management_service import (
    InterviewManagementError,
    evaluar_y_guardar_respuesta,
)


router = APIRouter(
    prefix="/entrevistas",
    tags=["Evaluación de respuestas"],
)


# ==========================================
# MODELO DE DATOS
# ==========================================

class RespuestaRequest(BaseModel):
    id_entrevista: int
    pregunta: str
    respuesta: str


# ==========================================
# EVALUAR Y GUARDAR RESPUESTA
# ==========================================

@router.post("/evaluar-respuesta")
def evaluar_respuesta_entrevista(
    datos: RespuestaRequest,
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    """
    Evalúa una respuesta y la guarda en la entrevista
    del usuario autenticado.
    """
    try:
        return evaluar_y_guardar_respuesta(
            db=db,
            usuario=usuario,
            id_entrevista=datos.id_entrevista,
            pregunta=datos.pregunta,
            respuesta=datos.respuesta,
        )
    except InterviewManagementError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error
