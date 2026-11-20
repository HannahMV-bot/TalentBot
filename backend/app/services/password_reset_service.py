import secrets
import hashlib
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.database.models import (
    RecuperacionContrasena,
    Usuario
)
from backend.app.services.user_service import buscar_usuario_por_correo
from backend.app.services.security import encriptar_contrasena


# ==========================================
# CONFIGURACIÓN
# ==========================================

DURACION_CODIGO_MINUTOS = 10
MAX_INTENTOS = 5


# ==========================================
# GENERAR CÓDIGO DE RECUPERACIÓN
# ==========================================

def generar_codigo():
    return f"{secrets.randbelow(1_000_000):06d}"


# ==========================================
# PROTEGER CÓDIGO
# ==========================================

def proteger_codigo(codigo: str):
    return hashlib.sha256(codigo.encode()).hexdigest()


# ==========================================
# CREAR SOLICITUD DE RECUPERACIÓN
# ==========================================

def crear_solicitud_recuperacion(db: Session, correo: str):
    usuario = buscar_usuario_por_correo(db, correo)

    if not usuario:
        return None

    # Invalidar códigos anteriores
    db.query(RecuperacionContrasena).filter(
        RecuperacionContrasena.id_usuario == usuario.id,
        RecuperacionContrasena.utilizado == 0
    ).update({"utilizado": 1})

    codigo = generar_codigo()

    recuperacion = RecuperacionContrasena(
        id_usuario=usuario.id,
        codigo_hash=proteger_codigo(codigo),
        fecha_expiracion=datetime.utcnow() + timedelta(
            minutes=DURACION_CODIGO_MINUTOS
        ),
        utilizado=0,
        intentos=0
    )

    db.add(recuperacion)
    db.commit()

    return codigo


# ==========================================
# VERIFICAR CÓDIGO
# ==========================================

def verificar_codigo_recuperacion(
    db: Session,
    correo: str,
    codigo: str
):
    usuario = buscar_usuario_por_correo(db, correo)

    if not usuario:
        return None

    recuperacion = db.query(RecuperacionContrasena).filter(
        RecuperacionContrasena.id_usuario == usuario.id,
        RecuperacionContrasena.utilizado == 0
    ).order_by(
        RecuperacionContrasena.fecha_creacion.desc()
    ).first()

    if not recuperacion:
        return None

    if datetime.utcnow() > recuperacion.fecha_expiracion:
        recuperacion.utilizado = 1
        db.commit()
        return None

    if recuperacion.intentos >= MAX_INTENTOS:
        recuperacion.utilizado = 1
        db.commit()
        return None

    recuperacion.intentos += 1

    if proteger_codigo(codigo) != recuperacion.codigo_hash:
        db.commit()
        return None

    db.commit()

    return recuperacion


# ==========================================
# CAMBIAR CONTRASEÑA
# ==========================================


def cambiar_contrasena(
    db: Session,
    recuperacion: RecuperacionContrasena,
    nueva_contrasena: str
):
    usuario = db.query(Usuario).filter(
        Usuario.id == recuperacion.id_usuario
    ).first()

    if not usuario:
        return False

    # Proteger la nueva contraseña con Argon2
    usuario.contrasena = encriptar_contrasena(nueva_contrasena)

    # Invalidar el código utilizado
    recuperacion.utilizado = 1

    db.commit()

    return True
