"""Utilidades compartidas para el bot de Telegram."""

from email_validator import EmailNotValidError, validate_email

TEMP_DATA_KEYS = {
    "registro_nombres",
    "registro_apellidos",
    "registro_correo",
    "login_correo",
    "entrevista_id",
    "entrevista_preguntas",
    "entrevista_indice",
    "entrevista_perfil",
    "entrevista_respuestas",
    "entrevista_perfiles_opciones",
}


def mensaje_bienvenida() -> str:
    return (
        "¡Bienvenido/a a TalentBot! \n\n"
        "Soy tu asistente de orientación laboral. Desde este chat podrás "
        "gestionar tu perfil, analizar tu hoja de vida, recibir recomendaciones "
        "de empleo, practicar entrevistas y consultar tu historial.\n\n"
        "Selecciona una opción del menú para comenzar:"
    )


def mensaje_ayuda() -> str:
    return (
        "Ayuda - TalentBot\n\n"
        "Opciones disponibles en el menú:\n"
        "1. Registrarme: crea una cuenta en TalentBot.\n"
        "2. Iniciar sesión: accede con tu cuenta para usar tus datos.\n"
        "3. Analizar mi hoja de vida: envía un PDF para identificar habilidades y perfil.\n"
        "4. Consultar mi perfil profesional: revisa tu perfil detectado.\n"
        "5. Buscar ofertas laborales: recibe recomendaciones según tus habilidades.\n"
        "6. Practicar entrevista laboral: responde preguntas y recibe retroalimentación.\n"
        "7. Consultar mi historial: revisa análisis, recomendaciones y entrevistas.\n"
        "8. Cerrar sesión: finaliza tu sesión en este chat.\n"
        "9. Ayuda: muestra esta información.\n\n"
        "Usa /start o /cancel en cualquier momento para volver al menú principal."
    )


def limpiar_datos_temporales(user_data: dict) -> None:
    """Elimina datos temporales de conversaciones sensibles."""
    for key in list(TEMP_DATA_KEYS):
        user_data.pop(key, None)


def normalizar_correo(correo: str) -> str:
    return (correo or "").strip().lower()


def es_correo_valido(correo: str) -> bool:
    try:
        validate_email(correo, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def mensaje_no_autenticado() -> str:
    return (
        "Debes iniciar sesión para acceder a esta funcionalidad. "
        "Selecciona \"2. Iniciar sesión\" en el menú principal."
    )


def mensaje_solo_privado() -> str:
    return (
        "Por seguridad, el registro y el inicio de sesión solo están disponibles "
        "en conversaciones privadas con el bot."
    )


def _formatear_perfil(perfil: dict) -> str:
    if not perfil:
        return "No disponible"
    perfiles = perfil.get("perfiles_recomendados") or []
    estado = perfil.get("estado") or ""
    if not perfiles:
        return estado or "No se pudo identificar un perfil profesional con la información disponible."
    if len(perfiles) == 1:
        texto = perfiles[0]
    else:
        texto = ", ".join(perfiles)
    if estado:
        return f"{texto} ({estado})"
    return texto


def _mensaje_orientacion_cv(analisis: dict) -> str:
    total = analisis.get("total_habilidades", 0) or 0
    habilidades = analisis.get("habilidades_detectadas") or []
    perfil = analisis.get("perfil_profesional") or {}
    perfiles = perfil.get("perfiles_recomendados") or []

    if total == 0 or not habilidades:
        return (
            "Orientación: no se identificaron habilidades técnicas en el documento. "
            "Te recomendamos incluir tus conocimientos, herramientas y tecnologías "
            "de forma clara en tu hoja de vida para mejorar el análisis."
        )

    if perfiles:
        return (
            "Orientación: tu perfil profesional fue identificado a partir de las habilidades detectadas. "
            "Cuando estén disponibles, podrás usar las recomendaciones laborales y el simulador de entrevistas "
            "para continuar tu proceso."
        )

    return (
        "Orientación: se detectaron habilidades, pero se necesita más información para definir un perfil específico. "
        "Considera detallar mejor tus competencias técnicas en tu hoja de vida."
    )


def formatear_resultado_cv(nombre_documento: str, analisis: dict) -> str:
    habilidades = analisis.get("habilidades_detectadas") or []
    total = analisis.get("total_habilidades", len(habilidades))
    perfil = analisis.get("perfil_profesional") or {}

    if habilidades:
        habilidades_texto = ", ".join(habilidades)
    else:
        habilidades_texto = "No se identificaron habilidades técnicas."

    perfil_texto = _formatear_perfil(perfil)
    orientacion = _mensaje_orientacion_cv(analisis)

    return (
        "Análisis de hoja de vida completado\n\n"
        f"Nombre del documento: {nombre_documento}\n"
        f"Habilidades identificadas: {habilidades_texto}\n"
        f"Cantidad de habilidades encontradas: {total}\n"
        f"Perfil profesional identificado: {perfil_texto}\n\n"
        f"{orientacion}"
    )


def dividir_mensaje_telegram(texto: str, limite: int = 4000) -> list[str]:
    """Divide un texto largo en partes seguras para Telegram."""
    if len(texto) <= limite:
        return [texto]

    partes = []
    actual = ""
    for linea in texto.split("\n"):
        candidata = linea if not actual else f"{actual}\n{linea}"
        if len(candidata) <= limite:
            actual = candidata
            continue
        if actual:
            partes.append(actual)
            actual = ""
        if len(linea) <= limite:
            actual = linea
        else:
            for i in range(0, len(linea), limite):
                partes.append(linea[i:i + limite])
    if actual:
        partes.append(actual)
    return partes


def _formatear_lista_habilidades(habilidades) -> str:
    if not habilidades:
        return "Ninguna"
    if isinstance(habilidades, list):
        return ", ".join(str(h) for h in habilidades) if habilidades else "Ninguna"
    return str(habilidades)


def formatear_recomendaciones_laborales(resultado: dict) -> str:
    recomendaciones = resultado.get("recomendaciones") or []
    encabezado = (
        "Recomendaciones laborales (ejemplos académicos)\n\n"
        "IMPORTANTE: Las ofertas mostradas son demostrativas y forman parte de un catálogo académico. "
        "No corresponden a vacantes laborales reales.\n"
    )

    if not recomendaciones:
        return encabezado + "\nNo se encontraron recomendaciones para mostrar."

    bloques = [encabezado]
    for idx, rec in enumerate(recomendaciones, start=1):
        coincidentes = _formatear_lista_habilidades(rec.get("habilidades_coincidentes"))
        faltantes = _formatear_lista_habilidades(rec.get("habilidades_faltantes"))
        bloque = (
            f"\n{idx}. {rec.get('cargo', 'Cargo no disponible')}\n"
            f"Empresa: {rec.get('empresa', 'No disponible')}\n"
            f"Modalidad: {rec.get('modalidad', 'No disponible')}\n"
            f"Porcentaje de compatibilidad: {rec.get('porcentaje_compatibilidad', 0)}%\n"
            f"Habilidades coincidentes: {coincidentes}\n"
            f"Habilidades que le faltan al candidato: {faltantes}\n"
        )
        bloques.append(bloque)

    return "".join(bloques)
