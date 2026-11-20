def clasificar_perfil(habilidades: list) -> dict:
    """
    Identifica los perfiles profesionales relacionados
    con las habilidades detectadas.
    """

    habilidades = [habilidad.lower() for habilidad in habilidades]

    perfiles = {
        "Desarrollador Frontend": [
            "html", "css", "javascript", "react"
        ],
        "Desarrollador Backend": [
            "python", "fastapi", "django", "node.js", "sql"
        ],
        "Analista de Datos": [
            "python", "sql", "excel", "power bi"
        ],
        "Especialista en Machine Learning": [
            "python", "machine learning", "scikit-learn"
        ]
    }

    resultados = {}

    for perfil, requisitos in perfiles.items():
        coincidencias = [
            habilidad for habilidad in requisitos
            if habilidad in habilidades
        ]

        resultados[perfil] = len(coincidencias)

    mayor_puntuacion = max(resultados.values())

    if mayor_puntuacion == 0:
        return {
            "perfiles_recomendados": [],
            "coincidencias": 0,
            "estado": "Se necesitan más habilidades"
        }

    perfiles_recomendados = [
        perfil
        for perfil, puntuacion in resultados.items()
        if puntuacion == mayor_puntuacion
    ]

    return {
        "perfiles_recomendados": perfiles_recomendados,
        "coincidencias": mayor_puntuacion,
        "estado": (
            "Varios perfiles identificados"
            if len(perfiles_recomendados) > 1
            else "Perfil identificado"
        )
    }
