# TalentBot

**Chatbot:** NOVA AI  
**Interfaz principal:** Telegram

TalentBot es un proyecto académico desarrollado en Python para la orientación laboral mediante un asistente conversacional. Su interfaz principal es el chatbot **NOVA AI**, que permite a los usuarios interactuar por Telegram para analizar hojas de vida, recibir recomendaciones laborales demostrativas, practicar entrevistas y consultar su historial.

## Descripción general

TalentBot integra un bot de Telegram con servicios de backend y persistencia en SQLite para ofrecer un flujo de acompañamiento básico en procesos de empleabilidad. El sistema reutiliza servicios existentes de lectura/procesamiento de CV, extracción de habilidades, clasificación de perfil, comparación con ofertas, simulación de entrevistas y evaluación de respuestas, manteniendo FastAPI como capa secundaria opcional sobre la misma lógica y base de datos.

## Objetivo general

Desarrollar un sistema de orientación laboral accesible desde Telegram que apoye a los usuarios en la identificación de su perfil profesional, la exploración de oportunidades laborales demostrativas y la práctica de entrevistas, a partir del análisis de su hoja de vida.

## Objetivos específicos

- Permitir el registro, inicio y cierre de sesión de usuarios desde Telegram con vinculación segura de cuentas.
- Procesar hojas de vida en formato PDF para extraer texto, identificar habilidades y clasificar el perfil profesional.
- Generar recomendaciones laborales demostrativas según las habilidades detectadas y mostrar su nivel de compatibilidad.
- Simular entrevistas por perfil profesional, registrar respuestas y entregar retroalimentación/evaluación cuando el evaluador lo permita.
- Consultar el historial de análisis, recomendaciones y entrevistas del usuario autenticado.
- Garantizar el aislamiento de la información entre usuarios y el uso seguro de credenciales/configuración.

## Problema que busca solucionar

Muchas personas requieren orientación inicial para interpretar su hoja de vida, reconocer habilidades relevantes, conocer posibles perfiles laborales y prepararse para entrevistas. TalentBot busca centralizar estas tareas en una interfaz conversacional sencilla (Telegram), reduciendo la necesidad de múltiples herramientas y facilitando un acompañamiento básico y automatizado con fines académicos.

## Funcionalidades principales

- **Registro e inicio de sesión:** creación de cuenta, autenticación y cierre de sesión desde conversaciones privadas en Telegram.
- **Asociación segura de cuentas de Telegram:** vinculación `telegram_id` ↔ usuario mediante una tabla independiente para controlar el acceso.
- **Análisis de hojas de vida PDF:** recepción de documentos PDF, extracción de texto, identificación de habilidades, clasificación de perfil y guardado de resultados.
- **Extracción de habilidades y clasificación profesional:** detección de habilidades técnicas y estimación de perfiles profesionales según coincidencias.
- **Recomendaciones laborales:** comparación de habilidades del usuario con un catálogo de ofertas y presentación de compatibilidad, coincidencias y habilidades faltantes.
- **Simulador de entrevistas:** generación de preguntas por perfil, respuesta pregunta a pregunta y registro de la entrevista.
- **Evaluación de respuestas:** retroalimentación y puntuación cuando el evaluador reconoce la pregunta; manejo de casos no reconocidos sin inventar puntuación.
- **Consulta de historial:** visualización del historial de análisis de CV, recomendaciones y entrevistas del usuario autenticado.

> **Importante:** las ofertas laborales actuales son **demostrativas** (catálogo académico) y **no corresponden a vacantes reales**.

## Tecnologías utilizadas

- **Lenguaje:** Python 3.10+ (probado en entorno con Python 3.12)
- **Interfaz conversacional:** `python-telegram-bot` (bot NOVA AI)
- **Backend/API secundaria:** FastAPI, Uvicorn
- **Base de datos y ORM:** SQLite, SQLAlchemy
- **Procesamiento de PDF:** PyMuPDF (`pymupdf`)
- **Seguridad y autenticación:** `pwdlib[argon2]`, `python-jose[cryptography]`, variables de entorno con `python-dotenv`
- **Validación:** `email-validator`
- **Pruebas automatizadas:** `pytest`

