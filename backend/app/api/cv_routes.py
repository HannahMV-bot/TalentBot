import json

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from sqlalchemy.orm import Session, joinedload

from backend.app.services.cv_analyzer import analizar_hoja_vida
from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db
from backend.app.database.models import HojaVida, AnalisisCV


# ==========================================
# CONFIGURACIÓN DEL ENRUTADOR
# ==========================================

router = APIRouter(
    prefix="/hojas-de-vida",
    tags=["Análisis de hojas de vida"]
)


# ==========================================
# ANALIZAR Y GUARDAR HOJA DE VIDA
# ==========================================

@router.post("/analizar")
async def analizar_cv(
    archivo: UploadFile = File(...),
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db)
):
    """
    Recibe una hoja de vida PDF, analiza sus habilidades
    y guarda los resultados asociados al usuario autenticado.
    """

    # Validar que sea un archivo PDF
    if not archivo.filename or not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe tener formato PDF."
        )

    try:
        # Leer el contenido del archivo
        contenido = await archivo.read()

        # Validar que el archivo no esté vacío
        if not contenido:
            raise HTTPException(
                status_code=400,
                detail="El archivo PDF está vacío."
            )

        # Analizar la hoja de vida
        resultado = analizar_hoja_vida(contenido)

        # Guardar la hoja de vida
        nueva_hoja_vida = HojaVida(
            nombre_archivo=archivo.filename,
            id_usuario=usuario.id
        )

        db.add(nueva_hoja_vida)
        db.flush()

        # Guardar los resultados del análisis
        nuevo_analisis = AnalisisCV(
            habilidades=json.dumps(
                resultado["habilidades_detectadas"],
                ensure_ascii=False
            ),
            perfil_profesional=json.dumps(
                resultado["perfil_profesional"],
                ensure_ascii=False
            ),
            id_hoja_vida=nueva_hoja_vida.id
        )

        db.add(nuevo_analisis)
        db.commit()

        # Actualizar los registros guardados
        db.refresh(nueva_hoja_vida)
        db.refresh(nuevo_analisis)

        return {
            "mensaje": "Hoja de vida analizada y guardada correctamente.",
            "usuario": usuario.id,
            "id_hoja_vida": nueva_hoja_vida.id,
            "id_analisis": nuevo_analisis.id,
            "nombre_archivo": archivo.filename,
            "analisis": resultado
        }

    except ValueError as error:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error al guardar el análisis."
        )

    finally:
        await archivo.close()


# ==========================================
# CONSULTAR HISTORIAL DE HOJAS DE VIDA
# ==========================================

@router.get("/historial")
def obtener_historial(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db)
):
    """
    Obtiene el historial de análisis del usuario autenticado.
    """

    # Consultar las hojas de vida del usuario
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
            analisis.append({
                "id_analisis": resultado.id,

                "habilidades": json.loads(
                    resultado.habilidades
                ) if resultado.habilidades else [],

                "perfil_profesional": json.loads(
                    resultado.perfil_profesional
                ) if resultado.perfil_profesional else None,

                "fecha_analisis": resultado.fecha_analisis
            })

        historial.append({
            "id_hoja_vida": hoja.id,
            "nombre_archivo": hoja.nombre_archivo,
            "fecha_subida": hoja.fecha_subida,
            "analisis": analisis
        })

    return {
        "mensaje": "Historial consultado correctamente.",
        "usuario": usuario.id,
        "total_hojas_vida": len(historial),
        "historial": historial
    }
