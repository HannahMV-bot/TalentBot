from contextlib import contextmanager

from telegram import Update
from telegram.ext import ContextTypes

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Usuario
from backend.app.services.telegram_account_service import obtener_usuario_por_telegram_id

AUTH_USER_ID_KEY = "auth_user_id"


@contextmanager
def db_session():
    """Proporciona una sesión de base de datos y garantiza su cierre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def es_chat_privado(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type == "private")


def establecer_sesion_activa(context: ContextTypes.DEFAULT_TYPE, usuario_id: int) -> None:
    context.user_data[AUTH_USER_ID_KEY] = usuario_id


def limpiar_sesion_activa(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(AUTH_USER_ID_KEY, None)


def obtener_id_usuario_autenticado(context: ContextTypes.DEFAULT_TYPE):
    return context.user_data.get(AUTH_USER_ID_KEY)


def esta_autenticado(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return obtener_id_usuario_autenticado(context) is not None


def obtener_usuario_autenticado(db, context: ContextTypes.DEFAULT_TYPE, telegram_id: int):
    """Obtiene el usuario autenticado en sesión activa y valida su pertenencia al Telegram."""
    usuario_id = obtener_id_usuario_autenticado(context)
    if not usuario_id:
        return None

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        limpiar_sesion_activa(context)
        return None

    usuario_vinculado = obtener_usuario_por_telegram_id(db, telegram_id)
    if not usuario_vinculado or usuario_vinculado.id != usuario.id:
        # La sesión activa no corresponde al vínculo actual del Telegram: se invalida.
        limpiar_sesion_activa(context)
        return None

    return usuario
