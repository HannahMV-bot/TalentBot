from backend.app.services.profile_classifier import clasificar_perfil

# Simulamos las habilidades de una persona
habilidades = [
    "Python",
    "FastAPI",
    "SQL",
    "Node.js"
]

# Ejecutamos el clasificador
resultado = clasificar_perfil(habilidades)

# Mostramos los resultados
print("RESULTADO DEL CLASIFICADOR")
print("--------------------------")
print("Habilidades:", habilidades)
print("Perfil recomendado:", resultado["perfil_recomendado"])
print("Coincidencias:", resultado["coincidencias"])
print("Estado:", resultado["estado"])
