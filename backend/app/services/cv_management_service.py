import json

from sqlalchemy.orm import Session, joinedload

from backend.app.database.models import AnalisisCV, HojaVida
from backend.app.services.cv_analyzer import analizar_hoja_vida


class CVManagementError(Exception):
    """Error de negocio para gestión de hojas de vida."""


def analizar_y_guardar_cv(db: Session, usuario, nombre_archivo: str, contenido: bytes) -> dict:
    """Analiza una hoja de vida PDF y guarda los resultados para el usuario."""
    if not nombre_archivo or not nombre_archivo.lower().endswith(".pdf"):
        raise CVManagementError("El archivo debe tener formato PDF.")

    if not contenido:
        raise CVManagementError("El archivo PDF está vacío.")

    try:
        resultado = analizar_hoja_vida(contenido)

        nueva_hoja_vida = HojaVida(
            nombre_archivo=nombre_archivo,
            id_usuario=usuario.id,
        )
        db.add(nueva_hoja_vida)
        db.flush()

        nuevo_analisis = AnalisisCV(
            habilidades=json.dumps(
                resultado["habilidades_detectadas"],
                ensure_ascii=False,
            ),
            perfil_profesional=json.dumps(
                resultado["perfil_profesional"],
                ensure_ascii=False,
            ),
            id_hoja_vida=nueva_hoja_vida.id,
        )

        db.add(nuevo_analisis)
        db.commit()
        db.refresh(nueva_hoja_vida)
        db.refresh(nuevo_analisis)

        return {
            "mensaje": "Hoja de vida analizada y guardada correctamente.",
            "usuario": usuario.id,
            "id_hoja_vida": nueva_hoja_vida.id,
            "id_analisis": nuevo_analisis.id,
            "nombre_archivo": nombre_archivo,
            "analisis": resultado,
        }

    except CVManagementError:
        db.rollback()
        raise
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def obtener_historial_cv(db: Session, usuario) -> dict:
    """Obtiene el historial de análisis de hojas de vida del usuario."""
    hojas_vida = (
        db.query(HojaVida)
        .options(joinedload(HojaVida.analisis))
        .filter(HojaVida.id_usuario == usuario.id)
        .order_by(HojaVida.fecha_subida.desc())
        .all()
    )

    historial = []
    for hoja in hojas_vida:
        analisis = []
        for resultado in hoja.analisis:
            analisis.append(
                {
                    "id_analisis": resultado.id,
                    "habilidades": json.loads(resultado.habilidades)
                    if resultado.habilidades
                    else [],
                    "perfil_profesional": json.loads(resultado.perfil_profesional)
                    if resultado.perfil_profesional
                    else None,
                    "fecha_analisis": resultado.fecha_analisis,
                }
            )

        historial.append(
            {
                "id_hoja_vida": hoja.id,
                "nombre_archivo": hoja.nombre_archivo,
                "fecha_subida": hoja.fecha_subida,
                "analisis": analisis,
            }
        )

    return {
        "mensaje": "Historial consultado correctamente.",
        "usuario": usuario.id,
        "total_hojas_vida": len(historial),
        "historial": historial,
    }


def obtener_ultimo_analisis_cv(db: Session, usuario):
    """Obtiene el último análisis de CV del usuario, si existe."""
    hoja_vida = (
        db.query(HojaVida)
        .filter(HojaVida.id_usuario == usuario.id)
        .order_by(HojaVida.fecha_subida.desc())
        .first()
    )
    if hoja_vida is None:
        return None, None

    analisis = (
        db.query(AnalisisCV)
        .filter(AnalisisCV.id_hoja_vida == hoja_vida.id)
        .order_by(AnalisisCV.fecha_analisis.desc())
        .first()
    )
    return hoja_vida, analisis
