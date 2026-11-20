from backend.app.database.connection import SessionLocal
from backend.app.services.user_service import iniciar_sesion


def test_iniciar_sesion_credenciales_incorrectas():
    db = SessionLocal()

    try:
        # Intentar iniciar sesión con un correo inexistente
        usuario = iniciar_sesion(
            db=db,
            correo="correo_inexistente@talentbot.com",
            contrasena="ClaveIncorrecta123*"
        )

        # No debe permitir el acceso
        assert usuario is None

    finally:
        db.close()
