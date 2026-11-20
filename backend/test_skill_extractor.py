from app.services.skill_extractor import detectar_habilidades


# Hoja de vida de prueba
texto_cv = """
Soy desarrolladora de software.

Tengo conocimientos en Python, SQL,
JavaScript, React, Node.js y Git.

También tengo experiencia utilizando
FastAPI y Machine Learning.
"""

# Analizar las habilidades
habilidades = detectar_habilidades(texto_cv)

# Mostrar los resultados
print("===== ANALISIS DE HABILIDADES =====")

if habilidades:
    print("Habilidades identificadas:")

    for habilidad in habilidades:
        print(f"- {habilidad}")
else:
    print("No se encontraron habilidades.")

print("===================================")
print("Analisis completado correctamente.")
