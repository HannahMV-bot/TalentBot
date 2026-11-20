import re
import unicodedata


def _normalizar(texto: str) -> str:
    """Normaliza texto para comparación: minúsculas y sin acentos."""
    texto = texto or ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _contar_palabras(texto: str) -> int:
    return len(re.findall(r"\w+", texto or "", flags=re.UNICODE))


def _contiene_termino(texto_norm: str, termino) -> bool:
    """Comprueba si un término o patrón aparece en el texto normalizado."""
    if isinstance(termino, re.Pattern):
        return termino.search(texto_norm) is not None
    if isinstance(termino, tuple):
        # tupla: todos los sub-términos deben aparecer (AND)
        return all(_contiene_termino(texto_norm, t) for t in termino)
    if isinstance(termino, list):
        # lista: cualquiera (OR)
        return any(_contiene_termino(texto_norm, t) for t in termino)

    # string: palabra/frase
    termino_norm = _normalizar(str(termino))
    if not termino_norm:
        return False

    # Token simple: permitir sufijos comunes (plural/conjugación) para términos
    # suficientemente específicos, evitando falsos positivos en tokens cortos.
    if re.fullmatch(r"[a-z0-9_]+", termino_norm):
        if len(termino_norm) <= 3:
            patron = r"\b" + re.escape(termino_norm) + r"\b"
        else:
            patron = r"\b" + re.escape(termino_norm) + r"\w*\b"
        return re.search(patron, texto_norm) is not None

    # Frase o expresión con espacios/símbolos: búsqueda por substring
    return termino_norm in texto_norm


def _concepto_demostrado(respuesta_norm: str, concepto: dict) -> bool:
    grupos = concepto.get("indicadores", [])
    if not grupos:
        return False
    for indicador in grupos:
        if _contiene_termino(respuesta_norm, indicador):
            return True
    return False


def _tiene_indicios_explicacion(respuesta_norm: str, num_palabras: int) -> bool:
    if num_palabras >= 14:
        return True

    texto = f" {respuesta_norm} "
    conectores_explicativos = [
        " es ", " son ", " sirve ", " sirven ", " permite ", " permiten ",
        " se utiliza ", " se utilizan ", " se usa ", " se usan ",
        " para ", " porque ", " mediante ", " consiste ", " ayuda ", " significa ",
        " cuando ", " diferencia ", " mientras ", " ejemplo ", " por ejemplo ",
        " como ", " ya que ", " debido ", " con el fin ", " su funcion ",
        " se encarga ", " encargado ", " define ", " definir ", " crea ", " crear ",
        " agrega ", " aporta ", " provoca ", " actualiza ", " hace que ",
        " permite que ", " de modo que ", " lo que ",
    ]
    if any(c in texto for c in conectores_explicativos):
        return True

    # Puntuación o estructura de frase con contenido suficiente
    if any(ch in (respuesta_norm or "") for ch in [".", ":", ";"]):
        return num_palabras >= 7
    if "," in (respuesta_norm or "") and num_palabras >= 9:
        return True

    return False


def _factor_sustancia(respuesta: str, respuesta_norm: str) -> float:
    palabras = _contar_palabras(respuesta)
    if palabras <= 1:
        return 0.15
    if palabras <= 3:
        return 0.35
    tiene_explicacion = _tiene_indicios_explicacion(respuesta_norm, palabras)
    if palabras <= 5:
        return 0.5 if tiene_explicacion else 0.35
    if palabras <= 8:
        return 0.75 if tiene_explicacion else 0.5
    if palabras <= 12:
        return 0.9 if tiene_explicacion else 0.7
    return 1.0 if tiene_explicacion else 0.85


def _construir_retroalimentacion(
    puntuacion: int,
    fortalezas: list,
    conceptos_faltantes: list,
    recomendacion: str,
    insuficiente_explicacion: bool,
    mensaje_adicional: str = "",
) -> str:
    partes = []
    if fortalezas:
        partes.append(f"Fortalezas: {'; '.join(fortalezas)}.")
    else:
        partes.append(
            "Fortalezas: no se identificaron conceptos clave explicados correctamente en la respuesta."
        )

    if conceptos_faltantes:
        partes.append(
            f"Conceptos que faltaron o se pueden reforzar: {'; '.join(conceptos_faltantes)}."
        )
    else:
        partes.append("Conceptos que faltaron o se pueden reforzar: ninguno relevante identificado.")

    if mensaje_adicional:
        partes.append(mensaje_adicional)
    elif insuficiente_explicacion and puntuacion < 100:
        partes.append(
            "Observación: la respuesta es breve o no explica con suficiente claridad los conceptos mencionados."
        )

    if recomendacion:
        partes.append(f"Recomendación: {recomendacion}")
    return "\n".join(partes)


def _estado_por_puntuacion(puntuacion: int) -> str:
    if puntuacion >= 70:
        return "Respuesta correcta"
    if puntuacion >= 40:
        return "Respuesta parcial"
    return "Respuesta incorrecta"


# ==========================
# Catálogo de criterios
# ==========================

