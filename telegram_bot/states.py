"""Estados de conversación para los flujos del bot.

Se completarán en etapas posteriores según las funcionalidades implementadas.
"""

# Ejemplos de estados previstos (registro, login, análisis, entrevista, etc.)
(
    REGISTRO_NOMBRES,
    REGISTRO_APELLIDOS,
    REGISTRO_CORREO,
    REGISTRO_CONTRASENA,
    LOGIN_CORREO,
    LOGIN_CONTRASENA,
    ESPERANDO_CV,
    ENTREVISTA_PERFIL,
    ENTREVISTA_RESPUESTA,
    HISTORIAL_MENU,
) = range(10)
