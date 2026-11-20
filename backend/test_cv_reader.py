import pymupdf as fitz

from app.services.cv_reader import extraer_texto_pdf


# Crear un PDF de prueba
documento = fitz.open()

pagina = documento.new_page()

pagina.insert_text(
    (72, 72),
    "Nombre: Ana Martinez\n"
    "Profesion: Desarrolladora de software\n"
    "Habilidades: Python, SQL, JavaScript\n"
    "Experiencia: 2 anos"
)

# Convertir el documento a bytes
contenido_pdf = documento.tobytes()

documento.close()

# Utilizar nuestro lector de TalentBot
texto = extraer_texto_pdf(contenido_pdf)

# Mostrar los resultados
print("===== RESULTADO DEL ANALISIS =====")
print(texto)
print("==================================")
print("Prueba completada correctamente.")
