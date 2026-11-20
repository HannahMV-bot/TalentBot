from backend.app.services.job_matcher import calcular_compatibilidad


# Catálogo inicial de ofertas laborales
OFERTAS_LABORALES = [
    {
        "id": 1,
        "cargo": "Desarrollador Backend Junior",
        "empresa": "Tech Solutions",
        "modalidad": "Remoto",
        "habilidades": [
            "Python", "SQL", "FastAPI", "Git", "Docker"
        ]
    },
    {
        "id": 2,
        "cargo": "Desarrollador Frontend Junior",
        "empresa": "Digital Creators",
        "modalidad": "Híbrido",
        "habilidades": [
            "HTML", "CSS", "JavaScript", "React", "Git"
        ]
    },
    {
        "id": 3,
        "cargo": "Analista de Datos Junior",
        "empresa": "Data Company",
        "modalidad": "Presencial",
        "habilidades": [
            "Python", "SQL", "Excel", "Power BI"
        ]
    },
    {
        "id": 4,
        "cargo": "Especialista en Machine Learning",
        "empresa": "AI Technology",
        "modalidad": "Remoto",
        "habilidades": [
            "Python", "Machine Learning", "SQL",
            "Scikit-learn"
        ]
    }
]


def recomendar_ofertas(habilidades_candidato: list) -> list:
    """
    Compara las habilidades del candidato con las ofertas
    laborales y devuelve las más compatibles.
    """

    recomendaciones = []

    for oferta in OFERTAS_LABORALES:

        resultado = calcular_compatibilidad(
            habilidades_candidato,
            oferta["habilidades"]
        )

        recomendacion = {
            "id": oferta["id"],
            "cargo": oferta["cargo"],
            "empresa": oferta["empresa"],
            "modalidad": oferta["modalidad"],
            "porcentaje_compatibilidad": resultado[
                "porcentaje_compatibilidad"
            ],
            "habilidades_coincidentes": resultado[
                "habilidades_coincidentes"
            ],
            "habilidades_faltantes": resultado[
                "habilidades_faltantes"
            ]
        }

        recomendaciones.append(recomendacion)

    # Ordenar desde la oferta más compatible
    recomendaciones.sort(
        key=lambda oferta: oferta["porcentaje_compatibilidad"],
        reverse=True
    )

    return recomendaciones
