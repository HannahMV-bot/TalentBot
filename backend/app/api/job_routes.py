from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies import obtener_usuario_actual
from backend.app.database.connection import obtener_db
from backend.app.services.job_management_service import (
    JobManagementError,
    generar_y_guardar_recomendaciones,
    obtener_historial_recomendaciones as obtener_historial_recomendaciones_service,
)


router = APIRouter(
    prefix="/ofertas",
    tags=["Recomendaciones laborales"],
)


# ==========================================
# GENERAR RECOMENDACIONES LABORALES
# ==========================================

@router.post("/recomendar")
def obtener_recomendaciones(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    """
    Obtiene las habilidades del último análisis del usuario,
    compara las ofertas laborales y guarda las recomendaciones.
    """
    try:
        return generar_y_guardar_recomendaciones(db=db, usuario=usuario)
    except JobManagementError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


# ==========================================
# CONSULTAR HISTORIAL DE RECOMENDACIONES
# ==========================================

@router.get("/historial")
def obtener_historial_recomendaciones(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    """
    Consulta las recomendaciones laborales guardadas
    para el usuario que inició sesión.
    """
    return obtener_historial_recomendaciones_service(db=db, usuario=usuario)
