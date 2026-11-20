from fastapi import FastAPI

from backend.app.api.cv_routes import router as cv_router
from backend.app.api.job_routes import router as job_router
from backend.app.api.interview_routes import router as interview_router
from backend.app.api.answer_routes import router as answer_router
from backend.app.api.auth_routes import router as auth_router

# Crear la aplicación principal
app = FastAPI(
    title="TalentBot API",
    description="Asistente inteligente de orientación laboral",
    version="1.0.0"
)

# Registrar las rutas de hojas de vida
app.include_router(cv_router)
app.include_router(job_router)
app.include_router(interview_router)
app.include_router(answer_router)
app.include_router(auth_router)

# Ruta principal
@app.get("/")
def inicio():
    return {
        "mensaje": "¡Bienvenido a TalentBot!",
        "descripcion": "Tu asistente inteligente de orientación laboral.",
        "estado": "Funcionando correctamente"
    }


# Ruta para consultar el estado
@app.get("/estado")
def estado():
    return {
        "proyecto": "TalentBot",
        "estado": "Activo",
        "version": "1.0.0"
    }
