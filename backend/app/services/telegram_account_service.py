from sqlalchemy.orm import Session

from backend.app.database.models import CuentaTelegram, Usuario


class TelegramLinkError(Exception):
    """Error de negocio para la vinculación de cuentas de Telegram."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def obtener_vinculo_por_telegram_id(db: Session, telegram_id: int):
    """Obtiene la vinculación asociada a un identificador de Telegram."""
    return (
        db.query(CuentaTelegram)
        .filter(CuentaTelegram.telegram_id == telegram_id)
        .first()
    )


def obtener_vinculo_por_usuario_id(db: Session, id_usuario: int):
    """Obtiene la vinculación asociada a un usuario."""
    return (
        db.query(CuentaTelegram)
        .filter(CuentaTelegram.id_usuario == id_usuario)
        .first()
    )


def obtener_usuario_por_telegram_id(db: Session, telegram_id: int):
    """Obtiene el usuario vinculado a un identificador de Telegram."""
    vinculo = obtener_vinculo_por_telegram_id(db, telegram_id)
    if not vinculo:
        return None
    return db.query(Usuario).filter(Usuario.id == vinculo.id_usuario).first()


def vincular_telegram_a_usuario(db: Session, telegram_id: int, usuario: Usuario):
    """
    Vincula un identificador de Telegram a un usuario de forma segura.

    Reglas:
    - Un telegram_id no puede vincularse a una cuenta distinta si ya está asociado.
    - Una cuenta de usuario no puede vincularse a otro Telegram si ya tiene vínculo.
    - Evita asociaciones duplicadas.
    """
    vinculo_telegram = obtener_vinculo_por_telegram_id(db, telegram_id)
    vinculo_usuario = obtener_vinculo_por_usuario_id(db, usuario.id)

    if vinculo_telegram and vinculo_telegram.id_usuario != usuario.id:
        raise TelegramLinkError(
            "Este Telegram ya está vinculado a otra cuenta. "
            "No es posible asociarlo a una cuenta diferente."
        )

    if vinculo_usuario and vinculo_usuario.telegram_id != telegram_id:
        raise TelegramLinkError(
            "Esta cuenta ya está vinculada a otro Telegram. "
            "Debes resolver esa vinculación mediante un procedimiento seguro."
        )

    if vinculo_telegram and vinculo_usuario:
        return vinculo_telegram

    try:
        nuevo_vinculo = CuentaTelegram(
            telegram_id=telegram_id,
            id_usuario=usuario.id,
        )
        db.add(nuevo_vinculo)
        db.commit()
        db.refresh(nuevo_vinculo)
        return nuevo_vinculo
    except Exception:
        db.rollback()
        # Revalidar en caso de condición de carrera/duplicado
        vinculo_telegram = obtener_vinculo_por_telegram_id(db, telegram_id)
        vinculo_usuario = obtener_vinculo_por_usuario_id(db, usuario.id)
        if vinculo_telegram and vinculo_usuario and vinculo_telegram.id_usuario == usuario.id:
            return vinculo_telegram
        if vinculo_telegram and vinculo_telegram.id_usuario != usuario.id:
            raise TelegramLinkError(
                "Este Telegram ya está vinculado a otra cuenta. "
                "No es posible asociarlo a una cuenta diferente."
            )
        if vinculo_usuario and vinculo_usuario.telegram_id != telegram_id:
            raise TelegramLinkError(
                "Esta cuenta ya está vinculada a otro Telegram. "
                "Debes resolver esa vinculación mediante un procedimiento seguro."
            )
        raise


def validar_posible_vinculo(db: Session, telegram_id: int, usuario: Usuario) -> None:
    """Valida que el telegram_id pueda vincularse al usuario sin apropiación de cuentas."""
    vinculo_telegram = obtener_vinculo_por_telegram_id(db, telegram_id)
    vinculo_usuario = obtener_vinculo_por_usuario_id(db, usuario.id)

    if vinculo_telegram and vinculo_telegram.id_usuario != usuario.id:
        raise TelegramLinkError(
            "Este Telegram ya está vinculado a otra cuenta. "
            "No es posible asociarlo a una cuenta diferente."
        )

    if vinculo_usuario and vinculo_usuario.telegram_id != telegram_id:
        raise TelegramLinkError(
            "Esta cuenta ya está vinculada a otro Telegram. "
            "Debes resolver esa vinculación mediante un procedimiento seguro."
        )
