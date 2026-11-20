from sqlalchemy.orm import Session

from backend.app.database.models import Usuario

from backend.app.services.security import (
    encriptar_contrasena,
    verificar_contrasena
)


def buscar_usuario_por_correo(db: Session, correo: str):
    """
    Busca un usuario utilizando su correo electrónico.
    """

    return db.query(Usuario).filter(
        Usuario.correo == correo
    ).first()


def registrar_usuario(
    db: Session,
    nombres: str,
    apellidos: str,
    correo: str,
    contrasena: str
):
    """
    Registra un usuario con su contraseña protegida.
    """

    usuario_existente = buscar_usuario_por_correo(
        db,
        correo
    )

    if usuario_existente:
        return None

    # Generar hash seguro de la contraseña
    contrasena_segura = encriptar_contrasena(contrasena)

    nuevo_usuario = Usuario(
        nombres=nombres,
        apellidos=apellidos,
        correo=correo,
        contrasena=contrasena_segura
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return nuevo_usuario


def iniciar_sesion(
    db: Session,
    correo: str,
    contrasena: str
):
    """
    Verifica las credenciales de un usuario.
    """

    # Buscar el usuario por correo
    usuario = buscar_usuario_por_correo(
        db,
        correo
    )

    if not usuario:
        return None

    # Verificar la contraseña
    contrasena_valida = verificar_contrasena(
        contrasena,
        usuario.contrasena
    )

    if not contrasena_valida:
        return None

    return usuario
