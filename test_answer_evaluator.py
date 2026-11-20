from backend.app.services.answer_evaluator import evaluar_respuesta

# Pregunta de entrevista
pregunta = "¿Qué es una API REST y para qué se utiliza?"

# Respuesta simulada del candidato
respuesta = (
    "Una API REST permite la comunicación entre aplicaciones "
    "mediante solicitudes HTTP entre un cliente y un servidor."
)

# Evaluar respuesta
resultado = evaluar_respuesta(pregunta, respuesta)

# Mostrar resultados
print("EVALUACIÓN DE ENTREVISTA - TALENTBOT")
print("------------------------------------")
print("Pregunta:", resultado["pregunta"])
print("Respuesta:", respuesta)
print("Puntuación:", resultado["puntuacion"], "%")
print("Palabras clave:", resultado.get("palabras_clave_encontradas", []))
print("Retroalimentación:", resultado["retroalimentacion"])
print("Estado:", resultado["estado"])
