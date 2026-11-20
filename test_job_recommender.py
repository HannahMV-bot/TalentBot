from backend.app.services.job_recommender import recomendar_ofertas

# Habilidades detectadas en la hoja de vida
habilidades_candidato = [
    "Python",
    "SQL",
    "FastAPI",
    "Git",
    "JavaScript",
    "React"
]

# Obtener recomendaciones
recomendaciones = recomendar_ofertas(habilidades_candidato)

# Mostrar resultados
print("RECOMENDACIONES LABORALES DE TALENTBOT")
print("--------------------------------------")

for oferta in recomendaciones:
    print("\nCargo:", oferta["cargo"])
    print("Empresa:", oferta["empresa"])
    print("Modalidad:", oferta["modalidad"])
    print(
        "Compatibilidad:",
        oferta["porcentaje_compatibilidad"],
        "%"
    )
    print(
        "Habilidades coincidentes:",
        oferta["habilidades_coincidentes"]
    )
    print(
        "Habilidades faltantes:",
        oferta["habilidades_faltantes"]
    )
