import re


# Catálogo inicial de habilidades profesionales
HABILIDADES = [
    "Python",
    "Java",
    "JavaScript",
    "SQL",
    "HTML",
    "CSS",
    "React",
    "Node.js",
    "FastAPI",
    "Django",
    "Git",
    "Docker",
    "Excel",
    "Power BI",
    "Machine Learning",
    "C++",
    "C#"
]


def detectar_habilidades(texto: str) -> list:
    """
    Identifica habilidades técnicas dentro de un texto.

    Args:
        texto: Contenido extraído de una hoja de vida.

    Returns:
        Lista de habilidades encontradas.
    """

    habilidades_encontradas = []

    # Convertir el texto a minúsculas
    texto = texto.lower()

    # Recorrer el catálogo de habilidades
    for habilidad in HABILIDADES:

        patron = (
            r"(?<!\w)"
            + re.escape(habilidad.lower())
            + r"(?!\w)"
        )

        if re.search(patron, texto):
            habilidades_encontradas.append(habilidad)

    return habilidades_encontradas