## Arquitectura del sistema

- **Interfaz principal (NOVA AI - Telegram):** gestiona la interacción con el usuario mediante comandos, menús y flujos conversacionales (`ConversationHandler`), validando autenticación y asociación de cuenta antes de acceder a funcionalidades protegidas.
- **Servicios de negocio (backend):** encapsulan la lógica de análisis de CV, extracción de habilidades, clasificación de perfiles, recomendación/evaluación de entrevistas, gestión de usuarios y persistencia/consulta de resultados.
- **Capa de persistencia:** modelos SQLAlchemy y base de datos SQLite local (`talentbot.db`) para usuarios, vínculos de Telegram, hojas de vida, análisis, ofertas, recomendaciones, entrevistas y respuestas.
- **API secundaria (FastAPI):** expone rutas HTTP que reutilizan los mismos servicios y modelos (útil para mantenimiento/pruebas de integración del backend), sin ser la interfaz principal del usuario final.

## Estructura de carpetas

```text
.
├── backend/
│   └── app/
│       ├── api/                 # Rutas FastAPI (capa secundaria)
│       ├── database/            # Conexión y modelos SQLAlchemy
│       ├── services/            # Lógica de negocio y servicios compartidos
│       ├── config.py            # Configuración (JWT/secretos de backend)
│       └── main.py              # Aplicación FastAPI
├── telegram_bot/                # Bot NOVA AI (interfaz principal)
│   ├── auth.py                  # Sesión/autenticación en Telegram
│   ├── bot.py                   # Punto de entrada y registro de handlers
│   ├── config.py                # Carga de configuración del bot
│   ├── handlers.py              # Flujos y lógica de interacción
│   ├── keyboards.py             # Teclados y menús
│   ├── states.py                # Estados de conversación
│   └── utils.py                 # Utilidades y formateo de mensajes
├── tests/                       # Pruebas automatizadas (pytest)
├── create_database.py           # Creación/verificación de tablas SQLite
├── requirements.txt             # Dependencias del proyecto
├── .env.example                 # Plantilla de variables de entorno (sin secretos)
├── .gitignore                   # Exclusiones para Git
└── README.md                    # Documentación del proyecto
```

> Nota: `.env`, `talentbot.db` y `.venv/` son archivos/carpetas locales esperados en desarrollo, pero están excluidos del control de versiones.

## Modelo de funcionamiento

1. El usuario inicia conversación con **NOVA AI** en Telegram y accede al menú principal.
2. Se registra o inicia sesión; el sistema vincula de forma segura su cuenta de Telegram con su usuario en la base de datos.
3. Para análisis de CV, el usuario envía un PDF; el bot lo procesa con los servicios de lectura, extracción y clasificación, y guarda los resultados.
4. Con base en el último análisis, el sistema genera recomendaciones laborales **demostrativas** y permite simular entrevistas por perfil.
5. Durante la entrevista, las respuestas se registran y se evalúan cuando el evaluador dispone de criterios; los casos no reconocidos se guardan sin puntuación inventada.
6. El usuario puede consultar su historial (CV, recomendaciones, entrevistas), con acceso restringido a su propia información.

## Requisitos previos

