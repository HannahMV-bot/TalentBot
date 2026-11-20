import pymupdf as fitz
import pytest

from backend.app.services.cv_reader import extraer_texto_pdf


def test_extraer_texto_pdf_correctamente():
    # Crear un PDF de prueba
    documento = fitz.open()
    pagina = documento.new_page()

    pagina.insert_text(
        (72, 72),
        "Nombre: Ana Martinez\n"
        "Profesion: Desarrolladora de software\n"
        "Habilidades: Python, SQL, JavaScript\n"
        "Experiencia: 2 anos"
    )

    # Convertir el documento a bytes
    contenido_pdf = documento.tobytes()
    documento.close()

    # Extraer el texto
    texto = extraer_texto_pdf(contenido_pdf)

    # Verificar que el texto se haya extraído
    assert "Ana Martinez" in texto
    assert "Python" in texto
    assert "SQL" in texto
    assert "JavaScript" in texto


def test_rechazar_pdf_sin_texto():
    # Crear un PDF sin contenido textual
    documento = fitz.open()
    documento.new_page()

    contenido_pdf = documento.tobytes()
    documento.close()

    # Verificar que se genere el error esperado
    with pytest.raises(ValueError, match="No fue posible leer el PDF"):
        extraer_texto_pdf(contenido_pdf)
