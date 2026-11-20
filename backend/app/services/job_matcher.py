def calcular_compatibilidad(
    habilidades_candidato: list,
    habilidades_oferta: list
) -> dict:
    """
    Calcula el porcentaje de compatibilidad entre
    las habilidades de un candidato y una oferta laboral.
    """

    # Convertir las habilidades a minúsculas
    candidato = {
        habilidad.lower() for habilidad in habilidades_candidato
    }

    oferta = {
        habilidad.lower() for habilidad in habilidades_oferta
    }

    # Validar que la oferta tenga requisitos
    if not oferta:
        return {
            "porcentaje_compatibilidad": 0,
            "habilidades_coincidentes": [],
            "habilidades_faltantes": [],
            "estado": "La oferta no tiene requisitos"
        }

    # Identificar coincidencias
    coincidentes = candidato.intersection(oferta)

    # Identificar habilidades faltantes
    faltantes = oferta - candidato

    # Calcular porcentaje
    porcentaje = round(
        (len(coincidentes) / len(oferta)) * 100,
        2
    )

    return {
        "porcentaje_compatibilidad": porcentaje,
        "habilidades_coincidentes": sorted(coincidentes),
        "habilidades_faltantes": sorted(faltantes),
        "estado": "Compatibilidad calculada"
    }
