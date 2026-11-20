from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.services.answer_evaluator import evaluar_respuesta
from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db

from backend.app.database.models import (
    Entrevista,
    RespuestaEntrevista
)


router = APIRouter(
    prefix="/entrevistas",
    tags=["Evaluación de respuestas"]
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
    db: Session = Depends(obtener_db)
):
    """
    Evalúa una respuesta y la guarda en la entrevista
    del usuario autenticado.
    """

    entrevista = db.query(Entrevista).filter(
        Entrevista.id == datos.id_entrevista,
        Entrevista.id_usuario == usuario.id
    ).first()

    if entrevista is None:
        raise HTTPException(
            status_code=404,
            detail="La entrevista no existe o no te pertenece."
        )

    if not datos.pregunta.strip():
        raise HTTPException(
            status_code=400,
            detail="Debes proporcionar la pregunta."
        )

    resultado = evaluar_respuesta(
        datos.pregunta,
        datos.respuesta
    )

    if resultado["estado"] != "Evaluacion completada":
        raise HTTPException(
            status_code=400,
            detail=resultado["retroalimentacion"]
        )

    nueva_respuesta = RespuestaEntrevista(
        pregunta=datos.pregunta,
        respuesta=datos.respuesta,
        puntuacion=resultado["puntuacion"],
        retroalimentacion=resultado["retroalimentacion"],
        id_entrevista=entrevista.id
    )

    try:
        db.add(nueva_respuesta)
        db.commit()
        db.refresh(nueva_respuesta)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No fue posible guardar la respuesta."
        )

    return {
        "mensaje": "Respuesta evaluada y guardada correctamente.",
        "id_respuesta": nueva_respuesta.id,
        "id_entrevista": entrevista.id,
        "usuario": usuario.id,
        "pregunta": datos.pregunta,
        "respuesta": datos.respuesta,
        "puntuacion": resultado["puntuacion"],
        "retroalimentacion": resultado["retroalimentacion"],
        "estado": resultado["estado"]
    }