def _criterios_catalogo():
    return [
        {
            "id": "html_css_js",
            "match": lambda q: "html" in q and "css" in q and "javascript" in q,
            "conceptos": [
                {
                    "nombre": "HTML: estructura/contenido",
                    "indicadores": [
                        ("html", "estructura"),
                        ("html", "contenido"),
                        ("html", "etiqueta"),
                        ("html", "maquet"),
                        "estructura de la pagina",
                        "contenido de la pagina",
                    ],
                    "peso": 2,
                    "feedback_ok": "distingue que HTML se usa para la estructura o el contenido",
                    "feedback_falta": "explicar que HTML define la estructura y el contenido de la página",
                },
                {
                    "nombre": "CSS: estilos/presentación",
                    "indicadores": [
                        ("css", "estilo"),
                        ("css", "diseno"),
                        ("css", "presentacion"),
                        ("css", "visual"),
                        ("css", "apariencia"),
                        "colores",
                        "fuentes",
                    ],
                    "peso": 2,
                    "feedback_ok": "reconoce que CSS se encarga de los estilos o la presentación visual",
                    "feedback_falta": "aclarar que CSS controla los estilos y la presentación visual",
                },
                {
                    "nombre": "JavaScript: interactividad/comportamiento",
                    "indicadores": [
                        ("javascript", "interactiv"),
                        ("javascript", "dinam"),
                        ("javascript", "comport"),
                        ("javascript", "logica"),
                        ("javascript", "funcional"),
                        ("javascript", "evento"),
                        "eventos",
                    ],
                    "peso": 2,
                    "feedback_ok": "identifica que JavaScript aporta interactividad o comportamiento dinámico",
                    "feedback_falta": "indicar que JavaScript agrega interactividad y lógica de comportamiento",
                },
            ],
            "recomendacion": "Explica el rol de cada tecnología con un ejemplo breve (HTML estructura, CSS estilo, JavaScript interacción).",
        },
        {
            "id": "react_definicion",
            "match": lambda q: "react" in q and ("para que" in q or "utiliza" in q) and "componente" not in q and "estado" not in q and "state" not in q and "hook" not in q and "props" not in q,
            "conceptos": [
                {
                    "nombre": "Biblioteca de JavaScript",
                    "indicadores": ["biblioteca", "libreria"],
                    "peso": 3,
                    "esencial": True,
                    "feedback_ok": "identifica React como una biblioteca/librería de JavaScript",
                    "feedback_falta": "mencionar que React es una biblioteca de JavaScript",
                },
                {
                    "nombre": "Creación de interfaces de usuario",
                    "indicadores": ["interfa", " ui ", "interfaces de usuario", "vista", "pantallas", "aplicacion web", "pagina web", "dinam", "interactiv", "frontend"],
                    "peso": 3,
                    "esencial": True,
                    "feedback_ok": "explica que se utiliza para crear interfaces de usuario (por ejemplo, dinámicas o interactivas)",
                    "feedback_falta": "explicar que se utiliza para crear interfaces de usuario en aplicaciones o páginas web",
                },
                {
                    "nombre": "Componentes reutilizables",
                    "indicadores": ["componente", "reutiliz", "modular"],
                    "peso": 1,
                    "esencial": False,
                    "feedback_ok": "menciona el uso de componentes reutilizables",
                    "feedback_falta": "incluir que React organiza la interfaz en componentes reutilizables",
                },
                {
                    "nombre": "Actualización por estado/renderizado",
                    "indicadores": ["estado", "state", "actualiza", "render", "virtual dom", "reactiv"],
                    "peso": 1,
                    "esencial": False,
                    "feedback_ok": "aporta cómo se actualiza la interfaz (estado, props o renderizado)",
                    "feedback_falta": "complementar con cómo se actualiza la interfaz mediante el estado o el renderizado",
                },
            ],
            "recomendacion": "Puedes complementar tu respuesta mencionando componentes reutilizables y cómo React actualiza la interfaz con el estado.",
        },
        {
            "id": "react_componente",
            "match": lambda q: "componente" in q and "react" in q,
            "conceptos": [
                {
                    "nombre": "Pieza reutilizable de UI",
                    "indicadores": ["reutiliz", "pieza", "bloque", "parte", "modulo", "unidad", "independiente", "elemento"],
                    "peso": 3,
                    "esencial": True,
                    "feedback_ok": "describe el componente como una pieza reutilizable de la interfaz",
                    "feedback_falta": "explicar que un componente es una parte reutilizable de la interfaz",
                },
                {
                    "nombre": "Encapsula lógica y/o vista",
                    "indicadores": ["encapsul", "logica", "vista", "interfaz", "estructura", "funcion", "jsx", "retorna", "devuelve", "renderiza", "muestra"],
                    "peso": 2,
                    "esencial": True,
                    "feedback_ok": "indica que encapsula lógica y/o la representación de la interfaz",
                    "feedback_falta": "mencionar que encapsula lógica y la representación de la interfaz",
                },
                {
                    "nombre": "Props/composición",
                    "indicadores": ["props", "propiedades", "parametros", "composicion", "hijos", "children"],
                    "peso": 1,
                    "esencial": False,
                    "feedback_ok": "menciona props o la composición entre componentes",
                    "feedback_falta": "añadir cómo recibe datos (props) o cómo se compone con otros componentes",
                },
            ],
            "recomendacion": "Puedes complementar con un ejemplo sencillo y mencionar cómo recibe datos mediante props.",
        },
        {
            "id": "react_state",
            "match": lambda q: ("estado" in q or "state" in q) and "react" in q,
            "conceptos": [
                {
                    "nombre": "Datos que pueden cambiar",
                    "indicadores": ["dato", "informacion", "valor", "cambia", "dinam", "variable", "almacena", "guarda", "contenido"],
                    "peso": 3,
                    "esencial": True,
                    "feedback_ok": "explica que el estado representa datos que pueden cambiar",
                    "feedback_falta": "aclarar que el estado son datos que cambian con el tiempo",
                },
                {
                    "nombre": "Actualiza la interfaz al cambiar",
                    "indicadores": ["actualiza", "render", "rerender", "vuelve a", "interfaz", "vista", "refleja", "muestra", "cambio"],
                    "peso": 3,
                    "esencial": True,
                    "feedback_ok": "relaciona el estado con la actualización de la interfaz",
                    "feedback_falta": "indicar que los cambios de estado provocan que la interfaz se actualice",
                },
                {
                    "nombre": "Gestión con hooks/setState",
                    "indicadores": ["usestate", "setstate", "hook", "hooks", "modificar el estado", "actualizar el estado", "set"],
                    "peso": 1,
                    "esencial": False,
                    "feedback_ok": "menciona cómo se gestiona el estado (por ejemplo, useState/setState)",
                    "feedback_falta": "complementar con cómo se actualiza (por ejemplo, con useState)",
                },
            ],
            "recomendacion": "Puedes complementar describiendo cómo actualizarías el estado (por ejemplo, con useState) y qué datos guardarías.",
        },
        {
            "id": "responsive",
            "match": lambda q: "adaptable" in q or "responsive" in q or "responsiv" in q or ("diseno" in q and ("pantalla" in q or "movil" in q or "dispositivo" in q)),
            "conceptos": [
                {
                    "nombre": "Objetivo de adaptación a distintos dispositivos",
                    "indicadores": ["dispositivo", "pantalla", "tamano", "movil", "celular", "tablet", "escritorio", "adapta", "ajusta", "diferentes", "responsiv"],
                    "peso": 2,
                    "esencial": True,
                    "feedback_ok": "reconoce el objetivo de adaptar el diseño a diferentes tamaños de pantalla o dispositivos",
                    "feedback_falta": "indicar que el objetivo es adaptarse a distintos dispositivos y tamaños de pantalla",
                },
                {
                    "nombre": "Uso de media queries",
                    "indicadores": ["media query", "media queries", "@media", "breakpoint", "puntos de quiebre"],
                    "peso": 2,
                    "esencial": True,
                    "cuenta_como_tecnica": True,
                    "feedback_ok": "menciona el uso de media queries o breakpoints",
                    "feedback_falta": "explicar el uso de media queries para aplicar estilos según el tamaño de pantalla",
                },
                {
                    "nombre": "Técnicas de layout flexible/unidades relativas",
                    "indicadores": ["flexbox", "grid", "porcentaje", "relativ", "rem", "em", "vw", "vh", "fluida", "viewport", "meta viewport", "max-width"],
                    "peso": 2,
                    "esencial": True,
                    "cuenta_como_tecnica": True,
                    "feedback_ok": "cita técnicas como flexbox/grid, unidades relativas o viewport",
                    "feedback_falta": "describir técnicas como Flexbox, Grid o unidades relativas para ajustar el contenido",
                },
            ],
            "respuesta_breve_insuficiente": True,
            "max_palabras_breve_insuficiente": 2,
            "terminos_tema": ["responsiv", "adaptable", "adaptacion", "dispositivo", "pantalla"],
            "mensaje_respuesta_breve": "Tu respuesta identifica el tema, pero necesita una explicación más completa. Describe qué técnicas utilizarías y cómo permitirían adaptar el contenido a diferentes tamaños de pantalla.",
            "recomendacion_respuesta_breve": "Menciona, por ejemplo, el uso de media queries, Flexbox, Grid y unidades relativas (como %, rem o vw) para lograr un diseño adaptable.",
            "recomendacion": "Explica qué técnicas aplicarías (media queries, Flexbox/Grid, unidades relativas o viewport) y cómo ayudan a adaptar el contenido.",
        },
        {
            "id": "clave_primaria",
            "match": lambda q: "clave primaria" in q or "primary key" in q,
            "conceptos": [
                {
                    "nombre": "Identificador único",
                    "indicadores": ["identificador", "identifica", "unico", "unica", "univoc"],
                    "peso": 2,
                    "feedback_ok": "reconoce que la clave primaria identifica de forma única",
                    "feedback_falta": "explicar que es un identificador único",
                },
                {
                    "nombre": "Aplica a cada registro/fila",
                    "indicadores": ["registro", "fila", "tupla", "cada"],
                    "peso": 2,
                    "feedback_ok": "indica que identifica cada registro/fila",
                    "feedback_falta": "mencionar que identifica cada registro o fila de la tabla",
                },
                {
                    "nombre": "Tabla y restricciones",
                    "indicadores": ["tabla", "base de datos", "no nulo", "no se repite", "no duplic", "sin duplic", "no repet"],
                    "peso": 1,
                    "feedback_ok": "contextualiza su uso en la tabla y/o sus restricciones",
                    "feedback_falta": "añadir que pertenece a una tabla y no debe repetirse ni ser nula",
                },
            ],
            "recomendacion": "Puedes ejemplificar con un campo como id_usuario o id_producto que no se repite.",
        },
        {
            "id": "get_post",
            "match": lambda q: "get" in q and "post" in q,
            "conceptos": [
                {
                    "nombre": "GET para obtener/consultar datos",
                    "indicadores": [
                        ("get", "obtener"),
                        ("get", "consult"),
                        ("get", "recuper"),
                        ("get", "leer"),
                        ("get", "traer"),
                        ("get", "solicitar"),
                    ],
                    "peso": 2,
                    "feedback_ok": "explica que GET se usa para obtener o consultar información",
                    "feedback_falta": "aclarar que GET se utiliza para obtener/consultar datos",
                },
                {
                    "nombre": "POST para enviar/crear datos",
                    "indicadores": [
                        ("post", "enviar"),
                        ("post", "crear"),
                        ("post", "registr"),
                        ("post", "guardar"),
                        ("post", "insert"),
                        ("post", "agregar"),
                    ],
                    "peso": 2,
                    "feedback_ok": "explica que POST se usa para enviar o crear datos",
                    "feedback_falta": "aclarar que POST se utiliza para enviar o crear información",
                },
                {
                    "nombre": "Diferencias adicionales",
                    "indicadores": ["url", "parametro", "cuerpo", "body", "idempot", "modifica", "servidor", "visible", "encabezado"],
                    "peso": 1,
                    "feedback_ok": "añade diferencias relevantes (cuerpo/URL, efecto en el servidor, etc.)",
                    "feedback_falta": "señalar alguna diferencia adicional como el uso de body/URL o el efecto en el servidor",
                },
            ],
            "recomendacion": "Contrasta ambos métodos con un ejemplo práctico (consultar un listado con GET y registrar un recurso con POST).",
        },
        {
            "id": "api_rest",
            "match": lambda q: "api" in q and "rest" in q,
            "conceptos": [
                {
                    "nombre": "Interfaz/comunicación entre sistemas",
                    "indicadores": ["comunicacion", "interfaz", "aplicaciones", "sistemas", "servicios", "conecta", "intercambio", "permite"],
                    "peso": 2,
                    "feedback_ok": "describe la API REST como un mecanismo de comunicación/interfaz entre aplicaciones",
                    "feedback_falta": "explicar que una API REST permite la comunicación entre aplicaciones o sistemas",
                },
                {
                    "nombre": "HTTP y modelo cliente-servidor",
                    "indicadores": ["http", "cliente", "servidor", "solicitud", "peticion", "request", "respuesta", "response", "endpoint", "recurso", "url"],
                    "peso": 2,
                    "feedback_ok": "menciona HTTP y/o el modelo cliente-servidor/solicitudes",
                    "feedback_falta": "incluir que funciona sobre HTTP mediante solicitudes entre cliente y servidor",
                },
                {
                    "nombre": "Uso para operar con recursos/datos",
                    "indicadores": ["datos", "recursos", "json", "get", "post", "put", "delete", "consultar", "enviar", "crear", "operaciones", "informacion"],
                    "peso": 1,
                    "feedback_ok": "indica para qué se utiliza (intercambiar u operar con datos/recursos)",
                    "feedback_falta": "aclarar su utilidad para consultar o manipular recursos/datos",
                },
            ],
            "recomendacion": "Menciona métodos HTTP comunes (GET, POST, PUT, DELETE) y un ejemplo de recurso o endpoint.",
        },
        {
            "id": "crud",
            "match": lambda q: "crud" in q or "operaciones crud" in q,
            "conceptos": [
                {"nombre": "Crear (Create)", "indicadores": ["crear", "create", "insertar", "agregar", "alta"], "peso": 1, "feedback_ok": "incluye la operación de crear", "feedback_falta": "incluir la operación de crear (Create)"},
                {"nombre": "Leer (Read)", "indicadores": ["leer", "read", "consultar", "obtener", "listar", "mostrar"], "peso": 1, "feedback_ok": "incluye la operación de leer/consultar", "feedback_falta": "incluir la operación de leer o consultar (Read)"},
                {"nombre": "Actualizar (Update)", "indicadores": ["actualizar", "update", "modificar", "editar"], "peso": 1, "feedback_ok": "incluye la operación de actualizar", "feedback_falta": "incluir la operación de actualizar (Update)"},
                {"nombre": "Eliminar (Delete)", "indicadores": ["eliminar", "delete", "borrar", "remover"], "peso": 1, "feedback_ok": "incluye la operación de eliminar", "feedback_falta": "incluir la operación de eliminar (Delete)"},
            ],
            "recomendacion": "Relaciona cada operación CRUD con un ejemplo en una aplicación o base de datos.",
        },
        {
            "id": "manejo_errores_backend",
            "match": lambda q: ("error" in q or "errores" in q) and ("backend" in q or "aplicacion" in q or "manejar" in q or "gestion" in q),
            "conceptos": [
                {
                    "nombre": "Captura/control de excepciones",
                    "indicadores": ["try", "except", "catch", "excepcion", "manejo de errores", "control de errores", "bloque"],
                    "peso": 2,
                    "feedback_ok": "menciona mecanismos de captura/control de excepciones",
                    "feedback_falta": "incluir el uso de manejo de excepciones (por ejemplo, try/except o try/catch)",
                },
                {
                    "nombre": "Validación de datos/entradas",
                    "indicadores": ["valid", "entrada", "input", "datos", "verificar", "comprobar", "sanitiz"],
                    "peso": 2,
                    "feedback_ok": "considera la validación de datos o entradas",
                    "feedback_falta": "agregar la validación de datos de entrada para prevenir errores",
                },
                {
                    "nombre": "Respuestas adecuadas/logging",
                    "indicadores": ["log", "registro", "mensaje", "codigo", "status", "http", "respuesta", "monitoreo", "notificar"],
                    "peso": 1,
                    "feedback_ok": "contempla respuestas claras, códigos o registro de errores",
                    "feedback_falta": "mencionar respuestas adecuadas al cliente y/o registro (logging) de errores",
                },
            ],
            "recomendacion": "Combina validación preventiva, manejo de excepciones y respuestas/logs claros para facilitar el diagnóstico.",
        },
        {
            "id": "sql_uso",
            "match": lambda q: ("sql" in q and ("utiliza" in q or "sirve" in q or "para que" in q or "que es" in q)) and "clave primaria" not in q,
            "conceptos": [
                {
                    "nombre": "Lenguaje para bases de datos",
                    "indicadores": ["lenguaje", "base de datos", "bases de datos", "relacional", "gestionar", "sistema"],
                    "peso": 2,
                    "feedback_ok": "identifica SQL como lenguaje para trabajar con bases de datos",
                    "feedback_falta": "mencionar que SQL es un lenguaje para gestionar bases de datos (usualmente relacionales)",
                },
                {
                    "nombre": "Consultar/manipular datos",
                    "indicadores": ["consultar", "consultas", "select", "insert", "update", "delete", "manipular", "crear", "modificar", "obtener", "almacenar", "extraer"],
                    "peso": 2,
                    "feedback_ok": "explica que permite consultar y/o manipular datos",
                    "feedback_falta": "indicar que se usa para consultar y manipular datos (por ejemplo, con SELECT, INSERT, UPDATE, DELETE)",
                },
            ],
            "recomendacion": "Incluye ejemplos de operaciones comunes como consultas (SELECT) y modificaciones de datos.",
        },
        {
            "id": "analisis_datos",
            "match": lambda q: "analisis de datos" in q or ("que es" in q and "analisis" in q and "datos" in q),
            "conceptos": [
                {
                    "nombre": "Examinar/procesar datos",
                    "indicadores": ["examinar", "procesar", "recolect", "limpiar", "transform", "organizar", "explorar", "estudiar", "analizar", "interpretar"],
                    "peso": 2,
                    "feedback_ok": "explica que implica examinar o procesar datos",
                    "feedback_falta": "indicar que consiste en examinar, limpiar o procesar datos",
                },
                {
                    "nombre": "Obtener información/conclusiones/decisiones",
                    "indicadores": ["informacion", "conclusion", "decision", "patrones", "tendencia", "insight", "conocimiento", "util", "resultado"],
                    "peso": 2,
                    "feedback_ok": "señala que busca obtener información, patrones o apoyar decisiones",
                    "feedback_falta": "aclarar que su objetivo es obtener información útil o apoyar la toma de decisiones",
                },
            ],
            "recomendacion": "Puedes mencionar etapas como limpieza, exploración y visualización de datos para apoyar conclusiones.",
        },
        {
            "id": "tabla_vs_grafico",
            "match": lambda q: "tabla" in q and "grafico" in q,
            "conceptos": [
                {
                    "nombre": "Tabla: filas/columnas y detalle",
                    "indicadores": [("tabla", "fila"), ("tabla", "columna"), ("tabla", "dato"), ("tabla", "detalle"), ("tabla", "organiza"), ("tabla", "estructura")],
                    "peso": 2,
                    "feedback_ok": "describe la tabla como una estructura de filas/columnas con datos detallados",
                    "feedback_falta": "explicar que una tabla organiza datos en filas y columnas de forma detallada",
                },
                {
                    "nombre": "Gráfico: representación visual",
                    "indicadores": [("grafico", "visual"), ("grafico", "represent"), ("grafico", "imagen"), ("grafico", "muestra"), ("grafico", "forma")],
                    "peso": 2,
                    "feedback_ok": "describe el gráfico como una representación visual de los datos",
                    "feedback_falta": "explicar que un gráfico representa los datos de forma visual",
                },
                {
                    "nombre": "Tendencias/comparación",
                    "indicadores": ["tendencia", "compar", "patron", "facil", "rapido", "interpret", "analisis"],
                    "peso": 1,
                    "feedback_ok": "menciona la utilidad para comparar o identificar tendencias",
                    "feedback_falta": "añadir que los gráficos facilitan ver tendencias o comparaciones",
                },
            ],
            "recomendacion": "Contrasta cuándo conviene ver valores exactos (tabla) y cuándo visualizar patrones (gráfico).",
        },
        {
            "id": "power_bi",
            "match": lambda q: "power bi" in q or "powerbi" in q,
            "conceptos": [
                {
                    "nombre": "Herramienta de BI/visualización",
                    "indicadores": ["herramienta", "plataforma", "software", "business intelligence", "inteligencia de negocios", " bi ", "microsoft"],
                    "peso": 2,
                    "feedback_ok": "identifica Power BI como una herramienta de análisis/BI",
                    "feedback_falta": "mencionar que Power BI es una herramienta de Business Intelligence",
                },
                {
                    "nombre": "Informes/dashboards/visualizaciones",
                    "indicadores": ["visual", "informe", "report", "dashboard", "tablero", "grafico", "panel"],
                    "peso": 2,
                    "feedback_ok": "señala su uso para visualizar datos y crear informes o tableros",
                    "feedback_falta": "indicar que permite crear visualizaciones, informes y tableros",
                },
                {
                    "nombre": "Conexión/análisis de datos",
                    "indicadores": ["analisis", "datos", "conectar", "fuentes", "importar", "modelar"],
                    "peso": 1,
                    "feedback_ok": "menciona el análisis o conexión con fuentes de datos",
                    "feedback_falta": "añadir que se usa para analizar datos desde distintas fuentes",
                },
            ],
            "recomendacion": "Puedes mencionar ejemplos como dashboards interactivos para seguimiento de indicadores.",
        },
        {
            "id": "datos_inconsistentes",
            "match": lambda q: "inconsistente" in q or ("identific" in q and "datos" in q),
            "conceptos": [
                {
                    "nombre": "Nulos/duplicados/formatos",
                    "indicadores": ["nulo", "faltante", "duplic", "formato", "tipo", "vacio", "perdido", "erroneo"],
                    "peso": 2,
                    "feedback_ok": "propone revisar valores nulos, duplicados o formatos",
                    "feedback_falta": "incluir la detección de valores nulos, duplicados o formatos incorrectos",
                },
                {
                    "nombre": "Validación de rangos/reglas/coherencia",
                    "indicadores": ["rango", "regla", "coheren", "valid", "negocio", "fuera de", "atipico", "outlier", "logica"],
                    "peso": 2,
                    "feedback_ok": "considera validar rangos, reglas de negocio o coherencia",
                    "feedback_falta": "mencionar la validación de rangos, coherencia o reglas de negocio",
                },
                {
                    "nombre": "Perfilado/cruce/limpieza",
                    "indicadores": ["perfil", "compar", "cruce", "fuente", "explor", "limpieza", "estadistic", "depurar"],
                    "peso": 1,
                    "feedback_ok": "menciona técnicas de perfilado, cruce o limpieza de datos",
                    "feedback_falta": "añadir técnicas como perfilado, cruce entre fuentes o limpieza de datos",
                },
            ],
            "recomendacion": "Combina validaciones automáticas (tipos, rangos, duplicados) con revisión de reglas de negocio.",
        },
        {
            "id": "machine_learning",
            "match": lambda q: "machine learning" in q or "aprendizaje automatico" in q,
            "conceptos": [
                {
                    "nombre": "Relación con IA",
                    "indicadores": ["inteligencia artificial", " ia ", "rama", "campo", "disciplina", "subcampo"],
                    "peso": 1,
                    "feedback_ok": "lo relaciona con la inteligencia artificial",
                    "feedback_falta": "mencionar que es un campo relacionado con la inteligencia artificial",
                },
                {
                    "nombre": "Aprendizaje de patrones a partir de datos",
                    "indicadores": ["aprend", "patron", "datos", "entren", "experiencia", "ejemplo", "algoritmo"],
                    "peso": 2,
                    "feedback_ok": "explica que los modelos aprenden patrones a partir de datos",
                    "feedback_falta": "indicar que aprende patrones a partir de datos",
                },
                {
                    "nombre": "Predicción/tareas sin reglas explícitas fijas",
                    "indicadores": ["predic", "decision", "clasific", "sin program", "automatic", "modelo", "resultado"],
                    "peso": 2,
                    "feedback_ok": "señala que permite predecir o realizar tareas a partir de lo aprendido",
                    "feedback_falta": "aclarar que se usa para realizar predicciones o tareas sin programar reglas explícitas para cada caso",
                },
            ],
            "recomendacion": "Incluye un ejemplo sencillo, como clasificar correos o predecir valores a partir de datos históricos.",
        },
        {
            "id": "supervisado_no_supervisado",
            "match": lambda q: "supervisado" in q and "no supervisado" in q,
            "conceptos": [
                {
                    "nombre": "Supervisado: datos etiquetados",
                    "indicadores": [("supervisado", "etiquet"), ("supervisado", "label"), ("supervisado", "conocida"), ("supervisado", "respuesta"), ("supervisado", "objetivo")],
                    "peso": 2,
                    "feedback_ok": "explica que el aprendizaje supervisado usa datos etiquetados",
                    "feedback_falta": "aclarar que el supervisado trabaja con datos etiquetados",
                },
                {
                    "nombre": "No supervisado: sin etiquetas y patrones/grupos",
                    "indicadores": [("no supervisado", "sin etiquet"), ("no supervisado", "patron"), ("no supervisado", "agrup"), ("no supervisado", "cluster"), ("no supervisado", "segment")],
                    "peso": 2,
                    "feedback_ok": "explica que el no supervisado busca patrones o agrupaciones sin etiquetas",
                    "feedback_falta": "aclarar que el no supervisado trabaja sin etiquetas para encontrar patrones o grupos",
                },
                {
                    "nombre": "Ejemplos de tareas",
                    "indicadores": ["clasific", "regres", "clustering", "agrupamiento", "predic"],
                    "peso": 1,
                    "feedback_ok": "da ejemplos o propósitos de cada enfoque",
                    "feedback_falta": "añadir un ejemplo (clasificación/regresión vs agrupamiento)",
                },
            ],
            "recomendacion": "Contrasta ambos con ejemplos concretos, como predecir una etiqueta frente a agrupar clientes por similitud.",
        },
        {
            "id": "conjunto_entrenamiento",
            "match": lambda q: "conjunto de entrenamiento" in q or ("entrenamiento" in q and "datos" in q and "entrenar" in q),
            "conceptos": [
                {
                    "nombre": "Subconjunto de datos",
                    "indicadores": ["subconjunto", "parte", "porcion", "conjunto de datos", "datos", "muestra"],
                    "peso": 2,
                    "feedback_ok": "indica que es un subconjunto de los datos disponibles",
                    "feedback_falta": "explicar que es una parte del conjunto total de datos",
                },
                {
                    "nombre": "Uso para entrenar/ajustar el modelo",
                    "indicadores": ["entrenar", "entrena", "ajustar", "aprender", "modelo", "parametros", "algoritmo"],
                    "peso": 2,
                    "feedback_ok": "explica que se utiliza para entrenar o ajustar el modelo",
                    "feedback_falta": "aclarar que sirve para que el modelo aprenda o ajuste sus parámetros",
                },
            ],
            "recomendacion": "Puedes complementar mencionando que se diferencia de los conjuntos de validación y prueba.",
        },
        {
            "id": "overfitting",
            "match": lambda q: "sobreajuste" in q or "overfitting" in q,
            "conceptos": [
                {
                    "nombre": "Ajuste excesivo al entrenamiento/ruido",
                    "indicadores": ["demasiado", "memoriza", "ruido", "detalle", "especifico", "ajusta mucho", "entrenamiento", "aprende de mas"],
                    "peso": 2,
                    "feedback_ok": "explica que el modelo se ajusta en exceso a los datos de entrenamiento",
                    "feedback_falta": "indicar que el modelo aprende demasiado los datos de entrenamiento (incluido ruido)",
                },
                {
                    "nombre": "Mala generalización en datos nuevos",
                    "indicadores": ["generaliz", "nuevo", "prueba", "test", "rendimiento", "bajo", "no funciona", "desempeno", "desconocidos"],
                    "peso": 2,
                    "feedback_ok": "señala que generaliza mal ante datos nuevos",
                    "feedback_falta": "aclarar que tiene bajo desempeño en datos nuevos o de prueba",
                },
            ],
            "recomendacion": "Menciona posibles mitigaciones como más datos, regularización o validación para mejorar la generalización.",
        },
        {
            "id": "scikit_learn",
            "match": lambda q: "scikit" in q or "sklearn" in q,
            "conceptos": [
                {
                    "nombre": "Biblioteca de Python",
                    "indicadores": ["biblioteca", "libreria", "python", "paquete", "modulo"],
                    "peso": 2,
                    "feedback_ok": "identifica Scikit-learn como una biblioteca de Python",
                    "feedback_falta": "mencionar que es una biblioteca de Python",
                },
                {
                    "nombre": "Algoritmos/herramientas de ML",
                    "indicadores": ["machine learning", "aprendizaje automatico", "algoritmo", "clasificacion", "regresion", "clustering", "modelo", " ml "],
                    "peso": 2,
                    "feedback_ok": "indica que ofrece algoritmos o herramientas de machine learning",
                    "feedback_falta": "explicar que proporciona algoritmos y utilidades para machine learning",
                },
                {
                    "nombre": "Preprocesamiento/evaluación",
                    "indicadores": ["preproces", "entrenar", "evalu", "metric", "seleccion", "validacion", "pipeline", "transform"],
                    "peso": 1,
                    "feedback_ok": "menciona utilidades para preprocesar, entrenar o evaluar modelos",
                    "feedback_falta": "añadir que también incluye herramientas de preprocesamiento y evaluación",
                },
            ],
            "recomendacion": "Cita ejemplos de uso como clasificación, regresión, clustering o evaluación de modelos.",
        },
        # Compatibilidad ampliada con temas mencionados
        {
            "id": "props_react",
            "match": lambda q: "props" in q and "react" in q,
            "conceptos": [
                {"nombre": "Datos que recibe un componente", "indicadores": ["datos", "parametro", "propiedades", "recibe", "entrada", "argument", "valor"], "peso": 2, "feedback_ok": "explica que las props son datos que recibe un componente", "feedback_falta": "aclarar que las props son datos o parámetros que recibe un componente"},
                {"nombre": "Comunicación entre componentes", "indicadores": ["padre", "hijo", "comunica", "pasar", "componente", "reutiliz", "enviar"], "peso": 2, "feedback_ok": "menciona su uso para pasar información entre componentes", "feedback_falta": "indicar que permiten pasar información entre componentes"},
                {"nombre": "Uso de solo lectura/inmutabilidad", "indicadores": ["inmut", "no se modific", "solo lectura", "unidirecc", "no cambiar"], "peso": 1, "feedback_ok": "señala que se tratan como valores de solo lectura", "feedback_falta": "añadir que normalmente no deben modificarse directamente"},
            ],
            "recomendacion": "Ejemplifica cómo un componente padre pasa información a un hijo mediante props.",
        },
        {
            "id": "hooks_react",
            "match": lambda q: "hook" in q and "react" in q,
            "conceptos": [
                {"nombre": "Funciones de React", "indicadores": ["funcion", "api", "permiten", "react", "caracteristica"], "peso": 1, "feedback_ok": "identifica los hooks como funciones de React", "feedback_falta": "mencionar que los hooks son funciones proporcionadas por React"},
                {"nombre": "Estado y efectos en componentes funcionales", "indicadores": ["estado", "usestate", "efecto", "useeffect", "ciclo", "funcional", "lateral"], "peso": 2, "feedback_ok": "explica que permiten usar estado o efectos en componentes funcionales", "feedback_falta": "aclarar que permiten manejar estado y efectos en componentes funcionales"},
                {"nombre": "Ejemplos de hooks", "indicadores": ["usestate", "useeffect", "usecontext", "usememo", "usecallback", "usereducer"], "peso": 1, "feedback_ok": "menciona ejemplos concretos de hooks", "feedback_falta": "incluir ejemplos como useState o useEffect"},
            ],
            "recomendacion": "Cita casos de uso comunes, como useState para estado local y useEffect para efectos secundarios.",
        },
        {
            "id": "consumo_api",
            "match": lambda q: (("consum" in q or "llamar" in q or "solicitar" in q or "conectar" in q) and "api" in q),
            "conceptos": [
                {"nombre": "Solicitudes HTTP a endpoints", "indicadores": ["http", "solicitud", "peticion", "request", "fetch", "axios", "endpoint", "url", "cliente"], "peso": 2, "feedback_ok": "menciona cómo realizar solicitudes HTTP a una API", "feedback_falta": "explicar que implica hacer solicitudes HTTP a endpoints"},
                {"nombre": "Métodos e intercambio de datos", "indicadores": ["get", "post", "json", "datos", "respuesta", "body", "parametro", "enviar", "recibir"], "peso": 2, "feedback_ok": "considera métodos HTTP y el intercambio de datos", "feedback_falta": "incluir métodos como GET/POST y el manejo de datos (por ejemplo, JSON)"},
                {"nombre": "Manejo de respuestas/errores", "indicadores": ["respuesta", "status", "codigo", "error", "try", "catch", "promesa", "async", "await", "excepcion"], "peso": 1, "feedback_ok": "contempla el manejo de respuestas o errores", "feedback_falta": "añadir el manejo de respuestas, estados y posibles errores"},
            ],
            "recomendacion": "Describe un flujo básico: enviar solicitud, procesar la respuesta y manejar errores adecuadamente.",
        },
        {
            "id": "python_general",
            "match": lambda q: "python" in q and ("que es" in q or "para que" in q or "utiliza" in q),
            "conceptos": [
                {"nombre": "Lenguaje de programación", "indicadores": ["lenguaje", "programacion", "alto nivel", "interpretado"], "peso": 2, "feedback_ok": "identifica Python como un lenguaje de programación", "feedback_falta": "mencionar que Python es un lenguaje de programación"},
                {"nombre": "Usos/aplicaciones", "indicadores": ["web", "datos", "automat", "script", "machine learning", "backend", "aplicaciones", "analisis"], "peso": 2, "feedback_ok": "menciona aplicaciones o usos de Python", "feedback_falta": "incluir para qué se utiliza (web, datos, automatización, etc.)"},
                {"nombre": "Características", "indicadores": ["legible", "sencill", "simple", "librer", "biblioteca", "versatil", "comunidad"], "peso": 1, "feedback_ok": "destaca características relevantes de Python", "feedback_falta": "añadir alguna característica como legibilidad o ecosistema de bibliotecas"},
            ],
            "recomendacion": "Apóyate en un ejemplo de uso práctico para explicar por qué Python es útil en ese contexto.",
        },
        {
            "id": "fastapi",
            "match": lambda q: "fastapi" in q,
            "conceptos": [
                {"nombre": "Framework web para APIs en Python", "indicadores": ["framework", "python", "api", "web", "backend"], "peso": 2, "feedback_ok": "identifica FastAPI como un framework de Python para APIs", "feedback_falta": "mencionar que FastAPI es un framework de Python para crear APIs"},
                {"nombre": "Rendimiento/asincronía o tipado", "indicadores": ["rapido", "asincron", "async", "tipado", "type hints", "validacion", "pydantic"], "peso": 2, "feedback_ok": "menciona características como rendimiento, asincronía o validación/tipado", "feedback_falta": "incluir características como rapidez, soporte async o validación de datos"},
                {"nombre": "Documentación/endpoints", "indicadores": ["endpoint", "ruta", "documentacion", "openapi", "swagger", "rest"], "peso": 1, "feedback_ok": "señala la creación de endpoints o documentación automática", "feedback_falta": "añadir que facilita crear endpoints y documentación automática"},
            ],
            "recomendacion": "Menciona cómo definirías un endpoint y qué ventajas ofrece FastAPI en su desarrollo.",
        },
        {
            "id": "nodejs",
            "match": lambda q: "node" in q and ("js" in q or "javascript" in q),
            "conceptos": [
                {"nombre": "Entorno de ejecución de JavaScript", "indicadores": ["entorno", "ejecucion", "runtime", "javascript", "servidor"], "peso": 2, "feedback_ok": "identifica Node.js como entorno de ejecución para JavaScript", "feedback_falta": "mencionar que Node.js es un entorno de ejecución de JavaScript"},
                {"nombre": "Uso en backend/servidor", "indicadores": ["backend", "servidor", "aplicaciones", "red", "servicios"], "peso": 2, "feedback_ok": "explica su uso para desarrollar aplicaciones del lado del servidor", "feedback_falta": "indicar que se usa comúnmente para backend o servicios del lado del servidor"},
                {"nombre": "Modelo asincrónico/eventos o npm", "indicadores": ["asincron", "evento", "no bloqueante", "npm", "paquetes"], "peso": 1, "feedback_ok": "menciona características como asincronía, eventos o npm", "feedback_falta": "añadir características como el modelo asincrónico/no bloqueante o el ecosistema npm"},
            ],
            "recomendacion": "Relaciona Node.js con un caso de uso, como la creación de APIs o servicios en tiempo real.",
        },
        {
            "id": "bases_datos_sql",
            "match": lambda q: "base de datos" in q or "bases de datos" in q,
            "conceptos": [
                {"nombre": "Almacenamiento organizado de datos", "indicadores": ["almacena", "guardar", "organiza", "datos", "informacion", "sistema"], "peso": 2, "feedback_ok": "explica que una base de datos almacena y organiza información", "feedback_falta": "mencionar que una base de datos permite almacenar y organizar datos"},
                {"nombre": "Consulta/gestión de datos", "indicadores": ["consultar", "gestionar", "acceder", "administrar", "leer", "modificar"], "peso": 2, "feedback_ok": "indica que permite consultar o gestionar datos", "feedback_falta": "incluir que facilita consultar y gestionar la información"},
                {"nombre": "Estructura/relaciones o SQL", "indicadores": ["tabla", "relacion", "registro", "sql", "relacional", "campo"], "peso": 1, "feedback_ok": "menciona aspectos estructurales como tablas, relaciones o SQL", "feedback_falta": "añadir elementos como tablas/relaciones o el uso de SQL según el contexto"},
            ],
            "recomendacion": "Da un ejemplo de entidad y cómo se almacenarían sus registros en una base de datos.",
        },
        {
            "id": "autenticacion",
            "match": lambda q: "autentic" in q,
            "conceptos": [
                {"nombre": "Verificación de identidad", "indicadores": ["identidad", "usuario", "verificar", "credencial", "quien es", "login", "ingreso", "acceso"], "peso": 2, "feedback_ok": "explica que la autenticación verifica la identidad", "feedback_falta": "aclarar que la autenticación consiste en verificar la identidad del usuario"},
                {"nombre": "Mecanismos/credenciales", "indicadores": ["contrasena", "password", "token", "jwt", "sesion", "mfa", "oauth", "clave"], "peso": 2, "feedback_ok": "menciona mecanismos o credenciales de autenticación", "feedback_falta": "incluir mecanismos como contraseñas, tokens o sesiones"},
                {"nombre": "Relación con seguridad/acceso", "indicadores": ["autoriza", "permiso", "acceso", "seguridad", "proteger", "recurso"], "peso": 1, "feedback_ok": "relaciona la autenticación con el control de acceso o la seguridad", "feedback_falta": "diferenciarla brevemente de la autorización o permisos"},
            ],
            "recomendacion": "Explica un ejemplo de inicio de sesión y cómo se valida la identidad de forma segura.",
        },
        {
            "id": "seguridad",
            "match": lambda q: "seguridad" in q or "secure" in q or "vulnerab" in q,
            "conceptos": [
                {"nombre": "Protección de datos/sistemas", "indicadores": ["proteger", "proteccion", "datos", "sistema", "informacion", "confidencial", "integridad"], "peso": 2, "feedback_ok": "enfoca la seguridad en proteger datos y sistemas", "feedback_falta": "explicar que la seguridad busca proteger datos y sistemas"},
                {"nombre": "Prácticas/controles", "indicadores": ["cifrado", "hash", "valid", "acceso", "permiso", "autentic", "https", "contraseña", "control"], "peso": 2, "feedback_ok": "menciona prácticas o controles de seguridad", "feedback_falta": "incluir prácticas como validación, control de accesos o cifrado"},
                {"nombre": "Prevención de riesgos/vulnerabilidades", "indicadores": ["ataque", "riesgo", "prev", "mitig", "inyeccion", "xss", "sql injection", "vulnerab"], "peso": 1, "feedback_ok": "considera la prevención o mitigación de riesgos", "feedback_falta": "añadir la importancia de prevenir vulnerabilidades y riesgos"},
            ],
            "recomendacion": "Menciona medidas concretas según el contexto, como validación de entradas, gestión de permisos y protección de credenciales.",
        },
        {
            "id": "git",
            "match": lambda q: " git" in f" {q} " or q.startswith("git") or "control de versiones" in q,
            "conceptos": [
                {"nombre": "Sistema de control de versiones", "indicadores": ["control de versiones", "version", "versiones", "historial", "repositorio"], "peso": 2, "feedback_ok": "identifica Git como un sistema de control de versiones", "feedback_falta": "mencionar que Git es un sistema de control de versiones"},
                {"nombre": "Gestión de cambios y colaboración", "indicadores": ["rama", "branch", "commit", "colabor", "merge", "cambio", "equipo", "guardar cambios"], "peso": 2, "feedback_ok": "explica su utilidad para gestionar cambios y colaborar", "feedback_falta": "indicar que permite registrar cambios y trabajar colaborativamente (commits/ramas)"},
            ],
            "recomendacion": "Puedes mencionar comandos o flujos básicos como commit, branch y merge para gestionar cambios.",
        },
        {
            "id": "excel",
            "match": lambda q: "excel" in q,
            "conceptos": [
                {"nombre": "Herramienta de hojas de cálculo", "indicadores": ["hoja de calculo", "herramienta", "microsoft", "planilla", "tabla"], "peso": 2, "feedback_ok": "identifica Excel como una herramienta de hojas de cálculo", "feedback_falta": "mencionar que Excel es una herramienta de hojas de cálculo"},
                {"nombre": "Análisis/organización de datos", "indicadores": ["datos", "analisis", "organizar", "calculo", "formula", "grafico", "tabla dinamica", "filtro"], "peso": 2, "feedback_ok": "señala su uso para organizar, calcular o analizar datos", "feedback_falta": "indicar que se usa para organizar y analizar datos (fórmulas, tablas, gráficos)"},
            ],
            "recomendacion": "Incluye ejemplos como uso de fórmulas, filtros, tablas dinámicas o gráficos para analizar información.",
        },
        {
            "id": "modelo_predictivo",
            "match": lambda q: "modelo predictivo" in q or ("predict" in q and "modelo" in q),
            "conceptos": [
                {"nombre": "Modelo basado en datos", "indicadores": ["modelo", "datos", "algoritmo", "entren", "historico"], "peso": 2, "feedback_ok": "explica que se construye a partir de datos", "feedback_falta": "mencionar que es un modelo construido a partir de datos"},
                {"nombre": "Predicción de resultados futuros/tendencias", "indicadores": ["predic", "futuro", "resultado", "tendencia", "estimar", "pronost"], "peso": 2, "feedback_ok": "indica que sirve para predecir resultados o tendencias", "feedback_falta": "aclarar que se utiliza para predecir resultados o comportamientos futuros"},
            ],
            "recomendacion": "Menciona un ejemplo de variable a predecir y la importancia de contar con datos de calidad.",
        },
    ]