- Python 3.10 o superior (recomendado; probado en Python 3.12)
- `pip` y entorno virtual (`venv`)
- Cuenta de Telegram y token de bot creado con [@BotFather](https://t.me/BotFather)
- Sistema operativo con soporte para Python (desarrollo y pruebas realizadas en entorno Windows)

## Instalación paso a paso

1. **Clonar el repositorio**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd <CARPETA_DEL_PROYECTO>
   ```

2. **Crear y activar un entorno virtual**
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Actualizar pip e instalar dependencias**
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Configuración de variables de entorno

1. Crear un archivo `.env` en la raíz del proyecto a partir de la plantilla:
   - Windows (PowerShell): `Copy-Item .env.example .env`
   - Linux/macOS: `cp .env.example .env`

2. Completar las variables en `.env`:

| Variable | Descripción | Ejemplo (no sensible) |
|---|---|---|
| `SECRET_KEY` | Clave secreta usada por los componentes de autenticación/JWT del backend FastAPI (capa secundaria). Debe ser privada y aleatoria. | `cambia_esta_clave_por_una_segura` |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram proporcionado por BotFather para ejecutar NOVA AI. | `123456789:ABCDefGhIjKlMnOpQrStUvWxYz` *(formato de ejemplo, no real)* |

> No compartas ni publiques valores reales de `.env`.

## Creación de la base de datos

Desde la raíz del proyecto (con el entorno virtual activo):

```bash
python create_database.py
```

Este script crea/verifica las tablas necesarias en la base de datos SQLite local (`talentbot.db`). Si la base de datos ya existe, la operación es aditiva para tablas faltantes según la configuración actual del proyecto.

## Ejecución del bot (NOVA AI)

Desde la raíz del proyecto:

```bash
python -m telegram_bot.bot
```

En Windows (usando el intérprete del entorno virtual del proyecto):

```powershell
.\.venv\Scripts\python.exe -m telegram_bot.bot
```

Requisitos: `.env` configurado con `TELEGRAM_BOT_TOKEN` válido y dependencias instaladas. El bot se ejecuta por polling y atiende conversaciones en Telegram.

## Ejecución de FastAPI (servicio secundario)

FastAPI se conserva como **capa secundaria** que reutiliza la misma lógica y base de datos. Para ejecutarla desde la raíz del proyecto:

```bash
uvicorn backend.app.main:app --reload
```

La API quedará disponible (por defecto) en `http://127.0.0.1:8000`. Esta interfaz no reemplaza a NOVA AI como interfaz principal del usuario.

## Ejecución de pruebas automatizadas

Desde la raíz del proyecto:

```bash
pytest -q
```

En Windows (entorno virtual del proyecto):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas automatizadas actuales validan servicios y flujos del bot mediante `pytest`, incluyendo casos con mocks y bases de datos aisladas en memoria según corresponda. **Estas pruebas no equivalen a pruebas en tiempo real con la API de Telegram** ni a una conversación real con usuarios; para validar el funcionamiento en producción/uso real se requiere ejecutar NOVA AI con un token válido y realizar pruebas manuales en Telegram.

## Consideraciones de seguridad

- No versionar `.env`, `talentbot.db` ni otras bases de datos locales.
- No incluir tokens, contraseñas ni claves secretas en el código fuente ni en la documentación pública.
- Las contraseñas de usuarios se almacenan mediante hash seguro (Argon2) a través de los servicios existentes.
- El acceso a funcionalidades protegidas en Telegram requiere autenticación y vinculación válida `telegram_id` ↔ usuario.
- La información (análisis, recomendaciones, entrevistas e historial) se consulta filtrada por el usuario autenticado para evitar accesos cruzados.
- Los flujos sensibles (registro/inicio de sesión) están diseñados para usarse en conversaciones privadas y evitan exponer contraseñas en respuestas.
- El repositorio incluye `.env.example` sin credenciales reales como plantilla de configuración.

## Limitaciones actuales del sistema

- **Ofertas laborales demostrativas:** el catálogo de ofertas es académico y no representa vacantes reales ni se conecta a fuentes externas de empleo.
- **Extracción y clasificación basadas en reglas:** la identificación de habilidades y perfiles depende de catálogos/patrones definidos en los servicios actuales; puede no cubrir todos los casos o formatos de CV.
- **Evaluación de entrevistas acotada:** el evaluador utiliza criterios predefinidos para ciertas preguntas; algunas respuestas pueden quedar sin puntuación automática (se registran sin inventar resultados).
- **Dependencia del formato del CV:** el análisis se orienta a documentos PDF con texto extraíble; PDFs escaneados o sin texto legible pueden no procesarse correctamente.
- **Persistencia local:** utiliza SQLite local, adecuada para fines académicos/desarrollo, sin configuración de despliegue distribuido.
- **Alcance funcional:** no incluye recuperación de contraseña desde Telegram, notificaciones externas, panel web de usuario ni integración con servicios de empleo en tiempo real.
- **Operación del bot:** requiere ejecución activa del proceso y un token válido de Telegram; las pruebas automatizadas no sustituyen pruebas manuales en la plataforma.
