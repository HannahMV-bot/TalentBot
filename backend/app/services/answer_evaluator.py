def evaluar_respuesta(pregunta: str, respuesta: str) -> dict:
    """
    Evalúa una respuesta de entrevista mediante
    palabras clave relacionadas con la pregunta.
    """

    if not respuesta.strip():
        return {
            "pregunta": pregunta,
            "puntuacion": 0,
            "retroalimentacion": "Debes escribir una respuesta.",
            "estado": "Respuesta vacía"
        }

    criterios = {
        "api rest": [
            "api", "http", "solicitud", "cliente", "servidor"
        ],
        "get y post": [
            "get", "post", "obtener", "enviar", "datos"
        ],
        "clave primaria": [
            "identificador", "unico", "registro", "tabla", "base de datos"
        ],
        "crud": [
            "crear", "leer", "actualizar", "eliminar"
        ],
        "errores": [
            "try", "except", "excepcion", "validacion", "error"
        ]
    }

    pregunta_lower = pregunta.lower()
    respuesta_lower = respuesta.lower()

    palabras_clave = []

    for tema, palabras in criterios.items():
        if tema in pregunta_lower:
            palabras_clave = palabras
            break

    if not palabras_clave:
        return {
            "pregunta": pregunta,
            "puntuacion": 0,
            "retroalimentacion": "No existen criterios para evaluar esta pregunta.",
            "estado": "Pregunta no reconocida"
        }

    coincidencias = [
        palabra for palabra in palabras_clave
        if palabra in respuesta_lower
    ]

    puntuacion = round(
        (len(coincidencias) / len(palabras_clave)) * 100
    )

    if puntuacion >= 70:
        retroalimentacion = "¡Muy bien! Tu respuesta contiene conceptos importantes."
    elif puntuacion >= 40:
        retroalimentacion = "Tu respuesta es parcialmente correcta. Puedes ampliarla."
    else:
        retroalimentacion = "Debes profundizar más en los conceptos de la pregunta."

    return {
        "pregunta": pregunta,
        "respuesta": respuesta,
        "puntuacion": puntuacion,
        "palabras_clave_encontradas": coincidencias,
        "retroalimentacion": retroalimentacion,
        "estado": "Evaluacion completada"
    }
