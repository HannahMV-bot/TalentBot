import pymupdf as fitz

from backend.app.services.cv_analyzer import analizar_hoja_vida


def test_analizar_hoja_vida_completa():
    # Crear una hoja de vida PDF de prueba
    documento = fitz.open()
    pagina = documento.new_page()

    pagina.insert_text(
        (72, 72),
        "Nombre: Laura Gomez\n"
        "Profesion: Ingeniera de software\n"
        "Habilidades: Python, SQL, JavaScript, React\n"
        "Experiencia: 3 anos\n"
        "Conocimientos: FastAPI, Git y Docker"
    )

    # Convertir el PDF a bytes
    contenido_pdf = documento.tobytes()
    documento.close()

    # Ejecutar el análisis de TalentBot
    resultado = analizar_hoja_vida(contenido_pdf)

    # Comprobar los resultados
    assert "Laura Gomez" in resultado["texto_extraido"]
    assert "Python" in resultado["habilidades_detectadas"]
    assert "SQL" in resultado["habilidades_detectadas"]
    assert "JavaScript" in resultado["habilidades_detectadas"]
    assert "React" in resultado["habilidades_detectadas"]
    assert resultado["total_habilidades"] >= 4
    assert resultado["estado"] == "Analisis completado"
    assert "perfil_profesional" in resultado
