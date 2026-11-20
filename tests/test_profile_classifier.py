from backend.app.services.profile_classifier import clasificar_perfil


def test_clasificar_perfil_backend():
    # Simulamos las habilidades de una persona
    habilidades = [
        "Python",
        "FastAPI",
        "SQL",
        "Node.js"
    ]

    # Ejecutamos el clasificador
    resultado = clasificar_perfil(habilidades)

    # Verificamos los resultados
    assert resultado["perfiles_recomendados"] == [
        "Desarrollador Backend"
    ]

    assert resultado["coincidencias"] == 4

    assert resultado["estado"] == "Perfil identificado"
