import pymupdf as fitz


def extraer_texto_pdf(contenido_pdf: bytes) -> str:
    """
    Extrae el texto de una hoja de vida en formato PDF.

    Args:
        contenido_pdf: Contenido del archivo PDF en bytes.

    Returns:
        Texto extraído del documento.
    """

    try:
        # Abrir el documento PDF desde la memoria
        documento = fitz.open(
            stream=contenido_pdf,
            filetype="pdf"
        )

        texto_completo = ""

        # Recorrer todas las páginas del documento
        for pagina in documento:
            texto_completo += pagina.get_text() + "\n"

        documento.close()

        # Comprobar si se encontró texto
        if not texto_completo.strip():
            raise ValueError(
                "No se encontró texto en el PDF."
            )

        return texto_completo.strip()

    except Exception as error:
        raise ValueError(
            f"No fue posible leer el PDF: {error}"
        ) from error
