import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from telegram_bot.config import get_telegram_bot_token
from telegram_bot.handlers import (
    ayuda,
    cancelar,
    cv_entrada_invalida,
    cv_inicio,
    cv_recibir_documento,
    entrevista_entrada_invalida,
    entrevista_inicio,
    entrevista_responder,
    entrevista_seleccionar_perfil,
    historial_inicio,
    historial_opcion,
    login_contrasena,
    login_correo,
    login_inicio,
    menu_principal,
    registro_apellidos,
    registro_contrasena,
    registro_correo,
    registro_inicio,
    registro_nombres,
    start,
)
from telegram_bot.states import (
    ENTREVISTA_PERFIL,
    ENTREVISTA_RESPUESTA,
    ESPERANDO_CV,
    HISTORIAL_MENU,
    LOGIN_CONTRASENA,
    LOGIN_CORREO,
    REGISTRO_APELLIDOS,
    REGISTRO_CONTRASENA,
    REGISTRO_CORREO,
    REGISTRO_NOMBRES,
)
from telegram_bot.utils import limpiar_datos_temporales

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# Evitar exponer información sensible en niveles detallados de librerías HTTP
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start_fallback(update, context):
    """Finaliza una conversación y vuelve al menú principal."""
    limpiar_datos_temporales(context.user_data)
    await start(update, context)
    return ConversationHandler.END


def main() -> None:
    """Inicia el bot de Telegram de TalentBot."""
    token = get_telegram_bot_token()

    application = ApplicationBuilder().token(token).build()

    registro_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^1\. Registrarme$"), registro_inicio),
        ],
        states={
            REGISTRO_NOMBRES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), registro_nombres)
            ],
            REGISTRO_APELLIDOS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), registro_apellidos)
            ],
            REGISTRO_CORREO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), registro_correo)
            ],
            REGISTRO_CONTRASENA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), registro_contrasena)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancelar),
            CommandHandler("start", start_fallback),
            MessageHandler(filters.Regex(r"^Cancelar$"), cancelar),
        ],
        name="registro_conversacion",
        persistent=False,
    )

    login_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^2\. Iniciar sesión$"), login_inicio),
        ],
        states={
            LOGIN_CORREO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), login_correo)
            ],
            LOGIN_CONTRASENA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), login_contrasena)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancelar),
            CommandHandler("start", start_fallback),
            MessageHandler(filters.Regex(r"^Cancelar$"), cancelar),
        ],
        name="login_conversacion",
        persistent=False,
    )

    cv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^3\. Analizar mi hoja de vida$"), cv_inicio),
        ],
        states={
            ESPERANDO_CV: [
                MessageHandler(filters.Document.ALL & ~filters.COMMAND, cv_recibir_documento),
                MessageHandler(~filters.COMMAND, cv_entrada_invalida),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancelar),
            CommandHandler("start", start_fallback),
            MessageHandler(filters.Regex(r"^Cancelar$"), cancelar),
        ],
        name="cv_conversacion",
        persistent=False,
    )

    entrevista_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^6\. Practicar entrevista laboral$"), entrevista_inicio),
        ],
        states={
            ENTREVISTA_PERFIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), entrevista_seleccionar_perfil),
            ],
            ENTREVISTA_RESPUESTA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^Cancelar$"), entrevista_responder),
                MessageHandler(~filters.COMMAND, entrevista_entrada_invalida),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancelar),
            CommandHandler("start", start_fallback),
            MessageHandler(filters.Regex(r"^Cancelar$"), cancelar),
        ],
        name="entrevista_conversacion",
        persistent=False,
    )

    historial_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^7\. Consultar mi historial$"), historial_inicio),
        ],
        states={
            HISTORIAL_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, historial_opcion),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancelar),
            CommandHandler("start", start_fallback),
        ],
        name="historial_conversacion",
        persistent=False,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("cancel", cancelar))
    application.add_handler(registro_handler)
    application.add_handler(login_handler)
    application.add_handler(cv_handler)
    application.add_handler(entrevista_handler)
    application.add_handler(historial_handler)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu_principal)
    )

    logger.info("Iniciando TalentBot en Telegram...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
