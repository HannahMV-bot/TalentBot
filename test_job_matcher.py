from backend.app.services.job_matcher import calcular_compatibilidad

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

# Calcular compatibilidad
resultado = calcular_compatibilidad(
    habilidades_candidato,
    habilidades_oferta
)

# Mostrar resultados
print("ANÁLISIS DE COMPATIBILIDAD LABORAL")
print("----------------------------------")
print("Porcentaje:", resultado["porcentaje_compatibilidad"], "%")
print("Habilidades coincidentes:", resultado["habilidades_coincidentes"])
print("Habilidades faltantes:", resultado["habilidades_faltantes"])
print("Estado:", resultado["estado"])
