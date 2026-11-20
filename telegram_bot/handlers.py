import json
import logging

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Usuario
from backend.app.services.cv_management_service import (
    CVManagementError,
    analizar_y_guardar_cv,
    obtener_historial_cv,
    obtener_ultimo_analisis_cv,
)
from backend.app.services.interview_management_service import (
    InterviewManagementError,
    evaluar_y_guardar_respuesta,
    generar_y_guardar_entrevista,
    obtener_historial_entrevistas,
)
from backend.app.services.interview_simulator import PREGUNTAS_POR_PERFIL
from backend.app.services.job_management_service import (
    JobManagementError,
    generar_y_guardar_recomendaciones,
    obtener_historial_recomendaciones,
)
from backend.app.services.telegram_account_service import (
    TelegramLinkError,
    obtener_vinculo_por_telegram_id,
    validar_posible_vinculo,
    vincular_telegram_a_usuario,
)
from backend.app.services.user_service import buscar_usuario_por_correo, iniciar_sesion, registrar_usuario
from telegram_bot.auth import (
    db_session,
    es_chat_privado,
    establecer_sesion_activa,
    esta_autenticado,
    limpiar_sesion_activa,
    obtener_id_usuario_autenticado,
    obtener_usuario_autenticado,
)
from telegram_bot.keyboards import cancel_keyboard, history_menu_keyboard, main_menu_keyboard
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
from telegram_bot.utils import (
    dividir_mensaje_telegram,
    es_correo_valido,
    formatear_recomendaciones_laborales,
    formatear_resultado_cv,
    limpiar_datos_temporales,
    mensaje_ayuda,
    mensaje_bienvenida,
    mensaje_no_autenticado,
    mensaje_solo_privado,
    normalizar_correo,
)

logger = logging.getLogger(__name__)

PROTECTED_OPTIONS = {
    "4. Consultar mi perfil profesional",
}


async def _borrar_mensaje_si_es_posible(update: Update) -> None:
    message = update.effective_message
    if not message:
        return
    try:
        await message.delete()
    except Exception:
        # Si no se puede eliminar (p. ej. permisos o limitaciones), se continúa sin exponer el contenido.
        pass


