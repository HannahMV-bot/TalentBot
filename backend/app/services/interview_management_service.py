from sqlalchemy.orm import Session, joinedload

from backend.app.database.models import Entrevista, RespuestaEntrevista
from backend.app.services.answer_evaluator import evaluar_respuesta
from backend.app.services.interview_simulator import generar_preguntas


class InterviewManagementError(Exception):
    """Error de negocio para entrevistas y respuestas."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def generar_y_guardar_entrevista(db: Session, usuario, perfil: str) -> dict:
    """Genera preguntas para un perfil y guarda la entrevista del usuario."""
    if not perfil or not perfil.strip():
        raise InterviewManagementError(
            "Debes proporcionar un perfil profesional.",
            status_code=400,
        )

    resultado = generar_preguntas(perfil.strip())

    if not resultado["preguntas"]:
        raise InterviewManagementError(resultado["estado"], status_code=404)

    nueva_entrevista = Entrevista(
        perfil=resultado["perfil"],
        id_usuario=usuario.id,
    )

    try:
        db.add(nueva_entrevista)
        db.commit()
        db.refresh(nueva_entrevista)
    except Exception:
        db.rollback()
        raise InterviewManagementError(
            "No fue posible guardar la entrevista.",
            status_code=500,
        )

    return {
        "mensaje": "Entrevista generada y guardada correctamente.",
        "id_entrevista": nueva_entrevista.id,
        "usuario": usuario.id,
        "perfil": resultado["perfil"],
        "total_preguntas": resultado["total_preguntas"],
        "preguntas": resultado["preguntas"],
        "estado": resultado["estado"],
    }


def obtener_historial_entrevistas(db: Session, usuario) -> dict:
    """Consulta las entrevistas y respuestas del usuario."""
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
        respuestas_ordenadas = sorted(
            entrevista.respuestas,
            key=lambda respuesta: (
                respuesta.id is None,
                respuesta.id if respuesta.id is not None else 0,
            ),
        )
        for respuesta in respuestas_ordenadas:
            respuestas.append(
                {
                    "id_respuesta": respuesta.id,
                    "pregunta": respuesta.pregunta,
                    "respuesta": respuesta.respuesta,
                    "puntuacion": respuesta.puntuacion,
                    "retroalimentacion": respuesta.retroalimentacion,
                }
            )

        historial.append(
            {
                "id_entrevista": entrevista.id,
                "perfil": entrevista.perfil,
                "fecha": entrevista.fecha,
                "total_respuestas": len(respuestas),
                "respuestas": respuestas,
            }
        )

    return {
        "mensaje": "Historial de entrevistas consultado correctamente.",
        "usuario": usuario.id,
        "total_entrevistas": len(historial),
        "historial": historial,
    }


def evaluar_y_guardar_respuesta(
    db: Session,
    usuario,
    id_entrevista: int,
    pregunta: str,
    respuesta: str,
    guardar_no_reconocida: bool = False,
) -> dict:
    """Evalúa una respuesta y la guarda en la entrevista del usuario."""
    entrevista = (
        db.query(Entrevista)
        .filter(
            Entrevista.id == id_entrevista,
            Entrevista.id_usuario == usuario.id,
        )
        .first()
    )

    if entrevista is None:
        raise InterviewManagementError(
            "La entrevista no existe o no te pertenece.",
            status_code=404,
        )

    if not pregunta or not pregunta.strip():
        raise InterviewManagementError(
            "Debes proporcionar la pregunta.",
            status_code=400,
        )

    resultado = evaluar_respuesta(pregunta, respuesta)

    estado = resultado.get("estado")
    if estado == "Pregunta no reconocida":
        if not guardar_no_reconocida:
            raise InterviewManagementError(
                resultado.get("retroalimentacion")
                or "No existen criterios suficientes para evaluar esta pregunta.",
                status_code=422,
            )
        puntuacion = None
        retroalimentacion = (
            resultado.get("retroalimentacion")
            or "No existen criterios suficientes para evaluar esta pregunta."
        )
        mensaje = "Respuesta guardada. Esta pregunta no pudo ser evaluada automáticamente."
    else:
        puntuacion = resultado.get("puntuacion")
        retroalimentacion = resultado.get("retroalimentacion")
        mensaje = "Respuesta evaluada y guardada correctamente."

    nueva_respuesta = RespuestaEntrevista(
        pregunta=pregunta,
        respuesta=respuesta,
        puntuacion=puntuacion,
        retroalimentacion=retroalimentacion,
        id_entrevista=entrevista.id,
    )


    try:
        db.add(nueva_respuesta)
        db.commit()
        db.refresh(nueva_respuesta)
    except Exception:
        db.rollback()
        raise InterviewManagementError(
            "No fue posible guardar la respuesta.",
            status_code=500,
        )

    return {
        "mensaje": mensaje,
        "id_respuesta": nueva_respuesta.id,
        "id_entrevista": entrevista.id,
        "usuario": usuario.id,
        "pregunta": pregunta,
        "respuesta": respuesta,
        "puntuacion": puntuacion,
        "retroalimentacion": retroalimentacion,
        "estado": estado,
    }
