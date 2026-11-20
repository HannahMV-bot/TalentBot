from backend.app.services.interview_simulator import generar_preguntas


def test_generar_preguntas_backend():
    # Perfil profesional del candidato
    perfil = "Desarrollador Backend"

    # Ejecutar el simulador
    resultado = generar_preguntas(perfil)

    # Verificar los resultados
    assert resultado["perfil"] == perfil
    assert resultado["estado"] is not None
    assert resultado["total_preguntas"] == 5
    assert len(resultado["preguntas"]) == 5
    assert all(
        isinstance(pregunta, str) and pregunta.strip()
        for pregunta in resultado["preguntas"]
    )