def _texto_mensaje(update: Update) -> str:
    if not update.message or not update.message.text:
        return ""
    return update.message.text.strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el mensaje de bienvenida y el menú principal."""
    if not update.message:
        return
    limpiar_datos_temporales(context.user_data)
    await update.message.reply_text(
        mensaje_bienvenida(),
        reply_markup=main_menu_keyboard(),
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la ayuda del bot."""
    if not update.message:
        return
    await update.message.reply_text(
        mensaje_ayuda(),
        reply_markup=main_menu_keyboard(),
    )


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela cualquier proceso conversacional en curso."""
    limpiar_datos_temporales(context.user_data)
    if update.message:
        await update.message.reply_text(
            "Proceso cancelado. Puedes seleccionar una opción del menú principal.",
            reply_markup=main_menu_keyboard(),
        )
    return ConversationHandler.END


# ==========================================
# REGISTRO
# ==========================================

async def registro_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END

    limpiar_datos_temporales(context.user_data)

    if not es_chat_privado(update):
        await update.message.reply_text(
            mensaje_solo_privado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    telegram_id = update.effective_user.id

    if esta_autenticado(context):
        await update.message.reply_text(
            "Ya tienes una sesión activa. Si deseas registrar o usar otra cuenta, "
            "primero selecciona \"8. Cerrar sesión\".",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    with db_session() as db:
        vinculo = obtener_vinculo_por_telegram_id(db, telegram_id)
        if vinculo:
            await update.message.reply_text(
                "Este Telegram ya está vinculado a una cuenta registrada. "
                "Selecciona \"2. Iniciar sesión\" para acceder o usa un procedimiento seguro "
                "si necesitas resolver la vinculación.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "Vamos a crear tu cuenta. Escribe tus nombres.\n"
        "Puedes escribir \"Cancelar\" o usar /cancel para salir.",
        reply_markup=cancel_keyboard(),
    )
    return REGISTRO_NOMBRES


async def registro_nombres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END
    texto = _texto_mensaje(update)
    if not texto:
        await update.message.reply_text(
            "Por favor, ingresa tus nombres.", reply_markup=cancel_keyboard()
        )
        return REGISTRO_NOMBRES

    context.user_data["registro_nombres"] = texto
    await update.message.reply_text(
        "Ahora escribe tus apellidos.",
        reply_markup=cancel_keyboard(),
    )
    return REGISTRO_APELLIDOS


async def registro_apellidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END
    texto = _texto_mensaje(update)
    if not texto:
        await update.message.reply_text(
            "Por favor, ingresa tus apellidos.", reply_markup=cancel_keyboard()
        )
        return REGISTRO_APELLIDOS

    context.user_data["registro_apellidos"] = texto
    await update.message.reply_text(
        "Escribe tu correo electrónico.",
        reply_markup=cancel_keyboard(),
    )
    return REGISTRO_CORREO


async def registro_correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END
    correo = normalizar_correo(_texto_mensaje(update))

    if not es_correo_valido(correo):
        await update.message.reply_text(
            "El correo electrónico no tiene un formato válido. Intenta nuevamente.",
            reply_markup=cancel_keyboard(),
        )
        return REGISTRO_CORREO

    with db_session() as db:
        if buscar_usuario_por_correo(db, correo):
            await update.message.reply_text(
                "El correo electrónico ya está registrado. "
                "Si es tu cuenta, selecciona \"2. Iniciar sesión\".",
                reply_markup=main_menu_keyboard(),
            )
            limpiar_datos_temporales(context.user_data)
            return ConversationHandler.END

    context.user_data["registro_correo"] = correo
    await update.message.reply_text(
        "Escribe una contraseña para tu cuenta.\n"
        "Por seguridad, evita compartirla y, si es posible, elimínala del chat después de enviarla.",
        reply_markup=cancel_keyboard(),
    )
    return REGISTRO_CONTRASENA


async def registro_contrasena(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END

    contrasena = update.message.text or ""
    await _borrar_mensaje_si_es_posible(update)

    if not contrasena.strip():
        await update.message.reply_text(
            "La contraseña no puede estar vacía. Intenta nuevamente.",
            reply_markup=cancel_keyboard(),
        )
        return REGISTRO_CONTRASENA

    nombres = context.user_data.get("registro_nombres", "").strip()
    apellidos = context.user_data.get("registro_apellidos", "").strip()
    correo = context.user_data.get("registro_correo", "").strip()
    telegram_id = update.effective_user.id

    if not (nombres and apellidos and correo):
        limpiar_datos_temporales(context.user_data)
        await update.message.reply_text(
            "La información del registro está incompleta. Inicia el proceso nuevamente.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    usuario_id = None
    usuario_nombres = nombres

    with db_session() as db:
        vinculo = obtener_vinculo_por_telegram_id(db, telegram_id)
        if vinculo:
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                "Este Telegram ya está vinculado a una cuenta registrada. "
                "No es posible completar un nuevo registro desde este Telegram.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        if buscar_usuario_por_correo(db, correo):
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                "El correo electrónico ya está registrado. "
                "Selecciona \"2. Iniciar sesión\" si es tu cuenta.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        usuario = registrar_usuario(
            db=db,
            nombres=nombres,
            apellidos=apellidos,
            correo=correo,
            contrasena=contrasena,
        )

        if usuario is None:
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                "No fue posible completar el registro. Verifica tus datos e intenta nuevamente.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        try:
            vincular_telegram_a_usuario(db, telegram_id, usuario)
        except TelegramLinkError as error:
            # El usuario fue creado; se informa el conflicto de vinculación sin exponer datos sensibles.
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                f"Tu cuenta fue creada, pero no se pudo vincular este Telegram: {error.message}",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END
        except Exception:
            logger.exception("Error al vincular Telegram tras registro")
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                "Tu cuenta fue creada, pero ocurrió un error al vincular este Telegram. "
                "Intenta iniciar sesión para completar la vinculación.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        usuario_id = usuario.id
        usuario_nombres = usuario.nombres

    establecer_sesion_activa(context, usuario_id)
    limpiar_datos_temporales(context.user_data)
    await update.message.reply_text(
        f"Registro completado correctamente. ¡Bienvenido/a, {usuario_nombres}!",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


# ==========================================
# INICIO DE SESIÓN
# ==========================================

async def login_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END

    limpiar_datos_temporales(context.user_data)

    if not es_chat_privado(update):
        await update.message.reply_text(
            mensaje_solo_privado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    if esta_autenticado(context):
        await update.message.reply_text(
            "Ya tienes una sesión activa. Si deseas cambiar de cuenta, "
            "selecciona \"8. Cerrar sesión\" primero.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Inicia sesión con tu cuenta de TalentBot.\n"
        "Escribe tu correo electrónico.\n"
        "Puedes escribir \"Cancelar\" o usar /cancel para salir.",
        reply_markup=cancel_keyboard(),
    )
    return LOGIN_CORREO


async def login_correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END

    correo = normalizar_correo(_texto_mensaje(update))
    if not es_correo_valido(correo):
        await update.message.reply_text(
            "El correo electrónico no tiene un formato válido. Intenta nuevamente.",
            reply_markup=cancel_keyboard(),
        )
        return LOGIN_CORREO

    context.user_data["login_correo"] = correo
    await update.message.reply_text(
        "Escribe tu contraseña.\n"
        "Por seguridad, evita compartirla y, si es posible, elimínala del chat después de enviarla.",
        reply_markup=cancel_keyboard(),
    )
    return LOGIN_CONTRASENA


async def login_contrasena(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END

    contrasena = update.message.text or ""
    await _borrar_mensaje_si_es_posible(update)

    correo = context.user_data.get("login_correo", "").strip()
    telegram_id = update.effective_user.id

    if not correo:
        limpiar_datos_temporales(context.user_data)
        await update.message.reply_text(
            "No se encontró el correo del inicio de sesión. Intenta nuevamente.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    usuario_id = None
    usuario_nombres = ""

    with db_session() as db:
        usuario = iniciar_sesion(db=db, correo=correo, contrasena=contrasena)
        if usuario is None:
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                "Correo o contraseña incorrectos.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        try:
            validar_posible_vinculo(db, telegram_id, usuario)
            vincular_telegram_a_usuario(db, telegram_id, usuario)
        except TelegramLinkError as error:
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                error.message,
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END
        except Exception:
            logger.exception("Error al vincular Telegram durante inicio de sesión")
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                "Ocurrió un error al vincular tu cuenta de Telegram. Intenta nuevamente.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        usuario_id = usuario.id
        usuario_nombres = usuario.nombres

    establecer_sesion_activa(context, usuario_id)
    limpiar_datos_temporales(context.user_data)
    await update.message.reply_text(
        f"Inicio de sesión exitoso. ¡Hola, {usuario_nombres}!",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


# ==========================================
# ANÁLISIS DE HOJA DE VIDA (CV)
# ==========================================

async def cv_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de análisis de hoja de vida."""
    if not update.message:
        return ConversationHandler.END

    limpiar_datos_temporales(context.user_data)
    telegram_id = update.effective_user.id

    if not esta_autenticado(context):
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "Envíame tu hoja de vida en formato PDF para analizarla.\n"
        "Solo se aceptan documentos PDF.\n"
        "Puedes escribir \"Cancelar\" o usar /cancel para salir.",
        reply_markup=cancel_keyboard(),
    )
    return ESPERANDO_CV


