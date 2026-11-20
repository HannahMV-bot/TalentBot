from backend.app.services.cv_reader import extraer_texto_pdf
from backend.app.services.skill_extractor import detectar_habilidades
from backend.app.services.profile_classifier import clasificar_perfil


def analizar_hoja_vida(contenido_pdf: bytes) -> dict:
    """
    Analiza una hoja de vida en PDF.

    Extrae el texto, identifica las habilidades
    técnicas y recomienda un perfil profesional.
    """

    # Paso 1: Extraer el texto del PDF
    texto = extraer_texto_pdf(contenido_pdf)

    # Paso 2: Identificar las habilidades
    habilidades = detectar_habilidades(texto)

    # Paso 3: Clasificar el perfil profesional
    perfil = clasificar_perfil(habilidades)

    # Paso 4: Organizar los resultados
    resultado = {
        "texto_extraido": texto,
        "habilidades_detectadas": habilidades,
        "total_habilidades": len(habilidades),
        "perfil_profesional": perfil,
        "estado": "Analisis completado"
    }

    return resultado
