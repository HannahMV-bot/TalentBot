from backend.app.services.skill_extractor import detectar_habilidades


def test_detectar_habilidades_tecnicas():
    # Hoja de vida de prueba
    texto_cv = """
    Soy desarrolladora de software.

    Tengo conocimientos en Python, SQL,
    JavaScript, React, Node.js y Git.

    También tengo experiencia utilizando
    FastAPI y Machine Learning.
    """

    # Ejecutar la extracción
    habilidades = detectar_habilidades(texto_cv)

    # Verificar las habilidades detectadas
    habilidades_esperadas = [
        "Python",
        "JavaScript",
        "SQL",
        "React",
        "Node.js",
        "FastAPI",
        "Git",
        "Machine Learning"
    ]

    for habilidad in habilidades_esperadas:
        assert habilidad in habilidades

    assert len(habilidades) == 8


def test_no_detectar_habilidades_inexistentes():
    texto_cv = "Tengo experiencia en comunicación y trabajo en equipo."

    habilidades = detectar_habilidades(texto_cv)

    assert habilidades == []
