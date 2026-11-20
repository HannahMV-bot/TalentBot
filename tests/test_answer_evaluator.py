from backend.app.services.answer_evaluator import evaluar_respuesta


def _assert_estructura_evaluada(resultado, pregunta):
    assert resultado["pregunta"] == pregunta
    assert isinstance(resultado["retroalimentacion"], str)
    assert resultado["retroalimentacion"].strip()
    assert "estado" in resultado
    assert isinstance(resultado.get("fortalezas"), list)
    assert isinstance(resultado.get("conceptos_correctos"), list)
    assert isinstance(resultado.get("conceptos_faltantes"), list)
    assert isinstance(resultado.get("recomendacion"), str)
    assert "Fortalezas:" in resultado["retroalimentacion"]
    assert "Conceptos que faltaron" in resultado["retroalimentacion"]
    assert "Recomendación:" in resultado["retroalimentacion"]


def test_respuesta_basica_correcta_react_obtiene_puntuacion_alta():
    pregunta = "¿Qué es React y para qué se utiliza?"
    respuesta = (
        "React es una biblioteca de JavaScript que se utiliza para crear interfaces de usuario "
        "dinámicas e interactivas en páginas y aplicaciones web."
    )

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert resultado["puntuacion"] >= 80
    assert resultado["estado"] == "Respuesta correcta"


def test_respuesta_correcta_pero_incompleta_obtiene_puntuacion_parcial_razonable():
    pregunta = "¿Qué es React y para qué se utiliza?"
    respuesta = "React es una biblioteca de JavaScript."

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert 30 <= resultado["puntuacion"] < 70
    assert resultado["estado"] in {"Respuesta parcial", "Respuesta incorrecta"}
    assert resultado["conceptos_faltantes"]


def test_definicion_correcta_de_componente_obtiene_buena_puntuacion():
    pregunta = "¿Qué es un componente en React?"
    respuesta = (
        "Un componente en React es una pieza reutilizable de la interfaz que encapsula su lógica "
        "y puede retornar la vista; por ejemplo, un botón o una tarjeta que se usa en varias partes."
    )

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert resultado["puntuacion"] >= 75
    assert resultado["estado"] == "Respuesta correcta"
    assert resultado["conceptos_correctos"]


def test_definicion_correcta_de_state_obtiene_buena_puntuacion():
    pregunta = "¿Qué es el estado (state) en React?"
    respuesta = (
        "El state es la información o los datos que pueden cambiar dentro de un componente "
        "y, cuando se actualizan, hacen que la interfaz se vuelva a renderizar para reflejar esos cambios."
    )

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert resultado["puntuacion"] >= 75
    assert resultado["estado"] == "Respuesta correcta"
    assert resultado["conceptos_correctos"]


def test_respuesta_responsiva_es_identificada_como_insuficiente():
    pregunta = "¿Cómo harías que una página web sea adaptable?"
    respuesta = "Responsiva"

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert resultado["puntuacion"] < 40
    assert resultado["estado"] != "Respuesta correcta"
    retro = resultado["retroalimentacion"]
    assert "identifica el tema" in retro.lower()
    assert "necesita una explicación más completa" in retro.lower()
    assert "media queries" in retro.lower()
    assert "flexbox" in retro.lower()
    assert "grid" in retro.lower()
    assert "unidades relativas" in retro.lower()


def test_explicacion_completa_de_diseno_responsive_obtiene_puntuacion_alta():
    pregunta = "¿Cómo harías que una página web sea adaptable?"
    respuesta = (
        "Usaría diseño responsive con media queries para aplicar estilos según el tamaño de pantalla, "
        "un layout flexible con Flexbox o Grid, unidades relativas como porcentajes o rem, "
        "y la meta viewport para que el contenido se ajuste en móviles, tablets y escritorio."
    )

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert resultado["puntuacion"] >= 85
    assert resultado["estado"] == "Respuesta correcta"


def test_respuesta_incorrecta_no_obtiene_puntuacion_alta():
    pregunta = "¿Qué es una API REST y para qué se utiliza?"
    respuesta = "Es un programa para diseñar imágenes y editar videos."

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert resultado["puntuacion"] < 40
    assert resultado["estado"] == "Respuesta incorrecta"


def test_lista_de_palabras_tecnicas_sin_explicacion_no_recibe_puntuacion_alta():
    pregunta = "¿Qué es React y para qué se utiliza?"
    respuesta = "React JavaScript componentes interfaces estado props hooks"

    resultado = evaluar_respuesta(pregunta, respuesta)

    _assert_estructura_evaluada(resultado, pregunta)
    assert resultado["puntuacion"] is not None
    assert resultado["puntuacion"] < 50
    assert resultado["estado"] != "Respuesta correcta"


def test_pregunta_sin_criterios_no_recibe_puntuacion_inventada():
    pregunta = "¿Cuál es tu mayor fortaleza como profesional?"
    respuesta = "Soy una persona responsable, comprometida y con ganas de aprender."

    resultado = evaluar_respuesta(pregunta, respuesta)

    assert resultado["pregunta"] == pregunta
    assert resultado["puntuacion"] is None
    assert resultado["estado"] == "Pregunta no reconocida"
    assert isinstance(resultado["retroalimentacion"], str)
    assert "No existen criterios" in resultado["retroalimentacion"]


def test_respuesta_vacia_sigue_siendo_manejada():
    pregunta = "¿Qué es el estado (state) en React?"
    respuesta = "   "

    resultado = evaluar_respuesta(pregunta, respuesta)

    assert resultado["pregunta"] == pregunta
    assert resultado["puntuacion"] == 0
    assert resultado["estado"] == "Respuesta vacía"
    assert "Debes escribir una respuesta" in resultado["retroalimentacion"]


def test_compatibilidad_preguntas_existentes_backend():
    pregunta = "¿Qué es una API REST y para qué se utiliza?"
    respuesta = (
        "Una API REST permite la comunicación entre aplicaciones "
        "mediante solicitudes HTTP entre un cliente y un servidor."
    )

    resultado = evaluar_respuesta(pregunta, respuesta)

    assert resultado["pregunta"] == pregunta
    assert 0 <= resultado["puntuacion"] <= 100
    assert isinstance(resultado["retroalimentacion"], str)
    assert resultado["estado"] is not None
