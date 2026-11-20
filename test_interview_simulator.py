from backend.app.services.interview_simulator import generar_preguntas

# Perfil profesional del candidato
perfil = "Desarrollador Backend"

# Generar preguntas
resultado = generar_preguntas(perfil)

# Mostrar resultados
print("SIMULADOR DE ENTREVISTAS - TALENTBOT")
print("------------------------------------")
print("Perfil:", resultado["perfil"])
print("Total de preguntas:", resultado.get("total_preguntas", 0))
print("Estado:", resultado["estado"])

print("\nPREGUNTAS DE ENTREVISTA:")

for numero, pregunta in enumerate(resultado["preguntas"], start=1):
    print(f"{numero}. {pregunta}")