async def cv_recibir_documento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y procesa un documento PDF del usuario autenticado."""
    if not update.message:
        return ESPERANDO_CV

    telegram_id = update.effective_user.id

    if not esta_autenticado(context):
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    documento = update.message.document
    if not documento:
        await update.message.reply_text(
            "Debes enviar tu hoja de vida como documento PDF. Intenta nuevamente.",
            reply_markup=cancel_keyboard(),
        )
        return ESPERANDO_CV

    nombre_archivo = (documento.file_name or "").strip()
    if not nombre_archivo.lower().endswith(".pdf"):
        await update.message.reply_text(
            "El archivo debe tener formato PDF. Envía un documento con extensión .pdf.",
            reply_markup=cancel_keyboard(),
        )
        return ESPERANDO_CV

    # Validación temprana de tamaño/archivo vacío si Telegram reporta tamaño
    if documento.file_size is not None and documento.file_size <= 0:
        await update.message.reply_text(
            "El archivo PDF está vacío. Envía un documento válido.",
            reply_markup=cancel_keyboard(),
        )
        return ESPERANDO_CV

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Documento recibido. Estoy procesando tu hoja de vida, por favor espera..."
        )

        try:
            archivo = await documento.get_file()
            contenido = bytes(await archivo.download_as_bytearray())
        except Exception:
            logger.exception("Error al descargar documento de Telegram")
            await update.message.reply_text(
                "No fue posible descargar el documento. Verifica el archivo e intenta nuevamente.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        try:
            resultado = analizar_y_guardar_cv(
                db=db,
                usuario=usuario,
                nombre_archivo=nombre_archivo,
                contenido=contenido,
            )
        except CVManagementError as error:
            await update.message.reply_text(
                str(error),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END
        except ValueError as error:
            await update.message.reply_text(
                f"No fue posible procesar el PDF: {error}",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END
        except Exception:
            logger.exception("Error al procesar/guardar análisis de CV")
            await update.message.reply_text(
                "Ocurrió un error al procesar tu hoja de vida. Intenta nuevamente más tarde.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END
        finally:
            # No se crean archivos temporales en disco; se limpia la referencia en memoria.
            contenido = None

    analisis = resultado.get("analisis", {})
    mensaje_resultado = formatear_resultado_cv(nombre_archivo, analisis)
    await update.message.reply_text(
        mensaje_resultado,
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def cv_entrada_invalida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja entradas no válidas mientras se espera un PDF."""
    if not update.message:
        return ESPERANDO_CV
    await update.message.reply_text(
        "Por favor, envía tu hoja de vida como documento PDF o escribe \"Cancelar\" para salir.",
        reply_markup=cancel_keyboard(),
    )
    return ESPERANDO_CV


# ==========================================
# RECOMENDACIONES LABORALES
# ==========================================

