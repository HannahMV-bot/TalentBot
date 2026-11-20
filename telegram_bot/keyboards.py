from telegram import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Construye el menú principal del bot."""
    keyboard = [
        [KeyboardButton("1. Registrarme"), KeyboardButton("2. Iniciar sesión")],
        [KeyboardButton("3. Analizar mi hoja de vida"), KeyboardButton("4. Consultar mi perfil profesional")],
        [KeyboardButton("5. Buscar ofertas laborales"), KeyboardButton("6. Practicar entrevista laboral")],
        [KeyboardButton("7. Consultar mi historial"), KeyboardButton("8. Cerrar sesión")],
        [KeyboardButton("9. Ayuda")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Teclado con opción para cancelar un flujo en curso."""
    return ReplyKeyboardMarkup([[KeyboardButton("Cancelar")]], resize_keyboard=True)


def history_menu_keyboard() -> ReplyKeyboardMarkup:
    """Construye el menú de historial."""
    keyboard = [
        [KeyboardButton("1. Mis análisis de hojas de vida")],
        [KeyboardButton("2. Mis recomendaciones laborales")],
        [KeyboardButton("3. Mis entrevistas realizadas")],
        [KeyboardButton("4. Volver al menú principal")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
