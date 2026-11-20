from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db
from backend.app.services.cv_management_service import (
    CVManagementError,
    analizar_y_guardar_cv,
    obtener_historial_cv,
)


# ==========================================
# CONFIGURACIÓN DEL ENRUTADOR
# ==========================================

router = APIRouter(
    prefix="/hojas-de-vida",
    tags=["Análisis de hojas de vida"],
)


# ==========================================
# ANALIZAR Y GUARDAR HOJA DE VIDA
# ==========================================

@router.post("/analizar")
async def analizar_cv(
    archivo: UploadFile = File(...),
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    """
    Recibe una hoja de vida PDF, analiza sus habilidades
    y guarda los resultados asociados al usuario autenticado.
    """
    try:
        contenido = await archivo.read()
        return analizar_y_guardar_cv(
            db=db,
            usuario=usuario,
            nombre_archivo=archivo.filename or "",
            contenido=contenido,
        )

    except CVManagementError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error al guardar el análisis.",
        )

    finally:
        await archivo.close()


# ==========================================
# CONSULTAR HISTORIAL DE HOJAS DE VIDA
# ==========================================

@router.get("/historial")
def obtener_historial(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    """
    Obtiene el historial de análisis del usuario autenticado.
    """
    return obtener_historial_cv(db=db, usuario=usuario)
