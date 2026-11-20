import pymupdf as fitz

from app.services.cv_analyzer import analizar_hoja_vida


# Crear una hoja de vida de prueba
documento = fitz.open()

pagina = documento.new_page()

pagina.insert_text(
    (72, 72),
    "Nombre: Laura Gomez\n"
    "Profesion: Ingeniera de software\n"
    "Habilidades: Python, SQL, JavaScript, React\n"
    "Experiencia: 3 anos\n"
    "Conocimientos: FastAPI, Git y Docker"
)

# Convertir el PDF a bytes
contenido_pdf = documento.tobytes()

documento.close()


# Analizar la hoja de vida con TalentBot
resultado = analizar_hoja_vida(contenido_pdf)


# Mostrar el análisis
print("\n===== ANALISIS COMPLETO DE TALENTBOT =====")

print("\nTEXTO EXTRAIDO:")
print(resultado["texto_extraido"])

print("\nHABILIDADES DETECTADAS:")

for habilidad in resultado["habilidades_detectadas"]:
    print(f"- {habilidad}")

print("\nTOTAL DE HABILIDADES:")
print(resultado["total_habilidades"])

print("\nESTADO:")
print(resultado["estado"])

print("\n==========================================")
