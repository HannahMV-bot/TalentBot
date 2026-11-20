from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from backend.app.services.interview_simulator import generar_preguntas
from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db

from backend.app.database.models import (
    Entrevista,
    RespuestaEntrevista
)


router = APIRouter(
    prefix="/entrevistas",
    tags=["Simulador de entrevistas"]
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
    db: Session = Depends(obtener_db)
):
    if not datos.perfil.strip():
        raise HTTPException(
            status_code=400,
            detail="Debes proporcionar un perfil profesional."
        )

    resultado = generar_preguntas(datos.perfil.strip())

    if not resultado["preguntas"]:
        raise HTTPException(
            status_code=404,
            detail=resultado["estado"]
        )

    nueva_entrevista = Entrevista(
        perfil=resultado["perfil"],
        id_usuario=usuario.id
    )

    try:
        db.add(nueva_entrevista)
        db.commit()
        db.refresh(nueva_entrevista)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No fue posible guardar la entrevista."
        )

    return {
        "mensaje": "Entrevista generada y guardada correctamente.",
        "id_entrevista": nueva_entrevista.id,
        "usuario": usuario.id,
        "perfil": resultado["perfil"],
        "total_preguntas": resultado["total_preguntas"],
        "preguntas": resultado["preguntas"],
        "estado": resultado["estado"]
    }


# ==========================================
# HISTORIAL DE ENTREVISTAS
# ==========================================

@router.get("/historial")
def obtener_historial_entrevistas(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db)
):
    """
    Consulta las entrevistas y sus respuestas
    del usuario autenticado.
    """

    entrevistas = (
        db.query(Entrevista)
        .options(joinedload(Entrevista.respuestas))
        .filter(Entrevista.id_usuario == usuario.id)
        .order_by(Entrevista.fecha.desc())
        .all()
    )

    historial = []

    for entrevista in entrevistas:
        respuestas = []

        for respuesta in entrevista.respuestas:
            respuestas.append({
                "id_respuesta": respuesta.id,
                "pregunta": respuesta.pregunta,
                "respuesta": respuesta.respuesta,
                "puntuacion": respuesta.puntuacion,
                "retroalimentacion": respuesta.retroalimentacion
            })

        historial.append({
            "id_entrevista": entrevista.id,
            "perfil": entrevista.perfil,
            "fecha": entrevista.fecha,
            "total_respuestas": len(respuestas),
            "respuestas": respuestas
        })

    return {
        "mensaje": "Historial de entrevistas consultado correctamente.",
        "usuario": usuario.id,
        "total_entrevistas": len(historial),
        "historial": historial
    }
