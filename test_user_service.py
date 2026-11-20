from backend.app.database.connection import SessionLocal

from backend.app.services.user_service import (
    iniciar_sesion
)


# ==========================================
# PRUEBA DEL INICIO DE SESIÓN
# ==========================================

db = SessionLocal()

try:
    correo = "prueba@talentbot.com"
    contrasena = "TalentBot123*"

    # Intentar iniciar sesión
    usuario = iniciar_sesion(
        db=db,
        correo=correo,
        contrasena=contrasena
    )

    if usuario:
        print("Inicio de sesión exitoso.")
        print("Bienvenido:", usuario.nombres, usuario.apellidos)
    else:
        print("Correo o contraseña incorrectos.")

finally:
    db.close()
