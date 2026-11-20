from backend.app.services.answer_evaluator import evaluar_respuesta


def test_evaluar_respuesta_api_rest():
    # Pregunta de entrevista
    pregunta = "¿Qué es una API REST y para qué se utiliza?"

    # Respuesta simulada del candidato
    respuesta = (
        "Una API REST permite la comunicación entre aplicaciones "
        "mediante solicitudes HTTP entre un cliente y un servidor."
    )

    # Ejecutar la evaluación
    resultado = evaluar_respuesta(pregunta, respuesta)

    # Verificar los resultados
    assert resultado["pregunta"] == pregunta
    assert resultado["puntuacion"] >= 0
    assert resultado["puntuacion"] <= 100
    assert isinstance(resultado["retroalimentacion"], str)
    assert resultado["estado"] is not None
