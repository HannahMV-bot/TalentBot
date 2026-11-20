import json

from sqlalchemy.orm import Session, joinedload

from backend.app.database.models import AnalisisCV, HojaVida, OfertaLaboral, RecomendacionLaboral
from backend.app.services.job_recommender import OFERTAS_LABORALES, recomendar_ofertas


class JobManagementError(Exception):
    """Error de negocio para recomendaciones laborales."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def generar_y_guardar_recomendaciones(db: Session, usuario) -> dict:
    """Genera recomendaciones basadas en el último análisis del usuario y las guarda."""
    hoja_vida = (
        db.query(HojaVida)
        .filter(HojaVida.id_usuario == usuario.id)
        .order_by(HojaVida.fecha_subida.desc())
        .first()
    )

    if hoja_vida is None:
        raise JobManagementError("No tienes hojas de vida registradas.", status_code=404)

    analisis = (
        db.query(AnalisisCV)
        .filter(AnalisisCV.id_hoja_vida == hoja_vida.id)
        .order_by(AnalisisCV.fecha_analisis.desc())
        .first()
    )

    if analisis is None or not analisis.habilidades:
        raise JobManagementError(
            "No se encontraron habilidades para recomendar ofertas.",
            status_code=404,
        )

    habilidades_candidato = json.loads(analisis.habilidades)
    recomendaciones = recomendar_ofertas(habilidades_candidato)

    ofertas_catalogo = {oferta["id"]: oferta for oferta in OFERTAS_LABORALES}

    try:
        for recomendacion in recomendaciones:
            oferta = (
                db.query(OfertaLaboral)
                .filter(
                    OfertaLaboral.cargo == recomendacion["cargo"],
                    OfertaLaboral.empresa == recomendacion["empresa"],
                )
                .first()
            )

            if oferta is None:
                datos_oferta = ofertas_catalogo.get(recomendacion["id"])
                if datos_oferta is None:
                    raise ValueError("No se encontró la oferta en el catálogo.")

                oferta = OfertaLaboral(
                    cargo=recomendacion["cargo"],
                    empresa=recomendacion["empresa"],
                    modalidad=recomendacion["modalidad"],
                    habilidades=json.dumps(
                        datos_oferta["habilidades"],
                        ensure_ascii=False,
                    ),
                )
                db.add(oferta)
                db.flush()

            nueva_recomendacion = RecomendacionLaboral(
                porcentaje_compatibilidad=recomendacion["porcentaje_compatibilidad"],
                habilidades_coincidentes=json.dumps(
                    recomendacion["habilidades_coincidentes"],
                    ensure_ascii=False,
                ),
                habilidades_faltantes=json.dumps(
                    recomendacion["habilidades_faltantes"],
                    ensure_ascii=False,
                ),
                id_usuario=usuario.id,
                id_oferta=oferta.id,
            )
            db.add(nueva_recomendacion)

        db.commit()

    except JobManagementError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise JobManagementError(
            "No fue posible guardar las recomendaciones.",
            status_code=500,
        )

    return {
        "mensaje": "Recomendaciones generadas y guardadas correctamente.",
        "usuario": usuario.id,
        "total_ofertas": len(recomendaciones),
        "habilidades_candidato": habilidades_candidato,
        "recomendaciones": recomendaciones,
        "estado": "Recomendaciones generadas correctamente",
    }


def obtener_historial_recomendaciones(db: Session, usuario) -> dict:
    """Consulta las recomendaciones laborales guardadas del usuario."""
    historial = (
        db.query(RecomendacionLaboral)
        .options(joinedload(RecomendacionLaboral.oferta))
        .filter(RecomendacionLaboral.id_usuario == usuario.id)
        .order_by(RecomendacionLaboral.fecha_recomendacion.desc())
        .all()
    )

    recomendaciones = []
    for item in historial:
        oferta = item.oferta
        recomendaciones.append(
            {
                "id_recomendacion": item.id,
                "id_oferta": item.id_oferta,
                "cargo": oferta.cargo,
                "empresa": oferta.empresa,
                "modalidad": oferta.modalidad,
                "porcentaje_compatibilidad": item.porcentaje_compatibilidad,
                "habilidades_coincidentes": json.loads(
                    item.habilidades_coincidentes or "[]"
                ),
                "habilidades_faltantes": json.loads(
                    item.habilidades_faltantes or "[]"
                ),
                "fecha_recomendacion": item.fecha_recomendacion,
            }
        )

    return {
        "mensaje": "Historial consultado correctamente.",
        "usuario": usuario.id,
        "total_recomendaciones": len(recomendaciones),
        "historial": recomendaciones,
    }
