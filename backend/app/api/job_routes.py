import json

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

from backend.app.services.job_recommender import (
    recomendar_ofertas,
    OFERTAS_LABORALES
)

from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db

from backend.app.database.models import (
    HojaVida,
    AnalisisCV,
    OfertaLaboral,
    RecomendacionLaboral
)


router = APIRouter(
    prefix="/ofertas",
    tags=["Recomendaciones laborales"]
)


# ==========================================
# GENERAR RECOMENDACIONES LABORALES
# ==========================================

@router.post("/recomendar")
def obtener_recomendaciones(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db)
):
    """
    Obtiene las habilidades del último análisis del usuario,
    compara las ofertas laborales y guarda las recomendaciones.
    """

    hoja_vida = (
        db.query(HojaVida)
        .filter(HojaVida.id_usuario == usuario.id)
        .order_by(HojaVida.fecha_subida.desc())
        .first()
    )

    if hoja_vida is None:
        raise HTTPException(
            status_code=404,
            detail="No tienes hojas de vida registradas."
        )

    analisis = (
        db.query(AnalisisCV)
        .filter(AnalisisCV.id_hoja_vida == hoja_vida.id)
        .order_by(AnalisisCV.fecha_analisis.desc())
        .first()
    )

    if analisis is None or not analisis.habilidades:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron habilidades para recomendar ofertas."
        )

    habilidades_candidato = json.loads(analisis.habilidades)

    recomendaciones = recomendar_ofertas(habilidades_candidato)

    # Catálogo de ofertas organizado por su identificador
    ofertas_catalogo = {
        oferta["id"]: oferta
        for oferta in OFERTAS_LABORALES
    }

    try:
        for recomendacion in recomendaciones:

            oferta = db.query(OfertaLaboral).filter(
                OfertaLaboral.cargo == recomendacion["cargo"],
                OfertaLaboral.empresa == recomendacion["empresa"]
            ).first()

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
                        ensure_ascii=False
                    )
                )

                db.add(oferta)
                db.flush()

            nueva_recomendacion = RecomendacionLaboral(
                porcentaje_compatibilidad=recomendacion[
                    "porcentaje_compatibilidad"
                ],
                habilidades_coincidentes=json.dumps(
                    recomendacion["habilidades_coincidentes"],
                    ensure_ascii=False
                ),
                habilidades_faltantes=json.dumps(
                    recomendacion["habilidades_faltantes"],
                    ensure_ascii=False
                ),
                id_usuario=usuario.id,
                id_oferta=oferta.id
            )

            db.add(nueva_recomendacion)

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="No fue posible guardar las recomendaciones."
        )

    return {
        "mensaje": "Recomendaciones generadas y guardadas correctamente.",
        "usuario": usuario.id,
        "total_ofertas": len(recomendaciones),
        "habilidades_candidato": habilidades_candidato,
        "recomendaciones": recomendaciones,
        "estado": "Recomendaciones generadas correctamente"
    }


# ==========================================
# CONSULTAR HISTORIAL DE RECOMENDACIONES
# ==========================================

@router.get("/historial")
def obtener_historial_recomendaciones(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db)
):
    """
    Consulta las recomendaciones laborales guardadas
    para el usuario que inició sesión.
    """

    historial = (
        db.query(RecomendacionLaboral)
        .options(joinedload(RecomendacionLaboral.oferta))
        .filter(
            RecomendacionLaboral.id_usuario == usuario.id
        )
        .order_by(
            RecomendacionLaboral.fecha_recomendacion.desc()
        )
        .all()
    )

    recomendaciones = []

    for item in historial:
        oferta = item.oferta

        recomendaciones.append({
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
            "fecha_recomendacion": item.fecha_recomendacion
        })

    return {
        "mensaje": "Historial consultado correctamente.",
        "usuario": usuario.id,
        "total_recomendaciones": len(recomendaciones),
        "historial": recomendaciones
    }
