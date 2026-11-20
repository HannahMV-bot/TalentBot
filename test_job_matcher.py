from backend.app.services.job_matcher import calcular_compatibilidad


def test_calcular_compatibilidad_laboral():
    # Habilidades que tiene el candidato
    habilidades_candidato = [
        "Python",
        "SQL",
        "FastAPI",
        "React",
        "Git"
    ]

    # Habilidades solicitadas por la empresa
    habilidades_oferta = [
        "Python",
        "SQL",
        "FastAPI",
        "Docker",
        "Git"
    ]

    # Ejecutar el cálculo
    resultado = calcular_compatibilidad(
        habilidades_candidato,
        habilidades_oferta
    )

    # Verificar los resultados
    assert resultado["porcentaje_compatibilidad"] == 80.0
    assert len(resultado["habilidades_coincidentes"]) == 4
    assert "docker" in resultado["habilidades_faltantes"]
    assert resultado["estado"] == "Compatibilidad calculada"
