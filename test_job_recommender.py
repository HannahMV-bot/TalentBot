from backend.app.services.job_recommender import recomendar_ofertas


def test_recomendar_ofertas_laborales():
    # Habilidades detectadas en la hoja de vida
    habilidades_candidato = [
        "Python",
        "SQL",
        "FastAPI",
        "Git",
        "JavaScript",
        "React"
    ]

    # Ejecutar el recomendador
    recomendaciones = recomendar_ofertas(habilidades_candidato)

    # Verificar que se generen recomendaciones
    assert len(recomendaciones) > 0

    # Comprobar que cada oferta tenga los datos necesarios
    for oferta in recomendaciones:
        assert "cargo" in oferta
        assert "empresa" in oferta
        assert "modalidad" in oferta
        assert "porcentaje_compatibilidad" in oferta
        assert 0 <= oferta["porcentaje_compatibilidad"] <= 100

    # Comprobar que estén ordenadas de mayor a menor compatibilidad
    porcentajes = [
        oferta["porcentaje_compatibilidad"]
        for oferta in recomendaciones
    ]

    assert porcentajes == sorted(porcentajes, reverse=True)