def _seleccionar_criterio(pregunta: str):
    pregunta_norm = f" {_normalizar(pregunta)} "
    for criterio in _criterios_catalogo():
        try:
            if criterio["match"](pregunta_norm):
                return criterio
        except Exception:
            continue
    return None


def evaluar_respuesta(pregunta: str, respuesta: str) -> dict:
    """
    Evalúa una respuesta de entrevista con criterios conceptuales.

    Retorna puntuación (0-100), retroalimentación personalizada, conceptos
    correctos/faltantes y recomendación. Si no existen criterios suficientes
    para la pregunta, no inventa una calificación.
    """

    if not isinstance(pregunta, str):
        pregunta = "" if pregunta is None else str(pregunta)
    if not isinstance(respuesta, str):
        respuesta = "" if respuesta is None else str(respuesta)

    if not respuesta.strip():
        return {
            "pregunta": pregunta,
            "puntuacion": 0,
            "retroalimentacion": "Debes escribir una respuesta.",
            "estado": "Respuesta vacía",
            "fortalezas": [],
            "conceptos_correctos": [],
            "conceptos_faltantes": [],
            "recomendacion": "Escribe una respuesta que explique los conceptos clave de la pregunta.",
        }

    criterio = _seleccionar_criterio(pregunta)
    if not criterio:
        return {
            "pregunta": pregunta,
            "puntuacion": None,
            "retroalimentacion": "No existen criterios suficientes para evaluar esta pregunta.",
            "estado": "Pregunta no reconocida",
            "fortalezas": [],
            "conceptos_correctos": [],
            "conceptos_faltantes": [],
            "recomendacion": "No hay criterios automáticos disponibles para esta pregunta.",
        }

    respuesta_norm = _normalizar(respuesta)
    conceptos = criterio.get("conceptos", [])
    num_palabras = _contar_palabras(respuesta)

    conceptos_correctos = []
    conceptos_faltantes = []
    fortalezas = []
    peso_obtenido = 0
    peso_total = 0
    peso_esencial_obtenido = 0
    peso_esencial_total = 0

    for concepto in conceptos:
        peso = concepto.get("peso", 1)
        esencial = concepto.get("esencial", False)
        peso_total += peso
        if esencial:
            peso_esencial_total += peso

        if _concepto_demostrado(respuesta_norm, concepto):
            peso_obtenido += peso
            if esencial:
                peso_esencial_obtenido += peso
            nombre = concepto.get("nombre", "Concepto clave")
            ok = concepto.get("feedback_ok") or nombre
            conceptos_correctos.append(nombre)
            fortalezas.append(ok)
        else:
            falta = concepto.get("feedback_falta") or concepto.get("nombre", "Concepto clave")
            conceptos_faltantes.append(falta)

    peso_total = peso_total or 1
    cobertura = peso_obtenido / peso_total
    if peso_esencial_total > 0:
        cobertura_esencial = peso_esencial_obtenido / peso_esencial_total
        base = (0.35 * cobertura) + (0.65 * cobertura_esencial)
    else:
        cobertura_esencial = cobertura
        base = cobertura

    factor = _factor_sustancia(respuesta, respuesta_norm)
    explicacion_suficiente = _tiene_indicios_explicacion(respuesta_norm, num_palabras) or num_palabras >= 8
    if peso_esencial_total > 0 and cobertura_esencial >= 0.99:
        # Respuesta conceptualmente correcta en lo esencial: no penalizar en exceso por omisión de complementarios.
        if explicacion_suficiente or num_palabras >= 6:
            factor = max(factor, 0.9)
        else:
            factor = max(factor, 0.75)
    elif peso_esencial_total > 0 and cobertura_esencial >= 0.5:
        # Cobertura esencial parcial: solo reducir penalización si hay explicación suficiente.
        if explicacion_suficiente:
            factor = max(factor, 0.7)
        elif num_palabras >= 6:
            factor = max(factor, 0.55)
    elif peso_obtenido > 0 and num_palabras >= 6:
        factor = max(factor, 0.6 if explicacion_suficiente else 0.5)

    # Caso especial: respuesta extremadamente breve que solo identifica el tema sin explicar.
    insuficiente_breve = False
    if num_palabras <= 3:
        min_conceptos_para_breve = criterio.get("min_conceptos_para_respuesta_breve", 1)
        terminos_tema = criterio.get("terminos_tema", [])
        identifica_tema = any(_contiene_termino(respuesta_norm, t) for t in terminos_tema) if terminos_tema else peso_obtenido > 0
        tecnicas_demostradas = sum(
            1
            for c in conceptos
            if c.get("cuenta_como_tecnica") and _concepto_demostrado(respuesta_norm, c)
        )
        if criterio.get("respuesta_breve_insuficiente") and num_palabras <= criterio.get("max_palabras_breve_insuficiente", 2):
            if tecnicas_demostradas == 0:
                insuficiente_breve = True
        elif peso_obtenido > 0 and len(conceptos_correctos) < min_conceptos_para_breve and num_palabras <= 2:
            insuficiente_breve = True

        if insuficiente_breve:
            # Puede reconocer el tema, pero no constituye explicación suficiente.
            base = min(base, 0.25 if identifica_tema else 0.1)
            factor = min(factor, 0.6)

    puntuacion = int(round(base * factor * 100))
    puntuacion = max(0, min(100, puntuacion))

    insuficiente_explicacion = factor < 0.75 or insuficiente_breve
    estado = _estado_por_puntuacion(puntuacion)

    recomendacion = criterio.get(
        "recomendacion",
        "Refuerza los conceptos clave y explica su utilidad con mayor claridad.",
    )
    if insuficiente_breve and criterio.get("recomendacion_respuesta_breve"):
        recomendacion = criterio["recomendacion_respuesta_breve"]
    elif not conceptos_faltantes and puntuacion >= 70:
        recomendacion = (
            "Puedes complementar tu respuesta con un ejemplo práctico para hacerla aún más completa."
        )

    if insuficiente_breve and criterio.get("mensaje_respuesta_breve"):
        identifica_tema = peso_obtenido > 0 or (
            criterio.get("terminos_tema")
            and any(_contiene_termino(respuesta_norm, t) for t in criterio.get("terminos_tema", []))
        )
        fortalezas_mostrar = ["identifica el tema principal de la pregunta"] if identifica_tema else fortalezas
        if identifica_tema:
            fortalezas = fortalezas_mostrar
        conceptos_faltantes_mostrar = conceptos_faltantes if conceptos_faltantes else [
            "explicar cómo aplicarías la idea en la práctica"
        ]
        if not conceptos_faltantes:
            conceptos_faltantes = conceptos_faltantes_mostrar
        retroalimentacion = _construir_retroalimentacion(
            puntuacion=puntuacion,
            fortalezas=fortalezas_mostrar,
            conceptos_faltantes=conceptos_faltantes_mostrar,
            recomendacion=recomendacion,
            insuficiente_explicacion=True,
            mensaje_adicional=criterio.get("mensaje_respuesta_breve"),
        )
    else:
        retroalimentacion = _construir_retroalimentacion(
            puntuacion=puntuacion,
            fortalezas=fortalezas,
            conceptos_faltantes=conceptos_faltantes,
            recomendacion=recomendacion,
            insuficiente_explicacion=insuficiente_explicacion and (peso_obtenido > 0 or insuficiente_breve),
        )

    return {
        "pregunta": pregunta,
        "puntuacion": puntuacion,
        "retroalimentacion": retroalimentacion,
        "estado": estado,
        "fortalezas": fortalezas,
        "conceptos_correctos": conceptos_correctos,
        "conceptos_faltantes": conceptos_faltantes,
        "recomendacion": recomendacion,
    }