async def buscar_ofertas_laborales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Genera y muestra recomendaciones laborales para el usuario autenticado."""
    if not update.message:
        return

    telegram_id = update.effective_user.id

    if not esta_autenticado(context):
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return

        hoja_vida, analisis = obtener_ultimo_analisis_cv(db, usuario)
        if hoja_vida is None or analisis is None:
            await update.message.reply_text(
                "Aún no tienes un análisis de hoja de vida guardado. "
                "Selecciona \"3. Analizar mi hoja de vida\" para continuar.",
                reply_markup=main_menu_keyboard(),
            )
            return

        await update.message.reply_text(
            "Estoy generando tus recomendaciones laborales, por favor espera..."
        )

        try:
            resultado = generar_y_guardar_recomendaciones(db=db, usuario=usuario)
        except JobManagementError as error:
            if error.status_code == 404:
                await update.message.reply_text(
                    "Aún no tienes un análisis de hoja de vida disponible para generar recomendaciones. "
                    "Selecciona \"3. Analizar mi hoja de vida\" para continuar.",
                    reply_markup=main_menu_keyboard(),
                )
            else:
                await update.message.reply_text(
                    f"No fue posible generar las recomendaciones: {error.message}",
                    reply_markup=main_menu_keyboard(),
                )
            return
        except Exception:
            logger.exception("Error al generar recomendaciones laborales")
            await update.message.reply_text(
                "Ocurrió un error al generar tus recomendaciones. Intenta nuevamente más tarde.",
                reply_markup=main_menu_keyboard(),
            )
            return

    texto = formatear_recomendaciones_laborales(resultado)
    partes = dividir_mensaje_telegram(texto)
    total = len(partes)
    for i, parte in enumerate(partes, start=1):
        if total > 1:
            prefijo = f"(Parte {i}/{total})\n"
            contenido = prefijo + parte
            # Ajuste por si el prefijo excede el límite en casos extremos
            if len(contenido) > 4096:
                contenido = contenido[:4096]
        else:
            contenido = parte
        await update.message.reply_text(contenido)

    await update.message.reply_text(
        "Puedes volver al menú principal para continuar.",
        reply_markup=main_menu_keyboard(),
    )


# ==========================================
# SIMULADOR DE ENTREVISTAS
# ==========================================

def _perfiles_disponibles_desde_analisis(analisis_obj):
    if not analisis_obj or not analisis_obj.perfil_profesional:
        return []
    try:
        perfil_data = json.loads(analisis_obj.perfil_profesional)
    except Exception:
        return []
    recomendados = perfil_data.get("perfiles_recomendados") or []
    disponibles = [p for p in recomendados if p in PREGUNTAS_POR_PERFIL]
    # eliminar duplicados conservando orden
    vistos = set()
    resultado = []
    for p in disponibles:
        if p not in vistos:
            vistos.add(p)
            resultado.append(p)
    return resultado


def _teclado_seleccion_perfil(perfiles):
    filas = [[p] for p in perfiles]
    filas.append(["Cancelar"])
    return ReplyKeyboardMarkup(filas, resize_keyboard=True, one_time_keyboard=True)


def _formatear_pregunta_entrevista(indice: int, total: int, pregunta: str) -> str:
    return (
        f"Pregunta {indice + 1} de {total}\n\n"
        f"{pregunta}\n\n"
        "Escribe tu respuesta."
    )


def _formatear_resultado_evaluacion(resultado: dict) -> str:
    estado = resultado.get("estado")
    retro = resultado.get("retroalimentacion") or ""
    if estado == "Pregunta no reconocida" or resultado.get("puntuacion") is None:
        return (
            "Respuesta guardada.\n"
            "Evaluación automática: no disponible para esta pregunta.\n"
            f"Retroalimentación: {retro}"
        )
    return (
        "Respuesta evaluada.\n"
        f"Puntuación: {resultado.get('puntuacion')}\n"
        f"Retroalimentación: {retro}"
    )


def _formatear_resumen_entrevista(perfil: str, respuestas: list) -> str:
    if not respuestas:
        return (
            f"Resumen de la entrevista ({perfil})\n\n"
            "No se registraron respuestas."
        )

    lineas = [f"Resumen de la entrevista - Perfil: {perfil}", ""]
    puntuadas = [r.get("puntuacion") for r in respuestas if r.get("puntuacion") is not None]
    lineas.append(f"Preguntas respondidas: {len(respuestas)}")
    if puntuadas:
        promedio = round(sum(puntuadas) / len(puntuadas), 2)
        lineas.append(f"Promedio (respuestas evaluadas automáticamente): {promedio}")
    else:
        lineas.append("Promedio (respuestas evaluadas automáticamente): no disponible")
    lineas.append("")

    for i, item in enumerate(respuestas, start=1):
        lineas.append(f"{i}. Pregunta: {item.get('pregunta', '')}")
        if item.get("puntuacion") is None:
            lineas.append("   Puntuación: no disponible (sin evaluación automática)")
        else:
            lineas.append(f"   Puntuación: {item.get('puntuacion')}")
        retro = item.get("retroalimentacion") or ""
        if retro:
            lineas.append(f"   Retroalimentación: {retro}")
        lineas.append("")

    return "\n".join(lineas).strip()


async def _iniciar_entrevista_con_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE, perfil: str):
    telegram_id = update.effective_user.id
    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            limpiar_datos_temporales(context.user_data)
            return ConversationHandler.END

        try:
            resultado = generar_y_guardar_entrevista(db=db, usuario=usuario, perfil=perfil)
        except InterviewManagementError as error:
            await update.message.reply_text(
                f"No fue posible iniciar la entrevista: {error.message}",
                reply_markup=main_menu_keyboard(),
            )
            limpiar_datos_temporales(context.user_data)
            return ConversationHandler.END
        except Exception:
            logger.exception("Error al generar entrevista")
            await update.message.reply_text(
                "Ocurrió un error al iniciar la entrevista. Intenta nuevamente más tarde.",
                reply_markup=main_menu_keyboard(),
            )
            limpiar_datos_temporales(context.user_data)
            return ConversationHandler.END

    preguntas = resultado.get("preguntas") or []
    if not preguntas:
        await update.message.reply_text(
            "No se pudieron generar preguntas para este perfil.",
            reply_markup=main_menu_keyboard(),
        )
        limpiar_datos_temporales(context.user_data)
        return ConversationHandler.END

    context.user_data["entrevista_id"] = resultado.get("id_entrevista")
    context.user_data["entrevista_perfil"] = resultado.get("perfil", perfil)
    context.user_data["entrevista_preguntas"] = preguntas
    context.user_data["entrevista_indice"] = 0
    context.user_data["entrevista_respuestas"] = []
    context.user_data.pop("entrevista_perfiles_opciones", None)

    await update.message.reply_text(
        f"Entrevista iniciada para el perfil: {context.user_data['entrevista_perfil']}\n"
        "Responderás una pregunta a la vez. Puedes escribir \"Cancelar\" o usar /cancel para salir.",
        reply_markup=cancel_keyboard(),
    )
    await update.message.reply_text(
        _formatear_pregunta_entrevista(0, len(preguntas), preguntas[0]),
        reply_markup=cancel_keyboard(),
    )
    return ENTREVISTA_RESPUESTA


async def entrevista_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo del simulador de entrevistas."""
    if not update.message:
        return ConversationHandler.END

    limpiar_datos_temporales(context.user_data)
    telegram_id = update.effective_user.id

    if not esta_autenticado(context):
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        hoja_vida, analisis = obtener_ultimo_analisis_cv(db, usuario)
        if hoja_vida is None or analisis is None:
            await update.message.reply_text(
                "Aún no tienes un análisis de hoja de vida. "
                "Selecciona \"3. Analizar mi hoja de vida\" antes de iniciar una entrevista.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        perfiles = _perfiles_disponibles_desde_analisis(analisis)

    if not perfiles:
        await update.message.reply_text(
            "No se encontró un perfil profesional compatible con el simulador de entrevistas. "
            "Analiza nuevamente tu hoja de vida o actualiza tus habilidades para continuar.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    if len(perfiles) == 1:
        return await _iniciar_entrevista_con_perfil(update, context, perfiles[0])

    context.user_data["entrevista_perfiles_opciones"] = perfiles
    await update.message.reply_text(
        "Se detectaron varios perfiles profesionales. Selecciona con cuál deseas practicar la entrevista:",
        reply_markup=_teclado_seleccion_perfil(perfiles),
    )
    return ENTREVISTA_PERFIL


async def entrevista_seleccionar_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ENTREVISTA_PERFIL

    telegram_id = update.effective_user.id
    if not esta_autenticado(context):
        limpiar_datos_temporales(context.user_data)
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

    opciones = context.user_data.get("entrevista_perfiles_opciones") or []
    seleccion = (update.message.text or "").strip()

    if seleccion not in opciones:
        if opciones:
            await update.message.reply_text(
                "Selección inválida. Elige uno de los perfiles disponibles o escribe \"Cancelar\".",
                reply_markup=_teclado_seleccion_perfil(opciones),
            )
            return ENTREVISTA_PERFIL
        limpiar_datos_temporales(context.user_data)
        await update.message.reply_text(
            "No hay perfiles disponibles para seleccionar. Intenta iniciar la entrevista nuevamente.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    return await _iniciar_entrevista_con_perfil(update, context, seleccion)


async def entrevista_responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ENTREVISTA_RESPUESTA

    telegram_id = update.effective_user.id
    if not esta_autenticado(context):
        limpiar_datos_temporales(context.user_data)
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    # Entrada inválida: debe ser respuesta escrita (texto no vacío)
    if not update.message.text or not update.message.text.strip():
        preguntas = context.user_data.get("entrevista_preguntas") or []
        indice = context.user_data.get("entrevista_indice", 0)
        if preguntas and 0 <= indice < len(preguntas):
            await update.message.reply_text(
                "Entrada inválida. Por favor, escribe una respuesta en texto para continuar.\n\n"
                + _formatear_pregunta_entrevista(indice, len(preguntas), preguntas[indice]),
                reply_markup=cancel_keyboard(),
            )
        else:
            await update.message.reply_text(
                "Entrada inválida. Por favor, escribe una respuesta en texto.",
                reply_markup=cancel_keyboard(),
            )
        return ENTREVISTA_RESPUESTA

    respuesta_texto = update.message.text.strip()
    preguntas = context.user_data.get("entrevista_preguntas") or []
    indice = context.user_data.get("entrevista_indice", 0)
    entrevista_id = context.user_data.get("entrevista_id")
    perfil = context.user_data.get("entrevista_perfil", "")

    if not preguntas or entrevista_id is None or not (0 <= indice < len(preguntas)):
        limpiar_datos_temporales(context.user_data)
        await update.message.reply_text(
            "La sesión de entrevista no es válida o ha expirado. Inicia una nueva entrevista desde el menú.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    pregunta_actual = preguntas[indice]

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            limpiar_datos_temporales(context.user_data)
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        try:
            resultado = evaluar_y_guardar_respuesta(
                db=db,
                usuario=usuario,
                id_entrevista=entrevista_id,
                pregunta=pregunta_actual,
                respuesta=respuesta_texto,
                guardar_no_reconocida=True,
            )
        except InterviewManagementError as error:
            await update.message.reply_text(
                f"No fue posible registrar tu respuesta: {error.message}\n"
                "Intenta responder nuevamente.",
                reply_markup=cancel_keyboard(),
            )
            return ENTREVISTA_RESPUESTA
        except Exception:
            logger.exception("Error al evaluar/guardar respuesta de entrevista")
            await update.message.reply_text(
                "Ocurrió un error al guardar tu respuesta. Intenta nuevamente.",
                reply_markup=cancel_keyboard(),
            )
            return ENTREVISTA_RESPUESTA

    respuestas_guardadas = context.user_data.get("entrevista_respuestas") or []
    respuestas_guardadas.append(
        {
            "pregunta": pregunta_actual,
            "respuesta": respuesta_texto,
            "puntuacion": resultado.get("puntuacion"),
            "retroalimentacion": resultado.get("retroalimentacion"),
            "estado": resultado.get("estado"),
        }
    )
    context.user_data["entrevista_respuestas"] = respuestas_guardadas

    await update.message.reply_text(
        _formatear_resultado_evaluacion(resultado),
        reply_markup=cancel_keyboard(),
    )

    nuevo_indice = indice + 1
    context.user_data["entrevista_indice"] = nuevo_indice

    if nuevo_indice < len(preguntas):
        await update.message.reply_text(
            _formatear_pregunta_entrevista(nuevo_indice, len(preguntas), preguntas[nuevo_indice]),
            reply_markup=cancel_keyboard(),
        )
        return ENTREVISTA_RESPUESTA

    resumen = _formatear_resumen_entrevista(perfil, respuestas_guardadas)
    for parte in dividir_mensaje_telegram(resumen):
        await update.message.reply_text(parte)
    await update.message.reply_text(
        "Entrevista finalizada. Puedes volver al menú principal.",
        reply_markup=main_menu_keyboard(),
    )
    limpiar_datos_temporales(context.user_data)
    return ConversationHandler.END


async def entrevista_entrada_invalida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ENTREVISTA_RESPUESTA
    preguntas = context.user_data.get("entrevista_preguntas") or []
    indice = context.user_data.get("entrevista_indice", 0)
    if preguntas and 0 <= indice < len(preguntas):
        await update.message.reply_text(
            "Por favor, responde con un mensaje de texto.\n\n"
            + _formatear_pregunta_entrevista(indice, len(preguntas), preguntas[indice]),
            reply_markup=cancel_keyboard(),
        )
    else:
        await update.message.reply_text(
            "Por favor, responde con un mensaje de texto o escribe \"Cancelar\" para salir.",
            reply_markup=cancel_keyboard(),
        )
    return ENTREVISTA_RESPUESTA


# ==========================================
# HISTORIAL
# ==========================================

def _formatear_perfil_historial(perfil) -> str:
    if not perfil:
        return "No disponible"
    if isinstance(perfil, dict):
        perfiles = perfil.get("perfiles_recomendados") or []
        estado = perfil.get("estado") or ""
        if perfiles:
            texto = perfiles[0] if len(perfiles) == 1 else ", ".join(perfiles)
            return f"{texto} ({estado})" if estado else texto
        return estado or "No disponible"
    return str(perfil)


def _formatear_historial_cv(historial_data: dict) -> str:
    historial = historial_data.get("historial") or []
    if not historial:
        return "No tienes análisis de hojas de vida registrados."

    lineas = ["Mis análisis de hojas de vida", ""]
    for hoja in historial:
        nombre = hoja.get("nombre_archivo", "No disponible")
        analisis_lista = hoja.get("analisis") or []
        if not analisis_lista:
            lineas.append(f"Archivo: {nombre}")
            lineas.append("Fecha del análisis: No disponible")
            lineas.append("Perfil profesional detectado: No disponible")
            lineas.append("Habilidades identificadas: No disponibles")
            lineas.append("")
            continue
        for analisis in analisis_lista:
            fecha = analisis.get("fecha_analisis") or hoja.get("fecha_subida") or "No disponible"
            perfil = _formatear_perfil_historial(analisis.get("perfil_profesional"))
            habilidades = analisis.get("habilidades") or []
            habilidades_txt = ", ".join(habilidades) if habilidades else "No se identificaron habilidades."
            lineas.append(f"Archivo: {nombre}")
            lineas.append(f"Fecha del análisis: {fecha}")
            lineas.append(f"Perfil profesional detectado: {perfil}")
            lineas.append(f"Habilidades identificadas: {habilidades_txt}")
            lineas.append("")
    return "\n".join(lineas).strip()


def _formatear_historial_recomendaciones(historial_data: dict) -> str:
    historial = historial_data.get("historial") or []
    encabezado = (
        "Mis recomendaciones laborales\n\n"
        "Nota: Las ofertas mostradas son demostrativas y no corresponden a vacantes laborales reales.\n"
    )
    if not historial:
        return encabezado + "\nNo tienes recomendaciones laborales registradas."

    lineas = [encabezado]
    for i, item in enumerate(historial, start=1):
        lineas.append(
            f"\n{i}. Cargo: {item.get('cargo', 'No disponible')}\n"
            f"Empresa: {item.get('empresa', 'No disponible')}\n"
            f"Modalidad: {item.get('modalidad', 'No disponible')}\n"
            f"Porcentaje de compatibilidad: {item.get('porcentaje_compatibilidad', 0)}%\n"
            f"Fecha de recomendación: {item.get('fecha_recomendacion', 'No disponible')}\n"
        )
    return "".join(lineas).strip()


def _formatear_historial_entrevistas(historial_data: dict) -> str:
    historial = historial_data.get("historial") or []
    if not historial:
        return "No tienes entrevistas registradas."

    lineas = ["Mis entrevistas realizadas", ""]
    for i, entrevista in enumerate(historial, start=1):
        lineas.append(f"{i}. Perfil profesional: {entrevista.get('perfil', 'No disponible')}")
        lineas.append(f"Fecha de realización: {entrevista.get('fecha', 'No disponible')}")
        respuestas = entrevista.get("respuestas") or []
        lineas.append(f"Preguntas respondidas: {len(respuestas)}")
        if not respuestas:
            lineas.append("Puntuaciones disponibles: No hay respuestas registradas.")
            lineas.append("Retroalimentación registrada: No disponible.")
            lineas.append("")
            continue
        puntuadas = [r.get("puntuacion") for r in respuestas if r.get("puntuacion") is not None]
        if puntuadas:
            lineas.append(f"Puntuaciones disponibles: {', '.join(str(p) for p in puntuadas)}")
        else:
            lineas.append("Puntuaciones disponibles: No disponibles (sin evaluación automática).")
        lineas.append("Retroalimentación registrada:")
        for j, resp in enumerate(respuestas, start=1):
            puntuacion = resp.get("puntuacion")
            if puntuacion is None:
                punt_txt = "sin puntuación automática"
            else:
                punt_txt = str(puntuacion)
            retro = resp.get("retroalimentacion") or "Sin retroalimentación registrada."
            lineas.append(f"  - Pregunta {j}: Puntuación: {punt_txt}. Retroalimentación: {retro}")
        lineas.append("")
    return "\n".join(lineas).strip()


async def historial_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú de historial."""
    if not update.message:
        return ConversationHandler.END

    telegram_id = update.effective_user.id
    if not esta_autenticado(context):
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "Consulta tu historial. Selecciona una opción:",
        reply_markup=history_menu_keyboard(),
    )
    return HISTORIAL_MENU


async def historial_opcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestiona las opciones del menú de historial."""
    if not update.message or not update.message.text:
        return HISTORIAL_MENU

    texto = update.message.text.strip()
    telegram_id = update.effective_user.id

    if texto == "4. Volver al menú principal":
        await update.message.reply_text(
            "Regresando al menú principal.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    if not esta_autenticado(context):
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    with db_session() as db:
        usuario = obtener_usuario_autenticado(db, context, telegram_id)
        if not usuario:
            await update.message.reply_text(
                mensaje_no_autenticado(),
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        try:
            if texto == "1. Mis análisis de hojas de vida":
                data = obtener_historial_cv(db, usuario)
                mensaje = _formatear_historial_cv(data)
            elif texto == "2. Mis recomendaciones laborales":
                data = obtener_historial_recomendaciones(db, usuario)
                mensaje = _formatear_historial_recomendaciones(data)
            elif texto == "3. Mis entrevistas realizadas":
                data = obtener_historial_entrevistas(db, usuario)
                mensaje = _formatear_historial_entrevistas(data)
            else:
                await update.message.reply_text(
                    "Opción no válida. Selecciona una opción del menú de historial.",
                    reply_markup=history_menu_keyboard(),
                )
                return HISTORIAL_MENU
        except Exception:
            logger.exception("Error al consultar historial")
            await update.message.reply_text(
                "Ocurrió un error al consultar tu historial. Intenta nuevamente.",
                reply_markup=history_menu_keyboard(),
            )
            return HISTORIAL_MENU

    for parte in dividir_mensaje_telegram(mensaje):
        await update.message.reply_text(parte)

    await update.message.reply_text(
        "Selecciona otra opción del historial o vuelve al menú principal.",
        reply_markup=history_menu_keyboard(),
    )
    return HISTORIAL_MENU


# ==========================================
# CIERRE DE SESIÓN Y MENÚ
# ==========================================

async def cerrar_sesion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    limpiar_datos_temporales(context.user_data)
    if not esta_autenticado(context):
        limpiar_sesion_activa(context)
        await update.message.reply_text(
            "No tienes una sesión activa en este chat.",
            reply_markup=main_menu_keyboard(),
        )
        return

    limpiar_sesion_activa(context)
    await update.message.reply_text(
        "Sesión cerrada correctamente. Tu cuenta y su vinculación se mantienen; "
        "puedes volver a iniciar sesión cuando lo desees.",
        reply_markup=main_menu_keyboard(),
    )


async def opcion_protegida(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Retorna True si el usuario está autenticado para usar opciones protegidas."""
    if not update.message:
        return False

    if esta_autenticado(context):
        # Validación adicional contra la vinculación actual en BD
        telegram_id = update.effective_user.id
        with db_session() as db:
            usuario_id = obtener_id_usuario_autenticado(context)
            usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first() if usuario_id else None
            if not usuario:
                limpiar_sesion_activa(context)
            else:
                vinculo = obtener_vinculo_por_telegram_id(db, telegram_id)
                if not vinculo or vinculo.id_usuario != usuario.id:
                    limpiar_sesion_activa(context)

    if not esta_autenticado(context):
        await update.message.reply_text(
            mensaje_no_autenticado(),
            reply_markup=main_menu_keyboard(),
        )
        return False

    return True


async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a opciones del menú principal."""
    if not update.message or not update.message.text:
        return

    texto = update.message.text.strip()

    if texto == "9. Ayuda":
        await ayuda(update, context)
        return

    if texto == "8. Cerrar sesión":
        await cerrar_sesion(update, context)
        return

    if texto == "5. Buscar ofertas laborales":
        await buscar_ofertas_laborales(update, context)
        return

    if texto in {"1. Registrarme", "2. Iniciar sesión", "3. Analizar mi hoja de vida", "6. Practicar entrevista laboral", "7. Consultar mi historial"}:
        # Estas opciones se gestionan mediante ConversationHandler; si llegan aquí, mostrar guía.
        if texto in {"3. Analizar mi hoja de vida", "6. Practicar entrevista laboral", "7. Consultar mi historial"}:
            if not await opcion_protegida(update, context):
                return
        if esta_autenticado(context):
            await update.message.reply_text(
                "Ya tienes una sesión activa. Selecciona nuevamente la opción del menú para iniciar el proceso.",
                reply_markup=main_menu_keyboard(),
            )
        else:
            await update.message.reply_text(
                "Selecciona nuevamente la opción del menú para iniciar el proceso.",
                reply_markup=main_menu_keyboard(),
            )
        return

    if texto in PROTECTED_OPTIONS:
        if not await opcion_protegida(update, context):
            return
        await update.message.reply_text(
            "Esta funcionalidad se habilitará en una etapa posterior. "
            "Por ahora puedes usar /start para ver el menú principal.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if texto == "Cancelar":
        limpiar_datos_temporales(context.user_data)
        await update.message.reply_text(
            "No hay un proceso en curso para cancelar.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await update.message.reply_text(
        "No he reconocido esa opción. Usa el menú o el comando /start para continuar.",
        reply_markup=main_menu_keyboard(),
    )
